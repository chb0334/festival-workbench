#!/usr/bin/env python3.11
"""用浏览器捕获回来的 huaban_capture.json + 本地 images/huaban/*.webp，
把工作台四份副本的「花瓣网」板块整体替换为“节日+盘子”内容。

- 只保留有本地图的记录（缺图的报告出来，让用户补抓）
- 字段 schema 与现有记录一致（id/year/holiday/platform/title/source_url/...）
- 四份副本 img/thumb 前缀不同：根目录 images/huaban/，子目录 ../../images/huaban/

用法:
  python3.11 rebuild_huaban.py huaban_capture.json          # 预览
  python3.11 rebuild_huaban.py huaban_capture.json --apply  # 写回并提交
"""
import re, json, os, argparse, subprocess
from datetime import datetime

IMG_DIR = "images/huaban"
FILES = {
    "index.html": "images/huaban/",
    "index_online.html": "images/huaban/",
    "节日工作台数据库/工作台文件/index.html": "../../images/huaban/",
    "节日工作台数据库/工作台文件/index_online.html": "../../images/huaban/",
}


def extract_arr(s):
    i = s.index("var DATA")
    start = s.index("[", i)
    depth, end = 0, -1
    for j in range(start, len(s)):
        if s[j] == "[":
            depth += 1
        elif s[j] == "]":
            depth -= 1
            if depth == 0:
                end = j
                break
    return start, end


def filekey(u):
    m = re.search(r"([0-9a-f]{40}-[A-Za-z0-9]+)_", u or "")
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capture", help="huaban_capture.json 路径")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    cap = json.load(open(a.capture, encoding="utf-8"))
    if isinstance(cap, list) and cap and isinstance(cap[0], list):
        cap = [r for pg in cap for r in pg]
    by = {}
    for r in cap:
        h = r.get("hash") or filekey(r.get("url", ""))
        if h:
            by[h] = r
    print("捕获去重后图片数:", len(by))

    s0 = open("index.html", encoding="utf-8").read()
    st0, en0 = extract_arr(s0)
    arr0 = json.loads(s0[st0:en0 + 1])
    maxid = max((r.get("id", 0) for r in arr0), default=0)
    old_hb = sum(1 for r in arr0 if r.get("platform") == "花瓣网")

    today = datetime.now().strftime("%Y-%m-%d %H:%M")
    new, missing = [], []
    for h, r in by.items():
        path = os.path.join(IMG_DIR, h + ".webp")
        if not os.path.exists(path):
            missing.append(h)
            continue
        w = hh = b = 0
        try:
            from PIL import Image
            im = Image.open(path)
            w, hh = im.size
            b = os.path.getsize(path)
        except Exception:
            pass
        holiday = r.get("holiday") or (r.get("q", "").replace("盘子", "") if r.get("q") else "")
        title = r.get("title") or r.get("q") or holiday
        rec = {
            "id": 0, "year": "2026", "holiday": holiday, "platform": "花瓣网",
            "design_type": "", "title": title,
            "source_url": r.get("source") or "",
            "brand": "", "asin": "", "price": "", "evidence_type": "无",
            "evidence_value": "", "evidence_note": "",
            "collected_by": "花瓣网捕获书签", "collected_at": today,
            "tags": "", "note": "", "favorite": False, "file": "",
            "thumb": "", "width": w, "height": hh, "bytes": b, "hash": h,
            "holiday_reason": "搜索词含「%s」" % holiday,
            "material": "", "color": "", "composition": "",
            "review_status": "", "tier": 2, "heat": 0.0, "img": "",
        }
        new.append(rec)

    print("有本地图可写入:", len(new), " | 缺图:", len(missing))
    if missing:
        print("缺图 hash 样例(需补抓):", missing[:12])

    if not a.apply:
        print("\n[DRY-RUN] 加 --apply 写回；将把花瓣网板块由 %d 条替换为 %d 条" % (old_hb, len(new)))
        return

    nid = maxid
    for fpath, prefix in FILES.items():
        s = open(fpath, encoding="utf-8").read()
        st, en = extract_arr(s)
        arr = json.loads(s[st:en + 1])
        arr = [r for r in arr if r.get("platform") != "花瓣网"]
        for rec in new:
            nid += 1
            rec = dict(rec)
            rec["id"] = nid
            local = prefix + rec["hash"] + ".webp"
            rec["img"] = local
            rec["thumb"] = local
            arr.append(rec)
        open(fpath, "w", encoding="utf-8").write(
            s[:st] + json.dumps(arr, ensure_ascii=False, indent=2) + s[en + 1:])
        print("已写回:", fpath, "(总", len(arr), ", 花瓣网", len(new), ")")

    # 提交
    try:
        subprocess.run(["git", "add", *FILES.keys(), IMG_DIR], check=False)
        subprocess.run(["git", "commit", "-q", "-m",
                        "花瓣网板块重做为“节日+盘子”：捕获书签抓取%d张本地托管，四份副本同步(旧%d→新%d)"
                        % (len(new), old_hb, len(new))], check=False)
        print("已 git 提交")
    except Exception as e:
        print("提交出错:", e)


if __name__ == "__main__":
    main()
