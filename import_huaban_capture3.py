#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""把 huaban_capture(3).json 里【万圣节】的素材入库。

步骤：
  1. 读取捕获 JSON，筛选 holiday 为 万圣节 / 万圣节刀叉勺 的条目
  2. 按 图片KEY(URL里的40hex) / hash40hex / pinID 三重去重（命中现有 135 张或本批已有则跳过）
  3. 用浏览器UA + 免签名裸链 https://gd-hbimg.huaban.com/<KEY>_fw658webp 并行下载到 images/huaban/
  4. 按现有记录 schema 生成新记录（design_type 由搜索词判定，evidence_type=设计参考）
  5. 写入 4 份工作台副本（--apply 才真正写；先 --dry 看统计）
"""
import json, re, os, sys, glob, datetime, concurrent.futures

CAPTURE = "/tmp/huaban_capture3.json"
IMG_DIR = "images/huaban"
COPIES = [
    "index.html",
    "index_online.html",
    "节日工作台数据库/工作台文件/index.html",
    "节日工作台数据库/工作台文件/index_online.html",
]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

DESIGN_MAP = {
    "万圣节盘子": "盘子",
    "万圣节杯子": "杯子",
    "万圣节刀叉勺": "餐具",
}


def urlkey(u):
    """从 url 字段取出带后缀的图片KEY（如 321847...-NQzaCh）。"""
    if not u:
        return None
    seg = u.split("?")[0].rstrip("/").split("/")[-1]
    seg = re.sub(r"_fw\w*webp$", "", seg)   # 去掉 _fw240webp / _fw658webp
    if "-" not in seg:
        return None
    hexpart = seg.split("-")[0]
    if re.fullmatch(r"[0-9a-f]+", hexpart):
        return seg
    return None


def key40(u):
    """URL KEY 的前 40 位 hex（图片唯一标识）。"""
    k = urlkey(u)
    if not k:
        return None
    m = re.match(r"([0-9a-f]{40})", k)
    return m.group(1) if m else None


def hash40(h):
    return (h or "").split("-")[0] if h else None


def pin_id(src):
    if not src:
        return None
    m = re.search(r"/pins/(\d+)", src)
    return m.group(1) if m else None


def load_existing():
    """读取 index.html，返回 (arr, existing_files, existing_pins)。"""
    s = open("index.html", encoding="utf-8").read()
    i = s.index("var DATA")
    st = s.index("[", i)
    d = 0
    for j in range(st, len(s)):
        if s[j] == "[":
            d += 1
        elif s[j] == "]":
            d -= 1
            if d == 0:
                en = j
                break
    arr = json.loads(s[st:en + 1])
    files = set(os.path.basename(f).replace(".webp", "")
                for f in glob.glob(os.path.join(IMG_DIR, "*.webp")))
    pins = set()
    for r in arr:
        if r.get("platform") == "花瓣网" and r.get("source_url"):
            p = pin_id(r["source_url"])
            if p:
                pins.add(p)
    return arr, files, pins


def download_one(item):
    k = urlkey(item["url"])
    if not k:
        return None, "no_urlkey"
    out = os.path.join(IMG_DIR, key40(item["url"]) + ".webp")
    if os.path.exists(out) and os.path.getsize(out) > 1000:
        return out, "exists"
    url = f"https://gd-hbimg.huaban.com/{k}_fw658webp"
    try:
        cmd = f'curl -s -A "{UA}" -o "{out}" "{url}" --max-time 25 -w "%{{http_code}}"'
        code = os.popen(cmd).read().strip()
        if os.path.exists(out) and os.path.getsize(out) > 1000 and code == "200":
            return out, "ok"
        if os.path.exists(out):
            os.remove(out)
        return None, f"http{code}"
    except Exception as e:
        return None, f"err:{e}"


def main():
    dry = "--dry" in sys.argv
    apply = "--apply" in sys.argv
    data = json.load(open(CAPTURE, encoding="utf-8"))
    han = [d for d in data if d.get("holiday") in ("万圣节", "万圣节刀叉勺")]

    arr, existing_files, existing_pins = load_existing()
    max_id = max([r.get("id", 0) for r in arr] or [0])
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    # 去重筛选
    seen_k40 = set()
    todo = []
    skipped = 0
    for d in han:
        k40 = key40(d.get("url"))
        h40 = hash40(d.get("hash"))
        pid = pin_id(d.get("source"))
        if not k40:
            skipped += 1
            continue
        if k40 in existing_files or h40 in existing_files or (pid and pid in existing_pins):
            skipped += 1
            continue
        if k40 in seen_k40:
            skipped += 1
            continue
        seen_k40.add(k40)
        todo.append(d)

    print(f"万圣节捕获: {len(han)} 条 | 跳过(重复/已存在): {skipped} | 待下载: {len(todo)}")
    from collections import Counter
    print("待下载按类别:", dict(Counter(DESIGN_MAP.get(d["title"], "其他") for d in todo)))

    if dry:
        return

    # 下载
    print("开始并行下载...")
    results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        fut = {ex.submit(download_one, d): d for d in todo}
        done = 0
        for f in concurrent.futures.as_completed(fut):
            d = fut[f]
            out, status = f.result()
            results[key40(d["url"])] = (out, status)
            done += 1
            if done % 30 == 0:
                print(f"  进度 {done}/{len(todo)}")

    ok = [k for k, (o, s) in results.items() if o and s in ("ok", "exists")]
    fail = [(k, s) for k, (o, s) in results.items() if not o]
    print(f"下载完成: 成功 {len(ok)} | 失败 {len(fail)}")
    if fail:
        print("失败样本:", fail[:10])

    if not apply:
        print("\n（未写入。加 --apply 才真正入库并写 4 份副本）")
        return

    # 生成新记录
    new_recs = []
    for d in todo:
        k40 = key40(d["url"])
        out, status = results.get(k40, (None, "x"))
        if not out:
            continue
        sz = os.path.getsize(out)
        dt = DESIGN_MAP.get(d["title"], "其他")
        max_id += 1
        rec = {
            "id": max_id, "year": "2026", "holiday": "万圣节",
            "platform": "花瓣网", "design_type": dt, "title": d.get("title") or "万圣节素材",
            "source_url": (d.get("source") or "").strip(),
            "brand": "", "asin": "", "price": "",
            "evidence_type": "设计参考", "evidence_value": "—", "evidence_note": "",
            "collected_by": "花瓣网捕获书签", "collected_at": now,
            "tags": "", "note": "", "favorite": False, "file": "",
            "thumb": f"images/huaban/{k40}.webp", "width": 658, "height": 0,
            "bytes": sz, "hash": k40,
            "holiday_reason": "搜索词含「万圣节」",
            "material": "", "color": "", "composition": "",
            "review_status": "", "tier": 2, "heat": 0.0,
            "img": f"images/huaban/{k40}.webp",
        }
        new_recs.append(rec)

    print(f"生成新记录 {len(new_recs)} 条")

    # 写入 4 份副本
    for fp in COPIES:
        if not os.path.exists(fp):
            print("跳过(不存在):", fp)
            continue
        s = open(fp, encoding="utf-8").read()
        i = s.index("var DATA")
        st = s.index("[", i)
        d = 0
        for j in range(st, len(s)):
            if s[j] == "[":
                d += 1
            elif s[j] == "]":
                d -= 1
                if d == 0:
                    en = j
                    break
        old = json.loads(s[st:en + 1])
        old.extend(new_recs)
        new_block = json.dumps(old, ensure_ascii=False)
        s2 = s[:st] + new_block + s[en + 1:]
        open(fp, "w", encoding="utf-8").write(s2)
        print(f"  写入 {fp}: 现共 {len(old)} 条")

    print("入库完成。")


if __name__ == "__main__":
    main()
