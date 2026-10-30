# -*- coding: utf-8 -*-
"""兼容性修复：aspect-ratio/inset 替换为全浏览器兼容写法
   aspect-ratio 需 Chrome88+；国产浏览器/微信X5/旧Edge 常停留在 Chromium 86，
   不支持时卡片图高度塌陷 => 整个网格错乱。"""
import re, io, shutil
from PIL import Image

FILES = ["index.html", "index_online.html",
         "节日工作台数据库/工作台文件/index.html",
         "节日工作台数据库/工作台文件/index_online.html"]

OLD_IMG_CSS = ".card-img{position:relative;overflow:hidden;background:#f1efe9;aspect-ratio:1/1}\n.card-img img{display:block;width:100%;height:100%;object-fit:cover}"
NEW_IMG_CSS = (".card-img{position:relative;overflow:hidden;background:#f1efe9}\n"
               ".card-img::before{content:\"\";display:block;padding-top:100%}\n"  # 1:1 兼容写法
               ".card-img img{position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover}")

OLD_MODAL = ".modal{position:fixed;inset:0;z-index:50;display:flex}"
NEW_MODAL = ".modal{position:fixed;left:0;top:0;right:0;bottom:0;z-index:50;display:flex}"
OLD_BACK  = ".lb-backdrop{position:absolute;inset:0;background:rgba(20,17,14,.55)}"
NEW_BACK  = ".lb-backdrop{position:absolute;left:0;top:0;right:0;bottom:0;background:rgba(20,17,14,.55)}"

for f in FILES:
    s = io.open(f, encoding="utf-8").read()
    n = 0
    if OLD_IMG_CSS in s:
        s = s.replace(OLD_IMG_CSS, NEW_IMG_CSS); n += 1
    else:
        # 容错：可能已被换行差异影响
        s2 = re.sub(r"\.card-img\{[^}]*aspect-ratio:1/1\}",
                    ".card-img{position:relative;overflow:hidden;background:#f1efe9}", s)
        s2 = s2.replace(".card-img img{display:block;width:100%;height:100%;object-fit:cover}",
                        ".card-img::before{content:\"\";display:block;padding-top:100%}\n.card-img img{position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover}")
        if s2 != s: s = s2
        n += 1
    if OLD_MODAL in s: s = s.replace(OLD_MODAL, NEW_MODAL); n += 1
    if OLD_BACK in s:  s = s.replace(OLD_BACK, NEW_BACK); n += 1
    io.open(f, "w", encoding="utf-8").write(s)
    print(f, "patched", n)
