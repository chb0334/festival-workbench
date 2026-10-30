#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""制作离线工作台：复制 index.html + images，并对大图压缩，保证本地双击即看。"""
import os, shutil, io
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

SRC = "/workspace"
DST = "/workspace/离线工作台"

os.makedirs(DST, exist_ok=True)
print("复制 index.html ...")
shutil.copy(f"{SRC}/index.html", f"{DST}/index.html")

print("复制 images ...")
if os.path.exists(f"{DST}/images"):
    shutil.rmtree(f"{DST}/images")
shutil.copytree(f"{SRC}/images", f"{DST}/images")

MAXEDGE = 1400
THRESH = 400 * 1024  # 小于400KB不处理

def compress(p):
    try:
        size = os.path.getsize(p)
        if size < THRESH:
            return
        ext = p.lower().rsplit(".", 1)[-1]
        im = Image.open(p)
        w, h = im.size
        if max(w, h) > MAXEDGE:
            r = MAXEDGE / max(w, h)
            im = im.resize((int(w * r), int(h * r)))
        if ext in ("jpg", "jpeg"):
            im = im.convert("RGB")
            im.save(p, "JPEG", quality=78, optimize=True)
        elif ext == "png":
            im.save(p, "PNG", optimize=True)
        elif ext == "webp":
            im.save(p, "WEBP", quality=72)
        else:
            im.save(p)
    except Exception as e:
        print("跳过", p, e)

paths = []
for root, _, files in os.walk(f"{DST}/images"):
    for f in files:
        paths.append(os.path.join(root, f))

print(f"压缩 {len(paths)} 个文件 ...")
with ThreadPoolExecutor(max_workers=8) as ex:
    list(ex.map(compress, paths))

total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(f"{DST}/images") for f in fs)
print(f"完成。压缩后 images 大小: {total/1048576:.1f} MB")
