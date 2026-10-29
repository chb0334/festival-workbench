#!/usr/bin/env python3.11
"""花瓣图本地化收尾：把工作台四份副本中花瓣网记录的 img/thumb 改指本地文件。

匹配规则：从记录的 img URL 提取花瓣图 hash（如 1495...-WNsp5D），
若 images/huaban/<hash>.webp 已存在，则改写；不存在的跳过并报告（待补下载）。

- 根目录两份(index.html / index_online.html): images/huaban/<hash>.webp
- 子目录两份(节日工作台数据库/工作台文件/*):   ../../images/huaban/<hash>.webp

用法: python3.11 fix_huaban_imgs.py            # 预览
      python3.11 fix_huaban_imgs.py --apply    # 写回
"""
import re, os, json, argparse

FILES = {
    "index.html": "images/huaban/",
    "index_online.html": "images/huaban/",
    "节日工作台数据库/工作台文件/index.html": "../../images/huaban/",
    "节日工作台数据库/工作台文件/index_online.html": "../../images/huaban/",
}
IMG_DIR = "images/huaban"


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


def hash_of(u):
    m = re.search(r"huaban\.com/([0-9a-f]+-[A-Za-z0-9]+)_", u or "")
    return m.group(1) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()

    have = set()
    if os.path.isdir(IMG_DIR):
        have = {f[:-5] for f in os.listdir(IMG_DIR) if f.endswith(".webp")}
    print(f"本地已存在图片: {len(have)} 张 (目录 {IMG_DIR})\n")

    for path, prefix in FILES.items():
        s = open(path, encoding="utf-8").read()
        st, en = extract_arr(s)
        arr = json.loads(s[st:en + 1])
        hit = miss = 0
        for r in arr:
            if r.get("platform") != "花瓣网":
                continue
            h = hash_of(r.get("img", ""))
            if h and h in have:
                local = prefix + h + ".webp"
                r["img"] = local
                r["thumb"] = local
                hit += 1
            else:
                miss += 1
        print(f"{path}: 命中 {hit} | 缺图 {miss}")
        if a.apply and hit:
            new_html = s[:st] + json.dumps(arr, ensure_ascii=False, indent=2) + s[en + 1:]
            open(path, "w", encoding="utf-8").write(new_html)

    if not a.apply:
        print("\n[DRY-RUN] 加 --apply 写回")


if __name__ == "__main__":
    main()
