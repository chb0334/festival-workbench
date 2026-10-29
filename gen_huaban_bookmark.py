#!/usr/bin/env python3.11
"""生成「花瓣图下载」书签安装页 huaban_img_downloader.html。

白名单 hash 从工作台四份副本实时提取（去重），保证书签只下载工作台
实际引用的 201 张图，不多下、不漏下。
"""
import re, json, os

# ---- 从工作台提取花瓣网图片 hash（与 fix_huaban_imgs.py 同规则）----
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

s = open("index.html", encoding="utf-8").read()
st, en = extract_arr(s)
arr = json.loads(s[st:en + 1])
hb = [r for r in arr if r.get("platform") == "花瓣网"]
hashes = sorted({hash_of(r.get("img", "")) for r in hb} - {None})
print("花瓣网记录:", len(hb), "| 唯一 hash:", len(hashes))

WL = ",\n".join('    "%s"' % h for h in hashes)

# ---- 书签 JS（自动滚动加载 + 多源抓取 + 确认 + 批量下载）----
JS = r"""(function(){
  var WL=[__WL__];
  var set={}; WL.forEach(function(h){set[h]=1;});
  var best={};
  function rank(u){ if(/fw658|fw720|fw960|fw1000/.test(u))return 5; if(/fw240|fw320|fw336/.test(u))return 4; if(/crop/.test(u))return 3; if(/sq\d/.test(u))return 1; return 2; }
  function add(u){ if(!u)return; for(var k in set){ if(u.indexOf(k)>=0){ if(!best[k]||rank(u)>rank(best[k])) best[k]=u; break; } } }
  function collect(){
    [].forEach.call(document.images,function(im){
      add(im.src); add(im.getAttribute('data-src'));
      var ss=im.getAttribute('srcset'); if(ss){ ss.split(',').forEach(function(p){ add(p.trim().split(/\s+/)[0]); }); }
    });
    [].forEach.call(document.querySelectorAll('[style]'),function(el){
      var m=(el.getAttribute('style')||'').match(/url\(\s*['"]?([^'")]+)['"]?\s*\)/g);
      if(m){ m.forEach(function(x){ var u=x.replace(/.*url\(\s*['"]?/,'').replace(/['"]?\s*\)\s*$/,''); add(u); }); }
    });
    [].forEach.call(document.querySelectorAll('iframe'),function(f){
      try{ var d=f.contentDocument; if(d){ [].forEach.call(d.images,function(im){ add(im.src); add(im.getAttribute('data-src')); }); } }catch(e){}
    });
    try{
      var raw=document.documentElement.innerHTML.replace(/\\\//g,'/');
      var re=/[a-z0-9.\-]*hbimg[^"'\s<>\\]*/g, m2;
      while((m2=re.exec(raw))){ add('https://'+m2[0]); }
    }catch(e){}
  }
  var box=document.createElement('div');
  box.style.cssText='position:fixed;left:12px;top:12px;z-index:2147483647;background:#000d;color:#0f0;padding:10px 14px;border-radius:10px;font:14px/1.5 monospace;max-width:340px';
  box.textContent='正在自动滚动加载图片…'; document.body.appendChild(box);
  var n=0;
  (function scroll(){
    window.scrollBy(0,1500); n++;
    if(n<45){ setTimeout(scroll,350); } else { setTimeout(load,3500); }
  })();
  function load(){
    box.textContent='正在收集图片…'; collect();
    var keys=Object.keys(best);
    if(!keys.length){
      var im0=document.images[0];
      var sample=im0?String(im0.src||im0.getAttribute('data-src')||'(空src)').slice(0,110):'页面0张img';
      box.innerHTML='<div style="color:#f66">✗ 没匹配到白名单图</div><div style="color:#aaa;font-size:12px;margin-top:6px">诊断：本页img数='+document.images.length+'<br>样例: '+sample+'<br><br>①确认打开的是指定6个搜索页之一(别用首页/别的关键词)<br>②等图片显示出来再点书签<br>③还不行就把本截图发给助手</div>';
      return;
    }
    if(!confirm('将下载 '+keys.length+' 张花瓣图（白名单共 '+WL.length+' 张）。\n点“确定”开始，浏览器可能要求“允许多次下载”。')){ box.textContent='已取消'; return; }
    var i=0;
    (function next(){
      if(i>=keys.length){ box.textContent='✓ 完成，共下载 '+keys.length+' 张，去下载文件夹查看'; return; }
      var u=best[keys[i]];
      var a=document.createElement('a'); a.href=u; a.download=keys[i]+'.webp';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      box.textContent='下载中 '+(i+1)+'/'+keys.length; i++; setTimeout(next,350);
    })();
  }
})();""".replace("__WL__", WL)

HREF = "javascript:" + (JS.replace('"', '&quot;').replace('<', '&lt;').replace('>', '&gt;').replace('\n', ' '))

