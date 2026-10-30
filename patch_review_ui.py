# -*- coding: utf-8 -*-
"""人工审核功能：待审核条目可通过/剔除，结果写入 localStorage 并可导出 JSON。"""
import io

FILES = ["index.html","index_online.html",
         "节日工作台数据库/工作台文件/index.html",
         "节日工作台数据库/工作台文件/index_online.html"]

# ---------- 1) CSS ----------
OLD_CSS = ".badge-pending{position:absolute;right:8px;bottom:8px;background:#d97706;color:#fff;font-size:11px;border-radius:5px;padding:2px 7px;font-weight:600}"
NEW_CSS = OLD_CSS + """
.card-actions{display:flex;gap:6px;margin-top:7px}
.card-actions .act{flex:1;border:none;border-radius:6px;padding:5px 0;font-size:12px;cursor:pointer;font-weight:600;font-family:inherit;line-height:1.2}
.card-actions .act.pass{background:#1c6b52;color:#fff}
.card-actions .act.pass:hover{background:#155a44}
.card-actions .act.rej{background:#fdf1ee;color:#a33a24;border:1px solid #e8cfc8}
.card-actions .act.rej:hover{background:#f8e2dc}
.review-stat{font-size:12px;color:var(--ink-3);padding:6px 2px 8px;line-height:1.7}
.review-stat b{color:#d97706;font-size:13px}
.review-banner{display:flex;align-items:center;gap:10px;flex-wrap:wrap;padding:9px 12px;margin:10px 2px 0;background:#fff7ed;border:1px solid #fed7aa;border-radius:8px;font-size:13px;color:#9a3412}
.review-banner .sp{flex:1}
.btn.pass{background:#1c6b52;border-color:#1c6b52;color:#fff}
.btn.rej{background:#fdf1ee;border:1px solid #e8cfc8;color:#a33a24}"""

# ---------- 2) 卡片审核条（仅审核模式显示，保证等高） ----------
OLD_CARD = """      (sub?'<div class="card-sub">'+esc(sub)+'</div>':"")+meter+'</div></article>';"""
NEW_CARD = """      (sub?'<div class="card-sub">'+esc(sub)+'</div>':"")+meter+
      ((pending&&state.filters.pending)?('<div class="card-actions">'+
        '<button class="act pass" data-act="pass" data-id="'+it.id+'">✓ 通过</button>'+
        '<button class="act rej" data-act="reject" data-id="'+it.id+'">✗ 剔除</button></div>'):"")+
      '</div></article>';"""

