#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""筛选联动（faceted）改造：点任一筛选，其他组的数量按当前范围联动。

改动点：
1. matches 拆出 matchesF(it, skip)：skip 指定豁免哪个筛选维度
2. counts(key, skip)：在"除该维度外"的范围内计数
3. buildSidebar：各组数量 = 其他筛选生效后的数量，"全部" = 该范围总数
4. buildScope：节日/年份 chips 增加联动数量徽标
5. renderSummary：平台分布改为当前筛选结果内的分布
"""
import sys

COPIES = [
    "index.html",
    "index_online.html",
    "节日工作台数据库/工作台文件/index.html",
    "节日工作台数据库/工作台文件/index_online.html",
]

OLD_MATCHES = """function matches(it){
  var f=state.filters;
  if(f.year && it.year!==f.year) return false;
  if(f.holiday && it.holiday!==f.holiday) return false;
  if(f.month && monthOf(it)!==f.month) return false;
  if(f.platform && it.platform!==f.platform) return false;
  if(f.design_type && it.design_type!==f.design_type) return false;
  if(f.evidence_type && it.evidence_type!==f.evidence_type) return false;
  if(f.collected_by && it.collected_by!==f.collected_by) return false;
  if(f.has_evidence && !(it.evidence_type && it.evidence_type!=="无" && it.evidence_value)) return false;
  if(f.pending && it.review_status!=="待人工审核") return false;
  if(f.q){var q=f.q.toLowerCase();var hay=[it.title,it.tags,it.brand,it.asin,it.note,it.holiday_reason,it.material,it.color,it.composition].filter(Boolean).join(" ").toLowerCase();if(hay.indexOf(q)<0)return false;}
  return true;
}"""

NEW_MATCHES = """function matchesF(it, skip){
  var f=state.filters;
  if(skip!=="year" && f.year && it.year!==f.year) return false;
  if(skip!=="holiday" && f.holiday && it.holiday!==f.holiday) return false;
  if(skip!=="month" && f.month && monthOf(it)!==f.month) return false;
  if(skip!=="platform" && f.platform && it.platform!==f.platform) return false;
  if(skip!=="design_type" && f.design_type && it.design_type!==f.design_type) return false;
  if(skip!=="evidence_type" && f.evidence_type && it.evidence_type!==f.evidence_type) return false;
  if(skip!=="collected_by" && f.collected_by && it.collected_by!==f.collected_by) return false;
  if(f.has_evidence && !(it.evidence_type && it.evidence_type!=="无" && it.evidence_value)) return false;
  if(f.pending && it.review_status!=="待人工审核") return false;
  if(f.q){var q=f.q.toLowerCase();var hay=[it.title,it.tags,it.brand,it.asin,it.note,it.holiday_reason,it.material,it.color,it.composition].filter(Boolean).join(" ").toLowerCase();if(hay.indexOf(q)<0)return false;}
  return true;
}
function matches(it){ return matchesF(it, null); }"""

OLD_COUNTS = """function counts(key){
  var m={};
  DATA.forEach(function(d){var v=d[key]||"未填";m[v]=(m[v]||0)+1;});
  return m;
}"""

NEW_COUNTS = """function counts(key, skip){
  var m={};
  DATA.forEach(function(d){ if(!matchesF(d, skip||null)) return; var v=d[key]||"未填"; m[v]=(m[v]||0)+1; });
  return m;
}"""

OLD_SB1 = "var key=g[0], el=g[1], m=counts(key);"
NEW_SB1 = ("var key=g[0], el=g[1], m=counts(key,key), base=DATA.filter(function(d){return matchesF(d,key);}).length;")

OLD_SB2 = 'var val=v==="全部"?"":v, n=v==="全部"?DATA.length:(m[v]||0);'
NEW_SB2 = 'var val=v==="全部"?"":v, n=v==="全部"?base:(m[v]||0);'

OLD_SCOPE = """  $("#yearChips").innerHTML = ["全部"].concat(years).map(function(y){var v=y==="全部"?"":y;return '<button class="chip '+(state.filters.year===v?"active":"")+'" data-scope="year" data-v="'+esc(v)+'">'+esc(y)+'</button>';}).join("");
  $("#holidayChips").innerHTML = ["全部"].concat(holidays).map(function(h){var v=h==="全部"?"":h;return '<button class="chip '+(state.filters.holiday===v?"active":"")+'" data-scope="holiday" data-v="'+esc(v)+'">'+esc(h)+'</button>';}).join("");"""

NEW_SCOPE = """  var ym=counts("year","year"), hm=counts("holiday","holiday");
  var ybase=DATA.filter(function(d){return matchesF(d,"year");}).length;
  var hbase=DATA.filter(function(d){return matchesF(d,"holiday");}).length;
  $("#yearChips").innerHTML = ["全部"].concat(years).map(function(y){var v=y==="全部"?"":y;var n=y==="全部"?ybase:(ym[y]||0);return '<button class="chip '+(state.filters.year===v?"active":"")+'" data-scope="year" data-v="'+esc(v)+'">'+esc(y)+'<span class="n">'+n+'</span></button>';}).join("");
  $("#holidayChips").innerHTML = ["全部"].concat(holidays).map(function(h){var v=h==="全部"?"":h;var n=h==="全部"?hbase:(hm[h]||0);return '<button class="chip '+(state.filters.holiday===v?"active":"")+'" data-scope="holiday" data-v="'+esc(v)+'">'+esc(h)+'<span class="n">'+n+'</span></button>';}).join("");"""

OLD_SUM = 'var plat=counts("platform"); var platText=Object.keys(plat).map(function(k){return k+" "+plat[k];}).join(" · ");'
NEW_SUM = ('var pm={}; state.items.forEach(function(d){var v=d.platform||"未填";pm[v]=(pm[v]||0)+1;});'
           ' var platText=Object.keys(pm).map(function(k){return k+" "+pm[k];}).join(" · ");')

PATCHES = [
    ("matches→matchesF", OLD_MATCHES, NEW_MATCHES),
    ("counts+skip", OLD_COUNTS, NEW_COUNTS),
    ("sidebar计数", OLD_SB1, NEW_SB1),
    ("sidebar全部", OLD_SB2, NEW_SB2),
    ("scope联动", OLD_SCOPE, NEW_SCOPE),
    ("summary平台分布", OLD_SUM, NEW_SUM),
]


def main():
    apply = "--apply" in sys.argv
    for fp in COPIES:
        s = open(fp, encoding="utf-8").read()
        ok = True
        for name, old, new in PATCHES:
            c = s.count(old)
            if c != 1:
                print(f"[{fp}] ✗ {name}: 命中 {c} 次（应为1），跳过该文件")
                ok = False
                break
        if not ok:
            continue
        if not apply:
            print(f"[{fp}] ✓ 6处补丁均可命中（dry）")
            continue
        for name, old, new in PATCHES:
            s = s.replace(old, new)
        open(fp, "w", encoding="utf-8").write(s)
        print(f"[{fp}] ✓ 已应用6处补丁")
    if not apply:
        print("\n（dry运行，未写入。加 --apply 真正写入）")


if __name__ == "__main__":
    main()
