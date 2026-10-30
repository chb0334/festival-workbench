# -*- coding: utf-8 -*-
"""收藏功能：卡片星标、灯箱收藏键、只看收藏筛选、localStorage持久化、导出含收藏。"""
import io

FILES = ["index.html","index_online.html",
         "节日工作台数据库/工作台文件/index.html",
         "节日工作台数据库/工作台文件/index_online.html"]

PAIRS = []

# 1) CSS
PAIRS.append((
 '.badge-pending{position:absolute;right:8px;bottom:8px;background:#d97706;color:#fff;font-size:11px;border-radius:5px;padding:2px 7px;font-weight:600}',
 '.badge-pending{position:absolute;right:8px;bottom:8px;background:#d97706;color:#fff;font-size:11px;border-radius:5px;padding:2px 7px;font-weight:600}\n'
 '.badge-fav{position:absolute;left:8px;bottom:8px;z-index:2;border:none;background:rgba(30,28,25,.55);color:rgba(255,255,255,.8);width:28px;height:28px;border-radius:50%;font-size:15px;cursor:pointer;line-height:1;padding:0}\n'
 '.badge-fav:hover{background:rgba(30,28,25,.85);color:#fff}\n'
 '.badge-fav.on{background:#d97706;color:#fff}\n'
 '#lbFav.on{background:#d97706;border-color:#d97706;color:#fff}'))

# 2) 筛选逻辑
PAIRS.append((
 '  if(f.pending && it.review_status!=="待人工审核") return false;',
 '  if(f.pending && it.review_status!=="待人工审核") return false;\n  if(f.fav && !it.favorite) return false;'))

# 3) state 初始 + 重置
PAIRS.append((
 'var state = { filters:{year:"",holiday:"",platform:"",design_type:"",evidence_type:"",collected_by:"",month:"",q:"",has_evidence:false,pending:false}, sort:"heat"',
 'var state = { filters:{year:"",holiday:"",platform:"",design_type:"",evidence_type:"",collected_by:"",month:"",q:"",has_evidence:false,pending:false,fav:false}, sort:"heat"'))
PAIRS.append((
 'state.filters={year:"",holiday:"",element:"",platform:"",design_type:"",evidence_type:"",collected_by:"",month:"",q:"",has_evidence:false,pending:false};',
 'state.filters={year:"",holiday:"",element:"",platform:"",design_type:"",evidence_type:"",collected_by:"",month:"",q:"",has_evidence:false,pending:false,fav:false};'))
PAIRS.append((
 '$("#searchInput").value="";$("#evidenceOnly").checked=false;$("#pendingOnly").checked=false;',
 '$("#searchInput").value="";$("#evidenceOnly").checked=false;$("#pendingOnly").checked=false;if($("#favOnly"))$("#favOnly").checked=false;'))

# 4) 卡片收藏星（图片左下角）
PAIRS.append((
 """      (pending?'<span class="badge-pending">待审核</span>':"")+""",
 """      (pending?'<span class="badge-pending">待审核</span>':"")+
      '<button class="badge-fav'+(it.favorite?" on":"")+'" data-favid="'+it.id+'" title="收藏">★</button>'+"""))

# 5) 收藏核心逻辑（插在 function renderGrid 前）
PAIRS.append((
 'function renderGrid(){',
 """var FAV_KEY="wb_fav_v1";
function loadFavs(){ try{ return JSON.parse(localStorage.getItem(FAV_KEY)||"[]"); }catch(e){ return []; } }
function saveFavs(a){ try{ localStorage.setItem(FAV_KEY, JSON.stringify(a)); }catch(e){} }
function applyFavs(){ var a=loadFavs(); DATA.forEach(function(d){ if(a.indexOf(String(d.id))>=0) d.favorite=true; }); }
function favCount(){ var n=0; DATA.forEach(function(d){ if(d.favorite) n++; }); return n; }
function toggleFav(id){
  var it=DATA.find(function(x){ return x.id===id; }); if(!it) return;
  it.favorite=!it.favorite;
  var a=loadFavs(), k=String(id);
  if(it.favorite){ if(a.indexOf(k)<0) a.push(k); } else { a=a.filter(function(x){ return x!==k; }); }
  saveFavs(a);
  renderGrid(); renderReviewStat();
  var lf=$("#lbFav");
  if(lf&&state.current&&state.current.id===id){ lf.classList.toggle("on",it.favorite); lf.innerHTML=it.favorite?"★ 已收藏":"☆ 收藏"; }
}
function renderGrid(){"""))

