#!/usr/bin/env python3.11
"""把「花瓣网导出工具」书签导出的文本导入工作台(index.html)。

用法:
  python3.11 import_huaban.py export.txt            # 试运行, 只打印将新增
  python3.11 import_huaban.py export.txt --apply    # 真正写入 index.html
  cat export.txt | python3.11 import_huaban.py -     # 从 stdin 读取

去重: 按 source_url 与现有记录比对, 已存在则跳过。
分类: 按标题/链接里的节日关键词归入 万圣节/感恩节/圣诞节/复活节/情人节/独立日, 否则「其他」。
"""
import re
import json
import sys
import datetime
from collections import Counter

HOLIDAYS = [
    ("万圣节", ["万圣节", "万圣", "halloween"]),
    ("感恩节", ["感恩节", "thanksgiving"]),
    ("圣诞节", ["圣诞节", "圣诞", "christmas", "xmas"]),
    ("复活节", ["复活节", "easter"]),
    ("情人节", ["情人节", "七夕", "valentine"]),
    ("独立日", ["独立日", "国庆", "independence", "july 4th", "7月4日"]),
]


def classify(title, url):
    s = ((title or "") + " " + (url or "")).lower()
    for name, keys in HOLIDAYS:
        if any(k in s for k in keys):
            return name
    return "其他"


def parse_export(text):
    m = re.search(r'===HUABAN_EXPORT_START===(.*?)===HUABAN_EXPORT_END===', text, re.S)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except Exception:
            pass
    try:
        d = json.loads(text)
        return d if isinstance(d, list) else [d]
    except Exception:
        return []


DATA_FILE = "index.html"


def load_data(s):
    """返回 (arr, a, bj)：a 为数组 '[' 的位置，bj 为数组 ']' 的位置。"""
    m = re.search(r'var DATA\s*=\s*\[', s)
    if not m:
        raise RuntimeError("找不到 var DATA 数组")
    a = m.end() - 1
    depth = 0
    n = len(s)
    p = a
    while p < n:
        c = s[p]
        if c == '[':
            depth += 1
        elif c == ']':
            depth -= 1
            if depth == 0:
                return json.loads(s[a:p + 1]), a, p
        p += 1
    raise RuntimeError("数组未闭合")


def main():
    args = sys.argv[1:]
    apply = False
    path = None
    for a in args:
        if a == "--apply":
            apply = True
        elif a == "-":
            path = None
        elif not a.startswith("-"):
            path = a
    text = open(path, encoding='utf-8').read() if path else sys.stdin.read()

    items = parse_export(text)
    html = open(DATA_FILE, encoding='utf-8').read()
    arr, a, bj = load_data(html)
    existing_urls = {str(r.get('source_url', '')) for r in arr}
    max_id = max([r.get('id', 0) for r in arr] or [0])
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

    new_recs = []
    for it in items:
        url = (it.get('url') or '').strip()
        title = (it.get('title') or '').strip()
        img = (it.get('image') or '').strip()
        if not url and not img:
            continue
        if url and url in existing_urls:
            continue
        holiday = classify(title, url)
        max_id += 1
        rec = {
            "id": max_id, "year": "2026", "holiday": holiday,
            "platform": "花瓣网", "design_type": "", "title": title or "花瓣网图片",
            "source_url": url, "brand": "", "asin": "", "price": "",
            "evidence_type": "无", "evidence_value": "", "evidence_note": "",
            "collected_by": "花瓣网导出书签", "collected_at": now,
            "tags": "", "note": "", "favorite": False, "file": "",
            "thumb": img, "width": 0, "height": 0, "bytes": 0, "hash": "",
            "holiday_reason": (f"标题含「{holiday}」" if holiday != "其他" else ""),
            "material": "", "color": "", "composition": "",
            "review_status": "", "tier": 2, "heat": 0.0, "img": img,
        }
        new_recs.append(rec)
        if url:
            existing_urls.add(url)

    if not new_recs:
        print("无新增（导出为空或已全部存在）")
        return

    print(f"将新增 {len(new_recs)} 条花瓣网记录：")
    print("  按节日：", dict(Counter(r['holiday'] for r in new_recs)))
    for r in new_recs[:12]:
        print(f"  + #{r['id']} [{r['holiday']}] {r['title'][:42]}")
    if len(new_recs) > 12:
        print(f"  ... 其余 {len(new_recs) - 12} 条")

    if not apply:
        print("\n（试运行，未写入。加 --apply 才真正写入 index.html）")
        return

    arr.extend(new_recs)
    new_block = json.dumps(arr, ensure_ascii=False, indent=2)
    # html[:a] 保留 "var DATA = " 前缀(含缩进); html[bj+1:] 从原数组 ']' 后的 ';' 开始
    html2 = html[:a] + new_block + html[bj + 1:]
    open(DATA_FILE, 'w', encoding='utf-8').write(html2)
    print(f"\n已写入 index.html，当前共 {len(arr)} 条")


if __name__ == "__main__":
    main()
