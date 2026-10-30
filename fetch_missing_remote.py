#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""从 git HEAD 旧版 index.html 提取全部 workbuddy 远程 URL(836个唯一)，
   续传下载到 images/remote/，补齐 replace 时遗漏的 418 张。"""
import os, re, subprocess, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"


def collect_all():
    old = subprocess.check_output(["git", "show", "HEAD:index.html"], text=True)
    urls = re.findall(
        r"https://workbuddy-space-static\.codebuddy\.work/image/[A-Za-z0-9_]+\.[A-Za-z0-9]+",
        old)
    seen = set()
    uniq = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def download(u, tries=4):
    fn = os.path.join("images/remote", os.path.basename(u))
    if os.path.exists(fn) and os.path.getsize(fn) > 500:
        return ("skip", u)
    for t in range(tries):
        try:
            req = urllib.request.Request(
                u, headers={"User-Agent": UA,
                            "Referer": "https://workbuddy-space-static.codebuddy.work/"})
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
            if len(data) < 500:
                raise IOError("too small %d" % len(data))
            open(fn, "wb").write(data)
            return ("ok", u)
        except Exception as e:
            if t == tries - 1:
                return ("fail", u + " | " + str(e)[:80])
            time.sleep(1.5)
    return ("fail", u)


def main():
    urls = collect_all()
    print("git HEAD 提取唯一URL:", len(urls))
    os.makedirs("images/remote", exist_ok=True)
    ok = skip = fail = 0
    fails = []
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = [ex.submit(download, u) for u in urls]
        done = 0
        for f in as_completed(futs):
            status, u = f.result()
            done += 1
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip += 1
            else:
                fail += 1
                fails.append(u)
            if done % 100 == 0:
                print("进度 %d/%d ok=%d skip=%d fail=%d 耗时%.0fs"
                      % (done, len(urls), ok, skip, fail, time.time() - t0))
    print("=== 完成 ===")
    print("ok=%d skip=%d(已存在) fail=%d 耗时%.0fs" % (ok, skip, fail, time.time() - t0))
    if fails:
        print("失败:")
        for x in fails:
            print("  ", x)


if __name__ == "__main__":
    main()