# 6) 事件委托（在 data-act 之后）
PAIRS.append((
 """    if(ab){ doReview(Number(ab.dataset.id), ab.dataset.act); return; }""",
 """    if(ab){ doReview(Number(ab.dataset.id), ab.dataset.act); return; }
    var fv=e.target.closest("[data-favid]");
    if(fv){ toggleFav(Number(fv.dataset.favid)); return; }"""))

# 7) 侧栏：只看收藏（放在"只看待人工审核"后）
PAIRS.append((
 """<!--pnid:O02jnyXiJ5V22kgOiWY82Q--> 只看待人工审核</label>""",
 """<!--pnid:O02jnyXiJ5V22kgOiWY82Q--> 只看待人工审核</label>
      <label data-page-node-id="favOnlyLine" class="checkline"><input data-page-node-id="favOnlyInput" id="favOnly" type="checkbox"> 只看收藏</label>"""))

# 8) 绑定 favOnly
PAIRS.append((
 """  $("#pendingOnly").addEventListener("change",function(e){state.filters.pending=e.target.checked;refresh();});""",
 """  $("#pendingOnly").addEventListener("change",function(e){state.filters.pending=e.target.checked;refresh();});
  if($("#favOnly"))$("#favOnly").addEventListener("change",function(e){state.filters.fav=e.target.checked;refresh();});"""))

# 9) 灯箱收藏按钮
PAIRS.append((
 """<button class="btn ghost small" id="lbNext">下一条待审核 →</button>""",
 """<button class="btn ghost small" id="lbFav">☆ 收藏</button><button class="btn ghost small" id="lbNext">下一条待审核 →</button>"""))

# 10) openLightbox 同步收藏按钮状态
PAIRS.append((
 """  ["lbPass","lbReject"].forEach(function(k){var e2=$("#"+k);if(e2){e2.hidden=!_pend;e2.dataset.id=it.id;}});""",
 """  ["lbPass","lbReject"].forEach(function(k){var e2=$("#"+k);if(e2){e2.hidden=!_pend;e2.dataset.id=it.id;}});
  var lf=$("#lbFav"); if(lf){ lf.classList.toggle("on",!!it.favorite); lf.innerHTML=it.favorite?"★ 已收藏":"☆ 收藏"; }"""))

# 11) 统计里加收藏数
PAIRS.append((
 """  if(el) el.innerHTML="待审核 <b>"+n+"</b> 条<br>本次已通过 "+done+" 条";""",
 """  if(el) el.innerHTML="待审核 <b>"+n+"</b> 条 · 已收藏 <b>"+favCount()+"</b> 条<br>本次已通过 "+done+" 条";"""))

# 12) 导出含收藏
PAIRS.append((
 """  var out={exported_at:new Date().toISOString(), passed:ps, rejected:rj, decisions:REVIEW};""",
 """  var fvs=[]; DATA.forEach(function(d){ if(d.favorite) fvs.push(d.id); });
  var out={exported_at:new Date().toISOString(), passed:ps, rejected:rj, favorites:fvs, decisions:REVIEW};"""))

# 13) 启动时应用收藏
PAIRS.append((
 "applyReview(); buildScope(); bind(); renderReviewStat(); refresh();",
 "applyReview(); applyFavs(); buildScope(); bind(); renderReviewStat(); refresh();"))

for f in FILES:
    s = io.open(f, encoding="utf-8").read()
    for o, n in PAIRS:
        assert o in s, (f, o[:60])
        s = s.replace(o, n, 1)
    io.open(f, "w", encoding="utf-8").write(s)
    print("ok", f)
