# -*- coding: utf-8 -*-
"""收紧元素规则 + 主元素优先（最多2个），保留先前视觉补标结果"""
import io,json,re
EL={
"万圣节":[
 ("南瓜",r"南瓜|pumpkin"),("南瓜灯",r"南瓜灯|jack.?o.?lantern"),("骷髅",r"骷髅|skull|skeleton|骨架|\bbones?\b"),
 ("幽灵",r"幽灵|ghost|\bboo\b"),("蝙蝠",r"蝙蝠|\bbat\b|\bbats\b"),
 ("蜘蛛/蛛网",r"蜘蛛|蛛网|spider|cobweb|spider.?web"),("女巫",r"女巫|witch|巫婆"),("黑猫",r"黑猫|black.?cat"),
 ("科学怪人",r"科学怪人|frankenstein"),("木乃伊",r"木乃伊|mummy"),("吸血鬼",r"吸血鬼|vampire|dracula"),
 ("糖果/零食",r"糖果|\bcandy\b|trick.?or.?treat|candy.?corn|\btreats?\b")],
"感恩节":[
 ("火鸡",r"火鸡|turkey"),("南瓜",r"南瓜|pumpkin"),("南瓜派",r"南瓜派|pumpkin.?pie"),
 ("枫叶/秋叶",r"枫叶|秋叶|maple|fall.?leaves|autumn.?leaf|落叶"),
 ("丰收",r"丰收|harvest|\bgather\b|grateful|thankful|give.?thanks|cornucopia"),
 ("玉米",r"玉米|\bcorn\b|cornucopia"),("蔓越莓",r"蔓越莓|cranberry"),("向日葵",r"向日葵|sunflower")],
"圣诞节":[
 ("圣诞树",r"圣诞树|christmas.?tree|xmas.?tree"),("圣诞老人",r"圣诞老人|santa|st\.?nick"),
 ("驯鹿",r"驯鹿|reindeer|鹿角"),("雪人",r"雪人|snowman"),
 ("松枝/花环",r"松枝|花环|松果|\bwreath\b|\bpine\b|\bgarland\b|\bfir\b|冬青|\bholly\b"),
 ("槲寄生",r"槲寄生|mistletoe"),("胡桃夹子",r"胡桃夹子|nutcracker"),
 ("姜饼",r"姜饼|gingerbread|ginger.?bread"),("糖果杖",r"糖果杖|candy.?cane|拐杖糖|peppermint")],
}
# 通用性弱的排在后面：优先保留形象类元素
GENERIC={"糖果/零食","丰收"}
s=io.open("index.html",encoding="utf-8").read()
m=re.search(r'var DATA = (\[.*?\]);\n', s, re.S)
data=json.loads(m.group(1))
vis={e["id"] for e in json.load(open("/tmp/tg_map.json"))}   # 视觉补标过的 id
chg=0
for d in data:
    if d["id"] in vis:            # 视觉补标结果保留不动
        continue
    h=d.get("holiday")
    txt=" ".join(str(d.get(k,"") or "") for k in ("title","tags","holiday_reason","composition","note","material","color"))
    els=[n for n,p in EL.get(h,[]) if re.search(p,txt,re.I)]
    els=[e for e in els if e not in GENERIC][:2]            # 主元素最多2个
    d["elements"]=",".join(els)
    chg+=1
new_json=json.dumps(data,ensure_ascii=False,separators=(",",": "))
s=s[:m.start(1)]+new_json+s[m.end(1):]
for f in ["index_online.html","节日工作台数据库/工作台文件/index.html","节日工作台数据库/工作台文件/index_online.html"]:
    io.open(f,"w",encoding="utf-8").write(s)
io.open("index.html","w",encoding="utf-8").write(s)
print("文字规则重算:",chg,"条")
from collections import Counter
c=Counter()
for d in data:
    for e in (d.get("elements") or "").split(","):
        if e: c[(d.get("holiday"),e)]+=1
for k,v in sorted(c.items(),key=lambda x:-x[1]): print(v,k[0],k[1])