# ---- 安装页 HTML（含超详细步骤）----
HTML = r"""<!DOCTYPE html>
<html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>安装「花瓣图下载」书签</title></head>
<body style="font-family:-apple-system,Segoe UI,Arial,sans-serif;max-width:720px;margin:40px auto;padding:0 20px;line-height:1.85;color:#222">
<h2>安装「花瓣图下载」书签</h2>
<p>下面橙色按钮是<b>书签链接</b>。用鼠标<b>按住拖到浏览器收藏夹栏</b>松手即装好，<u>不用复制代码</u>。</p>
<p style="background:#fff7e6;border:1px solid #ffd591;padding:10px 14px;border-radius:8px;font-size:14px">⚠️ 直接<b>拖</b>，<b>别右键复制链接/手动粘贴</b>，会弄坏代码。</p>
<div style="text-align:center;margin:26px 0">
<a id="bm" href="__HREF__" style="display:inline-block;background:#ff9900;color:#fff;padding:16px 26px;border-radius:12px;font-size:17px;font-weight:700;text-decoration:none;cursor:grab;box-shadow:0 3px 12px rgba(255,153,0,.4)">📥 拖我到收藏夹栏：花瓣图下载</a>
</div>

<h3>一、先把书签装好（只做一次）</h3>
<ol style="font-size:14px">
<li><b>显示收藏夹栏</b>（书签要放在这里）：
  <ul>
    <li>Chrome/Edge：按 <code>Ctrl+Shift+B</code>（Mac 是 <code>Cmd+Shift+B</code>）；或右键浏览器顶部地址栏右侧空白处 → 勾选「显示书签栏」。</li>
    <li>Firefox：菜单 ☰ →「书签」→ 勾选「书签工具栏」。</li>
  </ul></li>
<li>用<b>鼠标左键按住上面橙色按钮</b>，拖到<b>收藏夹栏</b>上任意位置松手。收藏夹栏里出现一个名为「花瓣图下载」的按钮，即装好。</li>
<li>（验证）点一下收藏夹栏的「花瓣图下载」——此刻不在花瓣网，它会提示“本页没匹配到花瓣图”，说明书签已生效，关掉提示即可。</li>
</ol>

<h3>二、下载 201 张图（每个节日页跑一次，共 6 次）</h3>
<ol style="font-size:14px">
<li>在<b>地址栏</b>逐个打开下面 6 个搜索页（整段复制，每行一个，粘到地址栏回车；中文直接粘就行）：
<pre style="background:#f5f5f5;padding:10px;border-radius:6px;font-size:12px;white-space:pre-wrap">https://huaban.com/search/?q=万圣节
https://huaban.com/search/?q=感恩节
https://huaban.com/search/?q=圣诞节
https://huaban.com/search/?q=复活节
https://huaban.com/search/?q=情人节
https://huaban.com/search/?q=独立日</pre>
<div style="font-size:12px;color:#888">若打开后是空白/要求登录，先登录花瓣网再重开；若页面打不开，去掉 URL 里的斜杠试 <code>https://huaban.com/search?q=万圣节</code>。</div></li>
<li>页面打开后，<b>点收藏夹栏的「花瓣图下载」</b>。书签会<b>自动向下滚动</b>（约 15 秒）把图片加载出来，然后弹窗显示“将下载 N 张”。</li>
<li>弹窗点<b>「确定」</b>开始下载。浏览器右上角可能弹出“是否允许下载多个文件”→ 点<b>「允许」</b>（务必点允许，否则只下一张）。</li>
<li>左上角绿色提示变成“✓ 完成”即该页下载完。若想更保险，<b>手动再滚一下页面</b>到底，重跑一次书签（重复文件浏览器会覆盖，无害）。</li>
<li>把这 6 个页面<b>各跑一遍</b>，下载文件夹里会累积一批 <code>&lt;hash&gt;.webp</code> 文件，总共 <b>201 个</b>。</li>
</ol>

<h3>三、把图放进仓库（二选一）</h3>
<p style="font-size:14px"><b>方法 A（最简单，网页操作，无需 git）：</b></p>
<ol style="font-size:14px">
<li>打开你的 GitHub 仓库页面，进入 <code>images/huaban/</code> 目录（没有就新建文件夹）。</li>
<li>点 <b>Add file → Upload files</b>，把下载文件夹里的 <b>201 个 .webp</b> 一次性拖进去，写个提交说明，<b>Commit changes</b>。</li>
</ol>
<p style="font-size:14px"><b>方法 B（本地 git，适合熟练）：</b></p>
<ol style="font-size:14px">
<li>把 201 个 .webp 复制到仓库的 <code>images/huaban/</code> 目录。</li>
<li>命令行：<code>git add images/huaban/ &amp;&amp; git commit -m "add huaban images" &amp;&amp; git push</code>。</li>
</ol>

<h3>四、告诉我一声</h3>
<p style="font-size:14px">图传上去后，跟我说“图传好了”，我立刻跑 <code>fix_huaban_imgs.py</code> 改写工作台引用（按 hash 精准匹配）、提交并发布。之后<b>永久有图，不再受花瓣签名过期影响</b>。若我这边 dry-run 发现还缺几张，会告诉你具体缺哪些 hash，你补下即可。</p>

<p style="color:#888;font-size:13px;border-top:1px solid #eee;padding-top:12px">原理：花瓣图只有你本机浏览器（已登录/过验证）才取得到字节——沙箱数据中心 IP 被花瓣 CDN 封（HTTP 567）且花瓣禁跨域，所以我无法代下。书签在你浏览器里把图存成本地文件，再由仓库托管，一劳永逸。</p>
</body></html>""".replace("__HREF__", HREF)

with open("huaban_img_downloader.html", "w", encoding="utf-8") as f:
    f.write(HTML)
print("已生成 huaban_img_downloader.html（字节:", os.path.getsize("huaban_img_downloader.html"), "）")