# ---------- 3) 核心审核逻辑（插在 renderGrid 前） ----------
OLD_RG = "function renderGrid(){"
NEW_RG = """var REVIEW_KEY="wb_review_v1";
function loadReview(){ try{ return JSON.parse(localStorage.getItem(REVIEW_KEY)||"{}"); }catch(e){ return {}; } }
function saveReview(r){ try{ localStorage.setItem(REVIEW_KEY, JSON.stringify(r)); }catch(e){} }
var REVIEW = loadReview();
var reviewStack = [];
function pendingCount(){ var n=0; DATA.forEach(function(d){ if(d.review_status==="待人工审核") n++; }); return n; }
function applyReview(){
  Object.keys(REVIEW).forEach(function(id){
    var it=DATA.find(function(x){ return String(x.id)===String(id); });
    if(!it) return;
    if(REVIEW[id].act==="pass"){ it.review_status="已人工审核"; }
    else { var i=DATA.indexOf(it); if(i>=0) DATA.splice(i,1); }
  });
}
function doReview(id, act){
  var it=DATA.find(function(x){ return x.id===id; });
  if(!it) return;
  reviewStack.push({act:act, item:JSON.parse(JSON.stringify(it))});
  REVIEW[String(id)]={act:act, at:new Date().toISOString()};
  saveReview(REVIEW);
  if(act==="pass"){
    if(!it.holiday){
      var m=/视觉复审剔除\\(([^)]+)\\)/.exec(it.holiday_reason||"");
      if(m) it.holiday=m[1];
    }
    it.review_status="已人工审核";
    it.review_note="人工通过于 "+new Date().toISOString().slice(0,10);
  } else {
    var i=DATA.indexOf(it); if(i>=0) DATA.splice(i,1);
    var lb=$("#lightbox");
    if(!lb.hidden){ nextPending(); renderReviewStat(); refresh(); return; }
  }
  renderReviewStat();
  refresh();
}
function undoReview(){
  var last=reviewStack.pop(); if(!last) return;
  delete REVIEW[String(last.item.id)]; saveReview(REVIEW);
  if(last.act==="pass"){
    var it=DATA.find(function(x){ return x.id===last.item.id; });
    if(it){ it.review_status=last.item.review_status; it.holiday=last.item.holiday; it.holiday_reason=last.item.holiday_reason; it.review_note=last.item.review_note; }
  } else { DATA.push(last.item); }
  renderReviewStat(); refresh();
}
function nextPending(){
  var list=DATA.filter(function(d){ return d.review_status==="待人工审核"; });
  if(!list.length){ $$(".modal").forEach(function(m){ m.hidden=true; }); state.current=null; return; }
  openLightbox(list[0].id);
}
function exportReview(){
  var ps=[], rj=[];
  Object.keys(REVIEW).forEach(function(k){ (REVIEW[k].act==="pass"?ps:rj).push(Number(k)); });
  var out={exported_at:new Date().toISOString(), passed:ps, rejected:rj, decisions:REVIEW};
  var blob=new Blob([JSON.stringify(out,null,2)],{type:"application/json"});
  var a=document.createElement("a");
  a.href=URL.createObjectURL(blob);
  a.download="人工审核结果_"+new Date().toISOString().slice(0,10)+".json";
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(function(){ URL.revokeObjectURL(a.href); },3000);
}
function renderReviewStat(){
  var n=pendingCount(), done=0;
  Object.keys(REVIEW).forEach(function(k){ if(REVIEW[k].act==="pass") done++; });
  var el=$("#reviewStat");
  if(el) el.innerHTML="待审核 <b>"+n+"</b> 条<br>本次已通过 "+done+" 条";
  var bn=$("#reviewBanner");
  if(bn){
    if(state.filters.pending&&n>0){
      bn.style.display="";
      bn.innerHTML="审核模式：逐张确认，点 <b>✓ 通过</b> 保留，点 <b>✗ 剔除</b> 移出图池（剩余 "+n+" 条）<span class=\"sp\"></span>"+
        '<button class="btn ghost small" id="bnUndo">撤销上一次</button>';
      var u=$("#bnUndo"); if(u) u.onclick=undoReview;
    } else { bn.style.display="none"; bn.innerHTML=""; }
  }
  var lb=$("#lightbox");
  if(lb&&!lb.hidden&&state.current){
    var pend=state.current.review_status==="待人工审核";
    ["lbPass","lbReject"].forEach(function(k){ var e2=$("#"+k); if(e2){ e2.hidden=!pend; e2.dataset.id=state.current.id; } });
  }
}
function renderGrid(){"""

# ---------- 4) 事件委托：审核按钮优先 ----------
OLD_BIND = """  document.addEventListener("click",function(e){
    var sb=e.target.closest("[data-scope]");"""
NEW_BIND = """  document.addEventListener("click",function(e){
    var ab=e.target.closest("[data-act]");
    if(ab){ doReview(Number(ab.dataset.id), ab.dataset.act); return; }
    var sb=e.target.closest("[data-scope]");"""

# ---------- 5) 侧栏：审核统计 + 撤销/导出 ----------
OLD_SIDE = """      <label data-page-node-id="tJiKMJQW71Fv1lnNLYDsX2" class="checkline"><input data-page-node-id="SiM8Glaot0wlXDkaSNFLgU" id="pendingOnly" type="checkbox"><!--pnid:O02jnyXiJ5V22kgOiWY82Q--> 只看待人工审核</label>"""
NEW_SIDE = OLD_SIDE + """
      <div class="review-stat" id="reviewStat"></div>
      <button data-page-node-id="rbUndo" class="btn ghost small block" id="btnUndoReview">撤销上一次审核</button>
      <button data-page-node-id="rbExp" class="btn ghost small block" id="btnExportReview">导出审核结果</button>"""

