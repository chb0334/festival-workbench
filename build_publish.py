#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""构建用于在线发布的站点：900px 档，兼顾清晰度与加载速度（懒加载，每屏仅约20张）。"""
import os, shutil, io
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

SRC, DST = "/workspace", "/workspace/发布版"
if os.path.exists(DST): shutil.rmtree(DST)
os.makedirs(DST)
shutil.copy(f"{SRC}/index.html", f"{DST}/index.html")
shutil.copytree(f"{SRC}/images", f"{DST}/images")

MAXEDGE, JQ, WQ, THRESH = 900, 66, 62, 200*1024
renames = {}

def compress(p):
    rel = os.path.relpath(p, DST)
    try:
        ext = p.lower().rsplit(".", 1)[-1]
        im = Image.open(p); w, h = im.size
        if max(w, h) > MAXEDGE:
            r = MAXEDGE/max(w, h); im = im.resize((int(w*r), int(h*r)), Image.LANCZOS)
        if ext in ("jpg","jpeg"):
            if os.path.getsize(p) < THRESH and max(w,h) <= MAXEDGE: return
            im.convert("RGB").save(p,"JPEG",quality=JQ,optimize=True,progressive=True)
        elif ext == "webp":
            im.save(p,"WEBP",quality=WQ,method=4)
        elif ext == "png":
            im = im.convert("RGB"); np = p.rsplit(".",1)[0]+".jpg"
            im.save(np,"JPEG",quality=JQ,optimize=True,progressive=True); os.remove(p)
            renames[rel] = os.path.relpath(np, DST)
    except Exception: pass

paths=[os.path.join(r,f) for r,_,fs in os.walk(f"{DST}/images") for f in fs]
print("压缩", len(paths), "个文件 ...")
with ThreadPoolExecutor(max_workers=10) as ex: list(ex.map(compress, paths))
if renames:
    s=io.open(f"{DST}/index.html",encoding="utf-8").read()
    for o,n in renames.items(): s=s.replace('"'+o+'"','"'+n+'"')
    io.open(f"{DST}/index.html","w",encoding="utf-8").write(s)
    print("同步", len(renames), "处 png->jpg 引用")
t=sum(os.path.getsize(os.path.join(r,f)) for r,_,fs in os.walk(f"{DST}/images") for f in fs)
print(f"images: {t/1048576:.1f} MB")
