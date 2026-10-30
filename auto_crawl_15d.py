#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""节日素材工作台 · 15天周期自动抓取

流程: 亚马逊(带月销量证据) → 独立站 → 花瓣网(尽力,失败跳过) → 入库去重
      → 渲染校验 → 重建分发包 → 推送GitHub → 出报告

设计要点:
  - 每一步独立容错: 单源失败只记进报告, 不中断整体
  - 严格超时: 防止某一步卡死拖垮整个周期任务
  - 出报告: crawl_report_<日期>.json / .md, 便于人工复盘"这次抓到了什么"

用法:
  python3 auto_crawl_15d.py                       # 完整周期(默认每关键词25条)
  python3 auto_crawl_15d.py --per-kw 40           # 抓更多
  python3 auto_crawl_15d.py --skip-rebuild        # 跳过重建分发包(快速验证用)
  python3 auto_crawl_15d.py --skip-huaban         # 跳过花瓣网(已知常被EdgeOne挡)
"""
import subprocess, os, sys, json, io, re, time, argparse, datetime

WORK = "/workspace"
HTML = os.path.join(WORK, "index.html")


def run(cmd, timeout, tag):
    print("\n=== [%s] %s (超时%ss)" % (tag, " ".join(cmd[:2]), timeout), flush=True)
    t = time.time()
    try:
        p = subprocess.run(cmd, cwd=WORK, timeout=timeout,
                           capture_output=True, text=True, errors="ignore")
        r = {"tag": tag, "ok": p.returncode == 0, "rc": p.returncode,
             "sec": round(time.time() - t),
             "tail": (p.stdout or "")[-1200:], "err": (p.stderr or "")[-400:]}
    except subprocess.TimeoutExpired:
        r = {"tag": tag, "ok": False, "rc": -1, "sec": timeout,
             "tail": "", "err": "超时 %ss 被终止" % timeout}
    except Exception as e:
        r = {"tag": tag, "ok": False, "rc": -2, "sec": 0, "tail": "", "err": str(e)[:300]}
    print("    -> %s 耗时%ss %s" % ("OK" if r["ok"] else "FAIL", r["sec"],
                                    "" if r["ok"] else r["err"][:120]), flush=True)
    return r


def count_items():
    s = io.open(HTML, encoding="utf-8").read()
    m = re.search(r'var DATA = (\[.*?\]);', s, re.S)
    return len(json.loads(m.group(1))) if m else -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-kw", type=int, default=25)
    ap.add_argument("--skip-huaban", action="store_true")
    ap.add_argument("--skip-rebuild", action="store_true")
    ap.add_argument("--skip-push", action="store_true")
    args = ap.parse_args()

    steps, before = [], count_items()
    print("抓取前库存: %s 条" % before, flush=True)

    # 1) 亚马逊（主力源，带月销量证据）
    steps.append(run([sys.executable, "crawl_amz_items.py", "--per-kw", str(args.per_kw)],
                     3600, "亚马逊抓取"))

    # 2) 独立站
    steps.append(run([sys.executable, "crawl_sophistiplate.py"], 1500, "独立站抓取"))

    # 3) 花瓣网（常被 EdgeOne 挡，失败不影响整体）
    if not args.skip_huaban:
        steps.append(run([sys.executable, "crawl_huaban.py", "30"], 900, "花瓣网抓取"))
        hb = steps[-1]
        try:
            d = json.load(io.open(os.path.join(WORK, "huaban_export.json"), encoding="utf-8"))
            got = len(d) if isinstance(d, list) else 0
        except Exception:
            got = 0
        if got == 0:
            hb["ok"] = False
            hb["err"] = (hb["err"] or "") + " | 花瓣网未产出有效素材（huaban_export.json 为空/无效，通常被人机验证拦截）"
            print("    !! 花瓣网实际未抓到素材，记为失败", flush=True)

    # 4) 入库去重（--apply 必须带：脚本默认是 dry-run 预览，不写库！）
    steps.append(run([sys.executable, "import_new_materials.py", "--apply"], 900, "入库去重"))

    after = count_items()
    added = (after - before) if (after >= 0 and before >= 0) else -1
    print("抓取后库存: %s 条（新增 %s）" % (after, added), flush=True)

    # 5) 渲染校验（零裂图、卡片等高）
    verify = os.path.join(WORK, "verify_render.py")
    if os.path.exists(verify):
        steps.append(run([sys.executable, verify], 600, "渲染校验"))

    # 6) 重建分发包
    if not args.skip_rebuild:
        for s, t in [("build_offline.py", 2400), ("build_lite.py", 1800), ("build_publish.py", 1800)]:
            steps.append(run([sys.executable, s], t, "重建-" + s.replace(".py", "")))

    # 7) 推送 GitHub（网络抖动常见，失败仅记录）
    if not args.skip_push:
        run(["git", "add", "-A", "index.html", "index_online.html", "images",
             "节日工作台数据库/工作台文件"], 300, "git-add")
        cm = run(["git", "commit", "-m", "周期自动抓取(15天): 新增%s条, 库存%s条" % (added, after)],
                 300, "git-commit")
        steps.append(cm)
        ps = None
        for _try in range(3):  # 网络抖动常见，重试3次
            ps = run(["git", "push", "origin", "main"], 600, "git-push" + ("" if _try == 0 else "(重试%s)" % _try))
            if ps["ok"]:
                break
        steps.append(ps)

    # 8) 报告
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    rep = {"date": date, "before": before, "after": after, "added": added, "steps": steps}
    json.dump(rep, io.open(os.path.join(WORK, "crawl_report_%s.json" % date), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    md = ["# 周期抓取报告 %s" % date, "",
          "- 抓取前: **%s** 条 → 抓取后: **%s** 条（新增 **%s** 条）" % (before, after, added), "",
          "| 步骤 | 结果 | 耗时 |", "|---|---|---|"]
    for s in steps:
        md.append("| %s | %s | %ss |" % (s["tag"], "✅ 成功" if s["ok"] else "❌ 失败", s["sec"]))
    md.append("")
    for s in steps:
        if not s["ok"]:
            md.append("### ❌ %s 失败详情" % s["tag"])
            md.append("```")
            md.append((s["err"] or s["tail"])[-800:])
            md.append("```")
    io.open(os.path.join(WORK, "crawl_report_%s.md" % date), "w", encoding="utf-8").write("\n".join(md))

    ok = sum(1 for s in steps if s["ok"])
    print("\n==== 完成: %s/%s 步成功, 新增 %s 条 ====" % (ok, len(steps), added), flush=True)


if __name__ == "__main__":
    main()
