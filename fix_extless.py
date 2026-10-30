# -*- coding: utf-8 -*-
import io, os
from PIL import Image
FILES = ["index.html", "index_online.html",
         "节日工作台数据库/工作台文件/index.html",
         "节日工作台数据库/工作台文件/index_online.html"]
# 找出所有无扩展名/怪后缀的 images/remote 引用
import re
names=set()
for f in FILES:
    s=io.open(f,encoding="utf-8").read()
    names |= set(re.findall(r'images/remote/([A-Za-z0-9._-]+)', s))
bad=[n for n in names if not n.lower().endswith(('.jpg','.jpeg','.png','.webp','.gif'))]
print("extless refs:", bad)
for n in bad:
    src=os.path.join("images/remote",n)
    if not os.path.exists(src):
        print("  MISSING on disk:",n); continue
    dst=src+".jpg"
    im=Image.open(src).convert("RGB")
    im.save(dst,"JPEG",quality=88)
    os.remove(src)
    print("  ->",dst,im.size)
    for f in FILES:
        s=io.open(f,encoding="utf-8").read()
        if "images/remote/"+n in s:
            io.open(f,"w",encoding="utf-8").write(s.replace("images/remote/"+n,"images/remote/"+n+".jpg"))
            print("    ref updated in",f)
