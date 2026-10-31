// 节日素材工作台 · 书签采集器
// 用法：把下面整段保存为浏览器书签的网址（以 javascript: 开头），
// 在 Williams-Sonoma / 任意电商商品页点击该书签即可抓取。
// 可多次点击收集多件商品，点「导出全部」一次性下载 JSON，再导入工作台。
(function(){
  function q(s){return document.querySelector(s);}
  function qa(s){return [].slice.call(document.querySelectorAll(s));}
  function meta(p){var m=document.querySelector('meta[property="'+p+'"],meta[name="'+p+'"]');return m?m.getAttribute("content"):"";}
  function clean(x){return (x||"").replace(/\s+/g," ").trim();}
  function hostOf(u){try{return new URL(u).hostname.replace(/^www\./,"");}catch(e){return "";}}

  // 1) JSON-LD 结构化数据（多数电商站都有）
  var prod={};
  qa('script[type="application/ld+json"]').forEach(function(sc){
    try{
      var j=JSON.parse(sc.textContent);
      var arr=Array.isArray(j)?j:(j["@graph"]||[j]);
      arr.forEach(function(n){ if(n&&/product/i.test(n["@type"]||(n["@type"]||[]).join&&n["@type"].join(" ")||"")) prod=n; });
    }catch(e){}
  });
  function imgOf(x){
    if(!x)return "";
    if(typeof x==="string")return x;
    if(Array.isArray(x)){var f=x[0];return f?(typeof f==="string"?f:(f.url||"")):"";}
    return x.url||"";
  }
  var title = prod.name || meta("og:title") || clean(q("h1")?q("h1").innerText:"");
  var ogImgs = qa('meta[property="og:image"]').map(function(m){return m.getAttribute("content");});
  var img = imgOf(prod.image) || ogImgs[0] || meta("twitter:image") || "";
  if(!ogImgs.length && img) ogImgs=[img];
  var offers = prod.offers||{};
  var priceRaw = (offers.price!==undefined?offers.price:(offers.lowPrice!==undefined?offers.lowPrice:"")) || meta("og:price:amount") || "";
  var cur = offers.priceCurrency || meta("og:price:currency") || "USD";
  var price = priceRaw ? ("$"+priceRaw+" "+cur).trim() : (meta("og:price:amount")?("$"+meta("og:price:amount")):"");
  var brand = (prod.brand&&prod.brand.name) || meta("og:site_name") || hostOf(location.href);
  var desc = prod.description || meta("og:description") || "";
  var url = prod.url || meta("og:url") || location.href;
  var sku = prod.sku || prod.mpn || (offers&&offers.sku) || "";

  // 2) 节日 / 类型 初判（工作台导入时会再判一次）
  var blob=(title+" "+desc+" "+(prod.category||"")).toLowerCase();
  function det(map){for(var k in map){if(map[k].test(blob))return k;}return "";}
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
  var holiday=det(HOL), design_type=det(DES);

  // 2.5) 证据抓取：评分/评论数/畅销/销量/点赞/收藏/转发（电商页与社媒页通吃）
  var bodyText=(document.body?document.body.innerText:"")+" "+(prod.description||"")+" "+(meta("description")||"");
  var E={rating:null,reviews:null,sold:null,likes:null,saves:null,shares:null,bestseller:false};
  if(prod.aggregateRating){
    if(prod.aggregateRating.ratingValue!=null)E.rating=parseFloat(prod.aggregateRating.ratingValue);
    if(prod.aggregateRating.reviewCount!=null)E.reviews=parseInt(prod.aggregateRating.reviewCount,10);
  }
  function num(s){var m=(s||"").match(/([\d,]+(?:\.\d+)?)/);return m?parseFloat(m[1].replace(/,/g,"")):null;}
  var mR=bodyText.match(/([\d,]+)\s*(?:customer\s+)?reviews?/i); if(mR&&E.reviews==null)E.reviews=num(mR[1]);
  var mRa=bodyText.match(/([\d.]+)\s*(?:out of|\/)\s*5\b/i)||bodyText.match(/rated\s*([\d.]+)/i); if(mRa&&E.rating==null)E.rating=parseFloat(mRa[1]);
  var mS=bodyText.match(/([\d,]+)\s*(?:sold|orders?)/i); if(mS)E.sold=num(mS[1]);
  var mL=bodyText.match(/([\d,]+)\s*(?:likes?|hearts?|favorites?)/i); if(mL)E.likes=num(mL[1]);
  var mSv=bodyText.match(/([\d,]+)\s*(?:saves?|saved|wishlist|added to (?:their )?(?:registry|list|cart))/i); if(mSv)E.saves=num(mSv[1]);
  var mSh=bodyText.match(/([\d,]+)\s*(?:shares?|reposts?|forwards?)/i); if(mSh)E.shares=num(mSh[1]);
  E.bestseller=/bestseller|best seller|top rated|most loved|top seller|editor'?s pick|#\d+\s*(?:best|top)/i.test(bodyText)||!!document.querySelector('[class*="bestseller" i],[class*="best-seller" i],[class*="top-rated" i],[class*="top-seller" i]');
  var signals=[];
  if(E.reviews!=null)signals.push("评论 "+E.reviews+(E.rating!=null?(" · "+E.rating+"★"):""));
  if(E.bestseller)signals.push("畅销标");
  if(E.sold!=null)signals.push("销量 "+E.sold);
  if(E.likes!=null)signals.push("点赞 "+E.likes);
  if(E.saves!=null)signals.push("收藏 "+E.saves);
  if(E.shares!=null)signals.push("转发 "+E.shares);
  // 主证据类型（优先级：销量>畅销>评论>点赞>收藏>转发）
  var evType="手动采集", evVal="", evNote="书签采集 @ "+hostOf(url);
  if(E.sold!=null){evType="月销量";evVal=String(E.sold);}
  else if(E.reviews!=null){evType="评论数";evVal=String(E.reviews);}
  else if(E.likes!=null){evType="点赞";evVal=String(E.likes);}
  else if(E.saves!=null){evType="收藏";evVal=String(E.saves);}
  else if(E.shares!=null){evType="转发";evVal=String(E.shares);}
  else if(E.bestseller){evType="Best Seller排名";evVal="是";}
  if(signals.length)evNote="书签采集 @ "+hostOf(url)+" | "+signals.join(" · ");
  function tierOf(v){return v==null?0:(v>=2000?5:v>=800?4:v>=200?3:v>=50?2:v>0?1:0);}
  var tier=tierOf(Math.max(E.reviews||0,E.sold||0,E.likes||0,E.saves||0,E.shares||0))||(E.bestseller?3:0);

  var item={
    platform:"独立站", brand:brand, title:clean(title),
    holiday:holiday, design_type:design_type,
    source_url:url, price:price,
    evidence_type:evType, evidence_value:evVal, evidence_note:evNote, tier:tier,
    img_remote:ogImgs[0]||"", img_gallery:ogImgs.slice(0,8),
    tags:sku, asin:"", collected_by:"手动采集",
    collected_at:new Date().toISOString().slice(0,16).replace("T"," ")
  };

  // 3) 收集进 sessionStorage（支持多件）
  var KEY="ws_collect";
  var arr=[];try{arr=JSON.parse(sessionStorage.getItem(KEY)||"[]");}catch(e){}
  arr.push(item);sessionStorage.setItem(KEY,JSON.stringify(arr));
  var n=arr.length;

  // 4) 浮动面板
  var old=document.getElementById("wbCapPanel");if(old)old.remove();
  var css="position:fixed;right:16px;bottom:16px;z-index:2147483647;width:340px;max-height:70vh;overflow:auto;"+
    "background:#1f1b16;color:#f4ead8;border:1px solid #c8843c;border-radius:12px;padding:14px;"+
    "font:13px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;box-shadow:0 10px 40px rgba(0,0,0,.45)";
  var p=document.createElement("div");p.id="wbCapPanel";p.setAttribute("style",css);
  function btn(label,fn,col){var b=document.createElement("button");b.textContent=label;b.style.cssText=
    "margin:4px 4px 0 0;padding:6px 10px;border:0;border-radius:7px;cursor:pointer;font-size:12px;background:"+
    (col||"#c8843c")+";color:#1f1b16;font-weight:600";b.onclick=fn;return b;}
  var evLine = evType==="手动采集" ? "证据：无（页面未暴露数据）" : ("证据："+evType+" "+evVal+(tier?(" · 强度 "+tier+"/5"):""));
  p.innerHTML='<div style="font-weight:700;margin-bottom:6px">✅ 已抓取：'+clean(title).slice(0,40)+
    '</div><div style="opacity:.8;margin-bottom:4px">本次共收集 <b style="color:#ffcf8a">'+n+
    '</b> 件 · 节日：'+(holiday||"未识别")+' · 类型：'+(design_type||"未识别")+'</div>'+
    '<div style="margin-bottom:8px;color:#ffcf8a">'+evLine+'</div>';
  var pre=document.createElement("pre");pre.style.cssText="background:#14110d;padding:8px;border-radius:8px;"+
    "max-height:160px;overflow:auto;white-space:pre-wrap;word-break:break-all;font-size:11px;margin:0 0 8px";
  pre.textContent=JSON.stringify(item,null,2);p.appendChild(pre);
  p.appendChild(btn("复制本条",function(){navigator.clipboard.writeText(JSON.stringify(item,null,2));},"#e9d9bf"));
  p.appendChild(btn("下载本条",function(){dl([item],"ws_item");}));
  p.appendChild(btn("导出全部("+n+")",function(){dl(arr,KEY);},"#7bbf6a"));
  p.appendChild(btn("清空",function(){sessionStorage.removeItem(KEY);p.remove();},"#7a7066"));
  p.appendChild(btn("关闭",function(){p.remove();},"#7a7066"));
  document.body.appendChild(p);

  function dl(items,name){
    var blob=new Blob([JSON.stringify(items,null,2)],{type:"application/json"});
    var a=document.createElement("a");a.href=URL.createObjectURL(blob);
    a.download=name+"_"+(items.length>1?items.length+"件":"")+".json";a.click();
    setTimeout(function(){URL.revokeObjectURL(a.href);},1000);
  }
})();