# ---------- 6) 顶部审核模式横幅 ----------
OLD_ECHIP = """    <div class="element-chips" id="elementChips" style="display:none"></div>"""
NEW_ECHIP = OLD_ECHIP + """
    <div class="review-banner" id="reviewBanner" style="display:none"></div>"""

# ---------- 7) 灯箱按钮 ----------
OLD_LBA = """class="lb-actions"><a data-page-node-id="Oi3oktEkpEx3D0wkXS1NlW" class="btn primary small" id="lbSource" rel="noopener" target="_blank"><!--pnid:68BND0HIGTZPHRDMnsGUXQ-->打开来源页</a></div>"""
NEW_LBA = """class="lb-actions"><a data-page-node-id="Oi3oktEkpEx3D0wkXS1NlW" class="btn primary small" id="lbSource" rel="noopener" target="_blank"><!--pnid:68BND0HIGTZPHRDMnsGUXQ-->打开来源页</a><button class="btn pass small" id="lbPass" data-act="pass" hidden>✓ 通过</button><button class="btn rej small" id="lbReject" data-act="reject" hidden>✗ 剔除</button><button class="btn ghost small" id="lbNext">下一条待审核 →</button></div>"""

# ---------- 8) 绑定按钮 + 启动时应用审核结果 ----------
OLD_EV = """  $("#pendingOnly").addEventListener("change",function(e){state.filters.pending=e.target.checked;refresh();});"""
NEW_EV = OLD_EV + """
  if($("#btnUndoReview"))$("#btnUndoReview").addEventListener("click",undoReview);
  if($("#btnExportReview"))$("#btnExportReview").addEventListener("click",exportReview);
  if($("#lbNext"))$("#lbNext").addEventListener("click",nextPending);"""

OLD_INIT = "buildScope(); bind(); refresh();"
NEW_INIT = "applyReview(); buildScope(); bind(); renderReviewStat(); refresh();"

# ---------- 9) refresh 里同步审核统计 ----------
OLD_REF = "  renderSummary(); renderElementChips(); renderGrid(); buildSidebar(); buildScope();"
NEW_REF = "  renderSummary(); renderElementChips(); renderGrid(); buildSidebar(); buildScope(); renderReviewStat();"

# ---------- 10) 键盘快捷键：P 通过 / X 剔除 ----------
OLD_KEY = """    if(e.key==="ArrowRight"&&idx<state.items.length-1)openLightbox(state.items[idx+1].id);"""
NEW_KEY = """    if(e.key==="ArrowRight"&&idx<state.items.length-1)openLightbox(state.items[idx+1].id);
    if(!state.current)return;
    if(e.key==="p"||e.key==="P"){doReview(state.current.id,"pass");return;}
    if(e.key==="x"||e.key==="X"){doReview(state.current.id,"reject");return;}"""

# ---------- 11) openLightbox 末尾刷新灯箱按钮状态 ----------
OLD_LBTAIL = """  var meta=["""
NEW_LBTAIL = """  var _pend=it.review_status==="待人工审核";
  ["lbPass","lbReject"].forEach(function(k){var e2=$("#"+k);if(e2){e2.hidden=!_pend;e2.dataset.id=it.id;}});
  var meta=["""

PAIRS = [(OLD_CSS,NEW_CSS),(OLD_CARD,NEW_CARD),(OLD_RG,NEW_RG),(OLD_BIND,NEW_BIND),
         (OLD_SIDE,NEW_SIDE),(OLD_ECHIP,NEW_ECHIP),(OLD_LBA,NEW_LBA),(OLD_EV,NEW_EV),
         (OLD_INIT,NEW_INIT),(OLD_REF,NEW_REF),(OLD_KEY,NEW_KEY),(OLD_LBTAIL,NEW_LBTAIL)]

for f in FILES:
    s = io.open(f, encoding="utf-8").read()
    for o, n in PAIRS:
        assert o in s, (f, o[:60])
        s = s.replace(o, n, 1)
    io.open(f, "w", encoding="utf-8").write(s)
    print("ok", f)
