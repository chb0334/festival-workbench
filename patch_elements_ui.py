# -*- coding: utf-8 -*-
"""前端：元素筛选 chips（随节日联动、计数联动、复用 toggle 逻辑）"""
import io
FILES=["index.html","index_online.html","节日工作台数据库/工作台文件/index.html","节日工作台数据库/工作台文件/index_online.html"]

# 1) matchesF 增加 element 过滤
old_f='if(skip!=="evidence_type" && f.evidence_type && it.evidence_type!==f.evidence_type) return false;'
new_f=old_f+'\n  if(skip!=="element" && f.element && (it.elements||"").split(",").indexOf(f.element)<0) return false;'

# 2) state.filters 初始化加 element
old_s='state.filters={year:"",holiday:"",platform:"",'
new_s='state.filters={year:"",holiday:"",element:"",platform:"",'

# 3) 元素清单常量（插在 renderSummary 前）
old_r='function renderSummary(){'
new_r='''var ELEMENTS={
"万圣节":["南瓜","南瓜灯","骷髅","幽灵","蝙蝠","蜘蛛/蛛网","女巫","黑猫","科学怪人","木乃伊","吸血鬼","糖果/零食"],
"感恩节":["火鸡","南瓜","南瓜派","枫叶/秋叶","丰收","玉米","蔓越莓","向日葵"],
"圣诞节":["圣诞树","圣诞老人","驯鹿","雪人","松枝/花环","槲寄生","胡桃夹子","姜饼","糖果杖"]
};
function renderElementChips(){
  var box=$("#elementChips"); if(!box) return;
  var list=ELEMENTS[state.filters.holiday];
  if(!list){ box.style.display="none"; box.innerHTML=""; return; }
  box.style.display="";
  var nOf=function(e){var n=0;DATA.forEach(function(d){if(matchesF(d,"element")&&(d.elements||"").split(",").indexOf(e)>=0)n++;});return n;};
  var html='<span class="el-label">元素</span>'+'<button class="chip'+(state.filters.element===""?" active":"")+'" data-filter="element" data-v="">全部<span class="n">'+DATA.filter(function(d){return matchesF(d,"element");}).length+'</span></button>';
  list.forEach(function(e){
    var n=nOf(e);
    html+='<button class="chip'+(state.filters.element===e?" active":"")+(n===0?" zero":"")+'" data-filter="element" data-v="'+esc(e)+'">'+esc(e)+'<span class="n">'+n+'</span></button>';
  });
  box.innerHTML=html;
}
function renderSummary(){'''

# 4) 摘要栏后渲染元素行
old_c="  renderSummary(); renderGrid(); buildSidebar(); buildScope();"
new_c="  renderSummary(); renderElementChips(); renderGrid(); buildSidebar(); buildScope();"

# 5) 换节日时清空不属于该节日的元素（在 data-scope 点击处理里）
old_b='if(sb){state.filters[sb.dataset.scope]=sb.dataset.v;buildScope();refresh();return;}'
new_b='if(sb){state.filters[sb.dataset.scope]=sb.dataset.v;if(sb.dataset.scope==="holiday"&&ELEMENTS[sb.dataset.v]&&state.filters.element&&ELEMENTS[sb.dataset.v].indexOf(state.filters.element)<0)state.filters.element="";buildScope();refresh();return;}'

# 6) summaryBar 后加容器（HTML）
old_h='<section data-page-node-id="sOMN2lJSmKMmf1LxYprzOH" class="summary-bar" id="summaryBar"></section>'
new_h=old_h+'\n    <div class="element-chips" id="elementChips" style="display:none"></div>'

# 7) CSS
old_css='.chip-static{display:inline-block;'
new_css='.element-chips{display:flex;flex-wrap:wrap;gap:8px;align-items:center;padding:10px 2px 2px}\n.element-chips .el-label{font-size:12px;color:var(--ink-3);font-weight:600;margin-right:2px}\n.chip-static{display:inline-block;'

for f in FILES:
    s=io.open(f,encoding="utf-8").read()
    for o,n in [(old_f,new_f),(old_s,new_s),(old_r,new_r),(old_c,new_c),(old_b,new_b),(old_h,new_h),(old_css,new_css)]:
        assert o in s,(f,o[:40])
        s=s.replace(o,n,1)
    io.open(f,"w",encoding="utf-8").write(s)
    print("ok",f)
