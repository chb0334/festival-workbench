# -*- coding: utf-8 -*-
"""给每条素材打节日元素标签 elements（多值逗号分隔）"""
import io,json,re
EL={
"万圣节":[("南瓜",r"南瓜|pumpkin"),("骷髅",r"骷髅|skull|skeleton|骨架"),("幽灵",r"幽灵|ghost|boo\b|精灵"),("蝙蝠",r"蝙蝠|bat\b|bats"),
        ("蜘蛛/蛛网",r"蜘蛛|蛛网|spider|web\b|cobweb"),("女巫",r"女巫|witch|魔法帽"),("黑猫",r"黑猫|black cat|猫\b"),("糖果/零食",r"糖果|candy|trick|treat|零食|甜品|dessert|蛋糕|cake|马芬|muffin|饼干|cookie|棒棒糖"),
        ("科学怪人",r"科学怪人|frankenstein"),("木乃伊",r"木乃伊|mummy"),("吸血鬼",r"吸血鬼|vampire|dracula"),("南瓜灯",r"南瓜灯|jack.?o.?lantern")],
"感恩节":[("火鸡",r"火鸡|turkey"),("南瓜",r"南瓜|pumpkin"),("枫叶/秋叶",r"枫叶|秋叶|maple|fall leaves|autumn leaf|落叶"),("丰收",r"丰收|harvest|gather|grateful|thankful|give thanks"),
        ("玉米",r"玉米|corn\b"),("蔓越莓",r"蔓越莓|cranberry"),("向日葵",r"向日葵|sunflower"),("南瓜派",r"南瓜派|pumpkin pie")],
"圣诞节":[("圣诞树",r"圣诞树|christmas tree|\btree\b"),("圣诞老人",r"圣诞老人|santa"),("驯鹿",r"驯鹿|reindeer|鹿角|moose"),("雪人",r"雪人|snowman"),
        ("松枝/花环",r"松枝|花环|松果|wreath|pine|garland|fir|冬青|holy\b"),("槲寄生",r"槲寄生|mistletoe"),("胡桃夹子",r"胡桃夹子|nutcracker"),("姜饼",r"姜饼|gingerbread"),("糖果杖",r"糖果杖|candy cane|拐杖糖")],
}
s=io.open("index.html",encoding="utf-8").read()
m=re.search(r'var DATA = (\[.*?\]);\n', s, re.S)
data=json.loads(m.group(1))
cnt={}
for d in data:
    h=d.get("holiday")
    txt=" ".join(str(d.get(k,"") or "") for k in ("title","tags","holiday_reason","composition","note","material","color"))
    els=[]
    for name,pat in EL.get(h,[]):
        if re.search(pat,txt,re.I): els.append(name)
    # 去重且南瓜灯并入南瓜
    if "南瓜灯" in els and "南瓜" in els: els.remove("南瓜灯")
    d["elements"]=",".join(els)
    for e in els: cnt[(h,e)]=cnt.get((h,e),0)+1
new_json=json.dumps(data,ensure_ascii=False,separators=(",",": "))
s=s[:m.start(1)]+new_json+s[m.end(1):]
io.open("index.html","w",encoding="utf-8").write(s)
for f in ["index_online.html","节日工作台数据库/工作台文件/index.html","节日工作台数据库/工作台文件/index_online.html"]:
    io.open(f,"w",encoding="utf-8").write(io.open("index.html",encoding="utf-8").read())
holy=sorted({h for h,_ in cnt})
for h in holy:
    items=sorted([(v,k[1]) for k,v in cnt.items() if k[0]==h],reverse=True)
    print(h, "→", ", ".join(f"{n}:{v}" for v,n in items))
none=sum(1 for d in data if not d.get("elements"))
print("无元素标记:",none,"/",len(data))
