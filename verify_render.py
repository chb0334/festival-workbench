#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""渲染校验：卡片数、裂图数、等高。供 auto_crawl_15d.py 调用。"""
from playwright.sync_api import sync_playwright
import pathlib
p = pathlib.Path("/workspace/index.html").resolve()
with sync_playwright() as pw:
    b = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
    pg = b.new_page(viewport={"width": 1400, "height": 1000})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(p.as_uri(), wait_until="networkidle")
    pg.wait_for_timeout(800)
    pg.evaluate("async()=>{for(let y=0;y<document.body.scrollHeight;y+=900){window.scrollTo(0,y);await new Promise(r=>setTimeout(r,40));}window.scrollTo(0,0);}")
    pg.wait_for_timeout(1500)
    r = pg.evaluate("""()=>{const c=[...document.querySelectorAll('.grid .card')];
      const i=[...document.querySelectorAll('.grid .card-img img')];
      // 仅检查本地图片(images/ 开头)；远程 CDN 图在沙箱无法加载，不应误判为裂图
      const local=i.filter(x=>/^(images\\/|file:\\/\\/.*\\/images\\/)/.test(x.getAttribute('src')||''));
      return {cards:c.length, broken:local.filter(x=>!x.complete||x.naturalWidth===0).length,
              h:[...new Set(c.map(x=>Math.round(x.getBoundingClientRect().height)))],
              w:[...new Set(c.map(x=>Math.round(x.getBoundingClientRect().width)))]};}""")
    print("渲染校验:", r, "| JS错误:", errs[:3])
    bad = r["broken"] > 0 or r["cards"] == 0 or len(r["h"]) > 1 or errs
    b.close()
    raise SystemExit(1 if bad else 0)
