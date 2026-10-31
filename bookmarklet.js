// 节日素材工作台 · 书签采集器 v3
// 用法：在 Williams-Sonoma 的【商品页】或【节日频道列表页】点击书签。
//  - 商品页：精确抓取该商品（含评分/评论数等证据）
//  - 列表页（如 WS 顶部导航的 Halloween / Thanksgiving / Christmas 频道）：
//    一键批量抓取整页商品，可翻页后继续点书签累积，最后「导出全部」。
// 注意：必须在真实网页上点击（空白新标签页抓不到东西，会弹出提示）。
(function(){
  function q(s){return document.querySelector(s);}
  function qa(s){return [].slice.call(document.querySelectorAll(s));}
  function meta(p){var m=document.querySelector('meta[property="'+p+'"],meta[name="'+p+'"]');return m?m.getAttribute("content"):"";}
  function clean(x){return (x||"").replace(/\s+/g," ").trim();}
  function hostOf(u){try{return new URL(u).hostname.replace(/^www\./,"");}catch(e){return "";}}
  var KEY="ws_collect";
  function load(){try{return JSON.parse(sessionStorage.getItem(KEY)||"[]");}catch(e){return [];}}
  function save(a){sessionStorage.setItem(KEY,JSON.stringify(a));}

  function panel(html){
    var old=document.getElementById("wbCapPanel");if(old)old.remove();
    var css="position:fixed;right:16px;bottom:16px;z-index:2147483647;width:340px;max-height:70vh;overflow:auto;"+
      "background:#1f1b16;color:#f4ead8;border:1px solid #c8843c;border-radius:12px;padding:14px;"+
      "font:13px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;box-shadow:0 10px 40px rgba(0,0,0,.45)";
    var p=document.createElement("div");p.id="wbCapPanel";p.setAttribute("style",css);p.innerHTML=html;
    function btn(label,fn,col){var b=document.createElement("button");b.textContent=label;b.style.cssText=
      "margin:4px 4px 0 0;padding:6px 10px;border:0;border-radius:7px;cursor:pointer;font-size:12px;background:"+
      (col||"#c8843c")+";color:#1f1b16;font-weight:600";b.onclick=fn;return b;}
    p._btn=btn;document.body.appendChild(p);return p;
  }
  function dl(items,name){
    var blob=new Blob([JSON.stringify(items,null,2)],{type:"application/json"});
    var a=document.createElement("a");a.href=URL.createObjectURL(blob);
    a.download=name+"_"+(items.length>1?items.length+"件":"")+".json";a.click();
    setTimeout(function(){URL.revokeObjectURL(a.href);},1000);
  }

  // 0) 空白页 / 非网页检测
  var bodyTxt=document.body?document.body.innerText:"";
  var isLocal=location.protocol==="about:"||location.protocol==="chrome:"||location.protocol==="edge:"||
              location.href==="about:blank"||/^(chrome|edge|browser):\/\//.test(location.href);
  if(isLocal||clean(bodyTxt).length<3){
    panel('<div style="font-weight:700;margin-bottom:6px">⚠️ 当前页面抓不了</div>'+
      '<div style="opacity:.85;line-height:1.7">这里是空白新标签页，书签只能抓取<b style="color:#ffcf8a">已打开的网页</b>。</div>'+
      '<div style="margin-top:8px;line-height:1.8">正确用法：<br>1️⃣ 先打开 Williams-Sonoma 的<b>商品页</b>，或顶部导航的 <b>Halloween / Thanksgiving / Christmas</b> 节日频道页<br>2️⃣ 再点击书签「抓取当前商品」</div>');
    return;
  }

  // 1) 页面级节日推断（频道页 URL 含 halloween/thanksgiving/christmas 等）
  var u=location.href.toLowerCase(), pt=clean(document.title).toLowerCase();
  function holOf(s){
    if(/halloween/.test(s))return "万圣节";
    if(/thanksgiving|harvest|fall-decor|autumn/.test(s))return "感恩节";
    if(/christmas|xmas|hanukkah|holiday/.test(s))return "圣诞节";
    if(/easter/.test(s))return "复活节";
    if(/valentine/.test(s))return "情人节";
    return "";
  }
  var pageHol=holOf(u+" "+pt);

  var HOL={"万圣节":/halloween|pumpkin|spider|ghost|skull|bat|witch|skeleton/i,
           "感恩节":/thanksgiving|harvest|turkey|fall|autumn|thanks/i,
           "圣诞节":/christmas|xmas|santa|hanukkah|reindeer|snowflake|ornament|holiday/i,
           "复活节":/easter|egg|bunny|rabbit/i,
           "情人节":/valentine|love|heart/i,
           "独立日":/4th|fourth of july|patriotic|fireworks/i};
  var DES={"盘子":/plate|dish|charger|dinner set|dinnerware/i,
           "杯子":/mug|cup|tumbler|glass|stein/i,
           "纸巾":/napkin|towel|linen/i,
           "餐具":/cutlery|silverware|utensil|flatware|fork|spoon|knife/i,
           "桌布":/tablecloth|runner|placemat/i,
           "装饰":/decor|ornament|banner|garland|centerpiece/i};
  function det(map,s){for(var k in map){if(map[k].test(s))return k;}return "";}

  // 2) 单品模式：JSON-LD Product
  var prod={};
  qa('script[type="application/ld+json"]').forEach(function(sc){
    try{
      var j=JSON.parse(sc.textContent);
      var g=Array.isArray(j)?j:(j["@graph"]||[j]);
      g.forEach(function(n){ if(n&&/product/i.test(n["@type"]||(n["@type"]||[]).join&&n["@type"].join(" ")||"")) prod=n; });
    }catch(e){}
  });
  function imgOf(x){
    if(!x)return "";
    if(typeof x==="string")return x;
    if(Array.isArray(x)){var f=x[0];return f?(typeof f==="string"?f:(f.url||"")):"";}
    return x.url||"";
  }
  var sTitle = prod.name || meta("og:title") || clean(q("h1")?q("h1").innerText:"");
  var sImg = imgOf(prod.image) || meta("og:image") || meta("twitter:image") || "";

  // 3) 列表模式：扫描商品 tile（频道页/分类页）
  function scanTiles(){
    var seen={},out=[];
    qa('a[href]').forEach(function(a){
      var h=a.href.split("#")[0];
      if(!/^https?:/.test(h))return;
      if(!/\/(products?|p)\/[^\/?#]+/.test(h))return;
      var key=h.toLowerCase();if(seen[key])return;
      var card=a.closest('li,article,[class*="product"],[data-testid*="product"],[class*="ProductCard"],section')||a;
      var img=card.querySelector('img')||a.querySelector('img');
      var src=img?(img.currentSrc||img.src||img.getAttribute("data-src")||""):"";
      var t=clean((img&&img.alt)||a.getAttribute("aria-label")||a.innerText||"");
      if(!src||t.length<3)return;
      var pm=(card.innerText||"").match(/\$\s?[\d,]+(?:\.\d{2})?/);
      seen[key]=1;
      out.push({title:t.slice(0,160),url:h,img:src,price:pm?pm[0].replace(/\s+/g,""):"",tile:card.innerText||""});
    });
    return out;
  }

  var items=[], mode="";
  if(sTitle && sImg && Object.keys(prod).length){
    mode="单品";
    var ogImgs=qa('meta[property="og:image"]').map(function(m){return m.getAttribute("content");});
    if(!ogImgs.length&&sImg)ogImgs=[sImg];
    var offers=prod.offers||{};
    var priceRaw=(offers.price!==undefined?offers.price:(offers.lowPrice!==undefined?offers.lowPrice:""))||meta("og:price:amount")||"";
    var cur=offers.priceCurrency||meta("og:price:currency")||"USD";
    var price=priceRaw?("$"+priceRaw+" "+cur).trim():"";
    var desc=prod.description||meta("og:description")||"";
    var blob=(sTitle+" "+desc+" "+(prod.category||"")).toLowerCase();
    var holiday=pageHol||det(HOL,blob);
    var design_type=det(DES,blob);
    // 证据（评分/评论/畅销/销量/点赞/收藏/转发）
    var allTxt=bodyTxt+" "+(prod.description||"")+" "+(meta("description")||"");
    var E={rating:null,reviews:null,sold:null,likes:null,saves:null,shares:null,bestseller:false};
    if(prod.aggregateRating){
      if(prod.aggregateRating.ratingValue!=null)E.rating=parseFloat(prod.aggregateRating.ratingValue);
      if(prod.aggregateRating.reviewCount!=null)E.reviews=parseInt(prod.aggregateRating.reviewCount,10);
    }
    function num(s){var m=(s||"").match(/([\d,]+(?:\.\d+)?)/);return m?parseFloat(m[1].replace(/,/g,"")):null;}
    var mR=allTxt.match(/([\d,]+)\s*(?:customer\s+)?reviews?/i); if(mR&&E.reviews==null)E.reviews=num(mR[1]);
    var mRa=allTxt.match(/([\d.]+)\s*(?:out of|\/)\s*5\b/i)||allTxt.match(/rated\s*([\d.]+)/i); if(mRa&&E.rating==null)E.rating=parseFloat(mRa[1]);
    var mS=allTxt.match(/([\d,]+)\s*(?:sold|orders?)/i); if(mS)E.sold=num(mS[1]);
    var mL=allTxt.match(/([\d,]+)\s*(?:likes?|hearts?|favorites?)/i); if(mL)E.likes=num(mL[1]);
    var mSv=allTxt.match(/([\d,]+)\s*(?:saves?|saved|wishlist)/i); if(mSv)E.saves=num(mSv[1]);
    var mSh=allTxt.match(/([\d,]+)\s*(?:shares?|reposts?|forwards?)/i); if(mSh)E.shares=num(mSh[1]);
    E.bestseller=/bestseller|best seller|top rated|top seller|editor'?s pick/i.test(allTxt)||!!document.querySelector('[class*="bestseller" i],[class*="best-seller" i],[class*="top-rated" i],[class*="top-seller" i]');
    var signals=[];
    if(E.reviews!=null)signals.push("评论 "+E.reviews+(E.rating!=null?(" · "+E.rating+"★"):""));
    if(E.bestseller)signals.push("畅销标");
    if(E.sold!=null)signals.push("销量 "+E.sold);
    if(E.likes!=null)signals.push("点赞 "+E.likes);
    if(E.saves!=null)signals.push("收藏 "+E.saves);
    if(E.shares!=null)signals.push("转发 "+E.shares);
    var evType="手动采集",evVal="";
    if(E.sold!=null){evType="月销量";evVal=String(E.sold);}
    else if(E.reviews!=null){evType="评论数";evVal=String(E.reviews);}
    else if(E.likes!=null){evType="点赞";evVal=String(E.likes);}
    else if(E.saves!=null){evType="收藏";evVal=String(E.saves);}
    else if(E.shares!=null){evType="转发";evVal=String(E.shares);}
    else if(E.bestseller){evType="Best Seller排名";evVal="是";}
    var evNote="书签采集 @ "+hostOf(location.href)+(signals.length?(" | "+signals.join(" · ")):"");
    function tierOf(v){return v==null?0:(v>=2000?5:v>=800?4:v>=200?3:v>=50?2:v>0?1:0);}
    var tier=tierOf(Math.max(E.reviews||0,E.sold||0,E.likes||0,E.saves||0,E.shares||0))||(E.bestseller?3:0);
    items.push({
      platform:"独立站", brand:(prod.brand&&prod.brand.name)||meta("og:site_name")||hostOf(location.href),
      title:clean(sTitle), holiday:holiday, design_type:design_type,
      source_url:prod.url||meta("og:url")||location.href, price:price,
      evidence_type:evType, evidence_value:evVal, evidence_note:evNote, tier:tier,
      img_remote:ogImgs[0]||"", img_gallery:ogImgs.slice(0,8),
      tags:prod.sku||prod.mpn||(offers&&offers.sku)||"", asin:"", collected_by:"手动采集",
      collected_at:new Date().toISOString().slice(0,16).replace("T"," ")
    });
  } else {
    // 列表页批量
    var tiles=scanTiles();
    if(tiles.length>=3){
      mode="列表";
      var arr=load(), exist={};arr.forEach(function(x){exist[x.source_url]=1;});
      var added=0;
      tiles.forEach(function(t){
        if(exist[t.url.toLowerCase()])return;
        var blob=(t.title+" "+t.tile).toLowerCase();
        arr.push({
          platform:"独立站", brand:hostOf(t.url), title:t.title,
          holiday:pageHol||det(HOL,blob), design_type:det(DES,blob),
          source_url:t.url, price:t.price,
          evidence_type:"手动采集", evidence_value:"", evidence_note:"书签列表采集 @ "+hostOf(t.url), tier:0,
          img_remote:t.img, img_gallery:[t.img], tags:"", asin:"", collected_by:"手动采集",
          collected_at:new Date().toISOString().slice(0,16).replace("T"," ")
        });
        exist[t.url.toLowerCase()]=1;added++;
      });
      save(arr);items=arr;
      var n=arr.length;
      var prev=arr.slice(-Math.min(added||5,5)).map(function(x){return "• "+x.title.slice(0,34)+(x.holiday?(" ["+x.holiday+"]"):"");}).join("<br>");
      var p=panel('<div style="font-weight:700;margin-bottom:6px">📦 列表页批量抓取：新增 <b style="color:#ffcf8a">'+added+'</b> 件</div>'+
        '<div style="opacity:.8;margin-bottom:4px">本页识别到 '+(pageHol?pageHol+"频道 · ":"")+tiles.length+' 件商品 · 共收集 <b style="color:#ffcf8a">'+n+'</b> 件</div>'+
        (added?'<div style="margin-bottom:8px;font-size:12px;opacity:.75">'+prev+'</div>':'<div style="margin-bottom:8px;color:#e88">本页商品都已抓过，翻页后可再点书签继续累积</div>'));
      p.appendChild(p._btn("导出全部("+n+")",function(){dl(arr,KEY);},"#7bbf6a"));
      p.appendChild(p._btn("复制全部",function(){navigator.clipboard.writeText(JSON.stringify(arr,null,2));},"#e9d9bf"));
      p.appendChild(p._btn("清空",function(){sessionStorage.removeItem(KEY);p.remove();},"#7a7066"));
      p.appendChild(p._btn("关闭",function(){p.remove();},"#7a7066"));
      return;
    }
  }

  if(!items.length){
    panel('<div style="font-weight:700;margin-bottom:6px">⚠️ 这页没识别到商品</div>'+
      '<div style="opacity:.85;line-height:1.7">请打开 Williams-Sonoma 的<b style="color:#ffcf8a">商品详情页</b>，或顶部导航的 <b style="color:#ffcf8a">Halloween / Thanksgiving / Christmas</b> 节日频道列表页，再点本书签。</div>');
    return;
  }

  // 4) 单品面板
  var item=items[0], arr2=load();arr2.push(item);save(arr2);
  var n2=arr2.length;
  var evLine = item.evidence_type==="手动采集" ? "证据：无（页面未暴露数据）" : ("证据："+item.evidence_type+" "+item.evidence_value+(item.tier?(" · 强度 "+item.tier+"/5"):""));
  var p2=panel('<div style="font-weight:700;margin-bottom:6px">✅ 已抓取：'+item.title.slice(0,40)+
    '</div><div style="opacity:.8;margin-bottom:4px">本次共收集 <b style="color:#ffcf8a">'+n2+
    '</b> 件 · 节日：'+(item.holiday||"未识别")+' · 类型：'+(item.design_type||"未识别")+'</div>'+
    '<div style="margin-bottom:8px;color:#ffcf8a">'+evLine+'</div>');
  var pre=document.createElement("pre");pre.style.cssText="background:#14110d;padding:8px;border-radius:8px;"+
    "max-height:160px;overflow:auto;white-space:pre-wrap;word-break:break-all;font-size:11px;margin:0 0 8px";
  pre.textContent=JSON.stringify(item,null,2);p2.appendChild(pre);
  p2.appendChild(p2._btn("复制本条",function(){navigator.clipboard.writeText(JSON.stringify(item,null,2));},"#e9d9bf"));
  p2.appendChild(p2._btn("下载本条",function(){dl([item],"ws_item");}));
  p2.appendChild(p2._btn("导出全部("+n2+")",function(){dl(arr2,KEY);},"#7bbf6a"));
  p2.appendChild(p2._btn("清空",function(){sessionStorage.removeItem(KEY);p2.remove();},"#7a7066"));
  p2.appendChild(p2._btn("关闭",function(){p2.remove();},"#7a7066"));
})();
