#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""通用：把工作台数据里所有 img 为 http(s) 的远程图本地化到 images/remote/，
   彻底清除外网依赖。对 4 份 HTML 同步替换。"""
import json, os, re, sys, time, urllib.request, hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
HTMLS = ["index.html", "index_online.html",
         "节日工作台数据库/工作台文件/index.html",
         "节日工作台数据库/工作台文件/index_online.html"]


def load_arr():
    s = open("index.html", encoding="utf-8").read()
    i = s.index("var DATA")
    st = s.index("[", i)
    d = cnt = 0
    for j in range(st, len(s)):
        if s[j] == "[":
            cnt += 1
        elif s[j] == "]":
            cnt -= 1
            if cnt == 0:
                en = j
                break
    return s, json.loads(s[st:en + 1])


def collect():
    _, arr = load_arr()
    urls = set()
    for r in arr:
        img = r.get("img") or ""
        if img.startswith("http"):
            urls.add(img)
    return urls


def localname(u):
    b = u.split("?")[0].rsplit("/", 1)[-1]
    if not b or "." not in b:
        b = hashlib.md5(u.encode()).hexdigest() + ".jpg"
    return b


def download(u, tries=4):
    b = localname(u)
    fn = "images/remote/" + b
    if os.path.exists(fn) and os.path.getsize(fn) > 300:
        return ("skip", u, b)
    host = u.split("/")[2]
    for t in range(tries):
        try:
            req = urllib.request.Request(
                u, headers={"User-Agent": UA, "Referer": "https://" + host + "/"})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
            if len(data) < 300:
                raise IOError("too small")
            open(fn, "wb").write(data)
            return ("ok", u, b)
        except Exception as e:
            if t == tries - 1:
                return ("fail", u, str(e)[:60])
            time.sleep(2)
    return ("fail", u, "timeout")


def main():
    os.makedirs("images/remote", exist_ok=True)
    apply = "--apply" in sys.argv
    urls = collect()
    print("全库剩余远程img URL:", len(urls))
    if not apply:
        for u in sorted(urls)[:5]:
            print("  ", u)
        print("（dry）跳过")
        return
    ok = skip = fail = 0
    fails = []
    mapping = {}
    with ThreadPoolExecutor(max_workers=12) as ex:
        for f in as_completed([ex.submit(download, u) for u in urls]):
            status, u, b = f.result()
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                fail += 1
                fails.append((u, b))
            mapping[u] = "images/remote/" + b
    print("下载: ok=%d skip=%d fail=%d" % (ok, skip, fail))
    for u, e in fails:
        print("  失败:", u, e)
    # 替换 4 份 HTML
    for fp in HTMLS:
        txt = open(fp, encoding="utf-8").read()
        new = txt
        for u, local in mapping.items():
            if u in new:
                new = new.replace(u, local)
        left = sum(1 for r in json.loads(extract_data(new)) if (r.get("img") or "").startswith("http"))
        open(fp, "w", encoding="utf-8").write(new)
        print("[%s] 替换后剩余远程img: %d" % (fp, left))
    # 复验
    print("复验全库远程img:", len(collect()))


def extract_data(txt):
    i = txt.index("var DATA")
    st = txt.index("[", i)
    cnt = 0
    for j in range(st, len(txt)):
        if txt[j] == "[":
            cnt += 1
        elif txt[j] == "]":
            cnt -= 1
            if cnt == 0:
                en = j
                break
    return txt[st:en + 1]


if __name__ == "__main__":
    main()
