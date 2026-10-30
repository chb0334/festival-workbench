#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""制作轻量离线包：图片压到适合微信/邮件传输的体积（目标<50MB），双击即看。"""
import os, shutil, io, zipfile
from PIL import Image
from concurrent.futures import ThreadPoolExecutor

SRC = "/workspace"
DST = "/workspace/离线工作台_轻量"

if os.path.exists(DST): shutil.rmtree(DST)
os.makedirs(DST)
shutil.copy(f"{SRC}/index.html", f"{DST}/index.html")
shutil.copytree(f"{SRC}/images", f"{DST}/images")

MAXEDGE = 700          # 卡片显示 210px，灯箱大图 900px 足够看清
THRESH  = 100 * 1024   # 小于150KB不再压
JQ, WQ  = 60, 55

renames = {}           # 旧相对路径 -> 新相对路径（png转jpg）

def compress(p):
    rel = os.path.relpath(p, DST)
    try:
        ext = p.lower().rsplit(".", 1)[-1]
        im = Image.open(p)
        w, h = im.size
        if max(w, h) > MAXEDGE:
            r = MAXEDGE / max(w, h)
            im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
        if ext in ("jpg", "jpeg"):
            if os.path.getsize(p) < THRESH and max(w, h) <= MAXEDGE: return
            im.convert("RGB").save(p, "JPEG", quality=JQ, optimize=True, progressive=True)
        elif ext == "webp":
            im.save(p, "WEBP", quality=WQ, method=4)
        elif ext == "png":
            im = im.convert("RGB")
            np = p.rsplit(".", 1)[0] + ".jpg"
            im.save(np, "JPEG", quality=JQ, optimize=True, progressive=True)
            os.remove(p)
            renames[rel] = os.path.relpath(np, DST)
        elif ext == "gif":
            pass
    except Exception:
        pass

paths = [os.path.join(r, f) for r, _, fs in os.walk(f"{DST}/images") for f in fs]
print(f"压缩 {len(paths)} 个文件 ...")
with ThreadPoolExecutor(max_workers=10) as ex:
    list(ex.map(compress, paths))

if renames:
    s = io.open(f"{DST}/index.html", encoding="utf-8").read()
    for old, new in renames.items():
        s = s.replace('"' + old + '"', '"' + new + '"')
    io.open(f"{DST}/index.html", "w", encoding="utf-8").write(s)
    print(f"同步 {len(renames)} 处 png->jpg 引用")

total = sum(os.path.getsize(os.path.join(r, f)) for r, _, fs in os.walk(f"{DST}/images") for f in fs)
print(f"images: {total/1048576:.1f} MB")

zp = "/workspace/节日素材工作台_轻量版.zip"
if os.path.exists(zp): os.remove(zp)
with zipfile.ZipFile(zp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for r, _, fs in os.walk(DST):
        for f in fs:
            fp = os.path.join(r, f)
            z.write(fp, os.path.relpath(fp, DST))
print(f"zip: {os.path.getsize(zp)/1048576:.1f} MB -> {zp}")
