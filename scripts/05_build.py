# -*- coding: utf-8 -*-
"""05 生成单文件 HTML 读本。

用法：
  python 05_build.py --base <dir> --title 昨日海 --theme sea --out 昨日海-剧情全文.html
主题：dark（乌萨斯那种暖红）/ sea（伊比利亚那种青蓝）
"""
import argparse, base64, io, json, os, re, sys
from PIL import Image

THEMES = {
    "dark": dict(bg="#17181b", fg="#d3cec3", dim="#8d867a", line="#2a2c31", acc="#d4705f",
                 sc="#23262b", av="#262a30", strong="#e9e2d4", txt="#ddd7cb", narr="#9b9488"),
    "sea": dict(bg="#141a1d", fg="#cfd6d4", dim="#8b9694", line="#263134", acc="#5fb3b3",
                sc="#1e282c", av="#233034", strong="#e2ecea", txt="#dbe4e2", narr="#95a09d"),
}

# 书架靠这个版本号 + generator 标记认出「是本 skill 做的读本」，改版本时记得一起动
VERSION = "0.7.5"


def b64(p, w, q=58):
    im = Image.open(p).convert("RGB")
    if w and im.width > w:
        im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=q, method=4)
    return base64.b64encode(buf.getvalue()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--theme", default="dark", choices=list(THEMES))
    ap.add_argument("--out", required=True)
    ap.add_argument("--credit", default="https://prts.wiki")
    ap.add_argument("--avdir", default="cast/avatar")
    args = ap.parse_args()
    T = THEMES[args.theme]

    eps = json.load(open(os.path.join(args.base, "full_events.json"), encoding="utf-8"))
    rows = json.load(open(os.path.join(args.base, "who_char.json"), encoding="utf-8"))
    full = os.path.join(args.base, "assets", "full")
    avdir = os.path.join(args.base, args.avdir)

    who_main = {n: c for n, v, c in rows if c != "-"}
    cm_path = os.path.join(args.base, "char_main.json")
    char_main = json.load(open(cm_path, encoding="utf-8")) if os.path.exists(cm_path) else {}

    def pick(who, cid):
        """某句的立绘如果其实是别人的（沿用上一个人），换回这个说话人自己的。

        再兜一层：同一个角色常有几套立绘 id，挑中的那个可能当初没下到图
        （04 的命名对不上就会漏），这会儿退回这个人的主立绘，别让他光着。
        """
        if cid and char_main and char_main.get(cid, who) != who:
            c = who_main.get(who) or cid
        else:
            c = cid or who_main.get(who)
        if c and not os.path.exists(os.path.join(avdir, c + ".png")):
            alt = who_main.get(who)
            if alt and os.path.exists(os.path.join(avdir, alt + ".png")):
                return alt
        return c
    sc_idx, sc_used = {}, []
    av_idx, av_used = {}, []
    for e in eps:
        for k, v in e["events"]:
            if k in ("bg", "cg") and v not in sc_idx and v not in ("bg_black", "bg_white"):
                if os.path.exists(os.path.join(full, v + ".webp")):
                    sc_idx[v] = len(sc_used)
                    sc_used.append(v)
    for e in eps:
        for k, v in e["events"]:
            if k == "say":
                cid = pick(v["who"], v.get("char"))
                if cid and cid not in av_idx and os.path.exists(os.path.join(avdir, cid + ".png")):
                    av_idx[cid] = len(av_used)
                    av_used.append(cid)

    sc_src = {k: "data:image/webp;base64," + b64(os.path.join(full, k + ".webp"), 780, 56) for k in sc_used}
    css = [f".a{i}{{background-image:url(data:image/webp;base64,{b64(os.path.join(avdir,c+'.png'),112,76)})}}"
           for i, c in enumerate(av_used)]

    def ep_meta(t):
        # 干员密录的页面标题形如「莫斯提马/干员密录/2」，没有关卡代号，
        # 硬套下面的拆法会让代号和名字都变成整串、标题重复一遍。
        m = re.match(r"^(.+?)/干员密录/(\d+)$", t)
        if m:
            return m.group(1), "干员密录·" + m.group(2), ""
        code = t.split(" ")[0]
        name = t.split(" ", 1)[1].split("/")[0] if " " in t else t
        part = t.split("/")[-1]
        return code, name, {"BEG": "行动前", "END": "行动后", "NBT": ""}.get(part, "")

    body, toc, buf = [], [], []

    def flush():
        if not buf:
            return
        who, cid, texts = buf[0]
        idx = av_idx.get(cid) if cid else None
        av = f'<div class="av a{idx}"></div>' if idx is not None else '<div class="av none"></div>'
        body.append(f'<div class="line">{av}<div class="sb"><span class="who">{who}</span>'
                    + "".join(f"<p>{t}</p>" for t in texts) + "</div></div>")
        buf.clear()

    for e in eps:
        code, name, label = ep_meta(e["title"])
        a = "e" + str(len(toc))
        toc.append((a, f"{code} {name}", label))
        body.append(f'<h2 id="{a}">{code} {name}<span class="lb">{label}</span></h2>')
        narr = []

        def fn():
            if narr:
                body.append("<p class='n'>" + "<br>".join(narr) + "</p>")
                narr.clear()

        for k, v in e["events"]:
            if k == "bg":
                if v in sc_idx:
                    flush(); fn(); body.append(f'<img class="sc" src="{sc_src[v]}" alt="">')
            elif k == "cg":
                if v in sc_idx:
                    flush(); fn(); body.append(f'<img class="sc iscg" src="{sc_src[v]}" alt="">')
            elif k == "narr":
                flush(); narr.append(v)
            else:
                fn()
                cid = pick(v["who"], v.get("char"))
                if buf and buf[0][0] == v["who"] and buf[0][1] == cid:
                    buf[0][2].append(v["text"])
                else:
                    flush(); buf.append((v["who"], cid, [v["text"]]))
        flush(); fn()

    toc_html = "".join(f'<a href="#{a}"><b>{t}</b><i>{l}</i></a>' for a, t, l in toc)
    says = sum(1 for e in eps for k, _ in e["events"] if k == "say")

    # 同一个目录里已经有书架的话，右下角多给一个「回书架」的圆钮。
    # 书名不确定，所以扫一遍目录找带书架标记的那个文件。
    outdir = os.path.dirname(os.path.abspath(args.out))
    shelf_btn = ""
    try:
        for fn in sorted(os.listdir(outdir)):
            if not fn.lower().endswith(".html"):
                continue
            fp = os.path.join(outdir, fn)
            if not os.path.isfile(fp):
                continue
            with open(fp, "rb") as f:
                head = f.read(4096).decode("utf-8", "ignore")
            if "arknights-story-reader-shelf/" in head:
                shelf_btn = f'<a id="shelfBtn" href="{fn}" title="回书架">📚</a>'
                break
    except Exception:
        pass

    CSS = f"""
:root{{--bg:{T['bg']};--fg:{T['fg']};--dim:{T['dim']};--line:{T['line']};--acc:{T['acc']};--k:1;--ik:1;--pad:clamp(14px, 4.2vw, 26px)}}
html{{background:{T['bg']};-webkit-text-size-adjust:100%}}
img,table,pre{{max-width:100%}}
*{{min-width:0}}
*{{box-sizing:border-box}} html{{-webkit-text-size-adjust:100%}}
body{{margin:0;background:var(--bg);color:var(--fg);overflow-x:hidden;
 font-family:"Noto Serif SC","Songti SC",Georgia,"Microsoft YaHei",serif}}
#page{{width:900px;margin:0 auto;transform-origin:top left;font-size:calc(16.5px * var(--k));line-height:1.9;
 padding:0 var(--pad) 90px var(--pad)}}
@supports (padding:env(safe-area-inset-left)){{
 #page{{padding-left:max(var(--pad),env(safe-area-inset-left));
        padding-right:max(var(--pad),env(safe-area-inset-right))}}
}}
header{{padding:40px 0 14px}}
.kicker{{font-size:.74em;letter-spacing:.22em;color:var(--acc);margin-bottom:10px;font-family:system-ui,sans-serif}}
h1{{font-size:1.55em;margin:0 0 6px;color:{T['strong']}}}
.sub{{color:var(--dim);font-size:.82em;line-height:1.7;margin:0}}
.toc{{margin:16px 0 26px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:10px 0}}
.toc a{{display:flex;justify-content:space-between;color:var(--fg);text-decoration:none;font-size:.86em;padding:5px 0;border-bottom:1px dotted #212628}}
.toc a i{{color:var(--dim);font-style:normal;font-size:12px}}
h2{{font-size:1.16em;margin:40px 0 12px;color:{T['strong']};border-top:1px solid var(--line);padding-top:18px}}
h2 .lb{{font-size:.72em;color:var(--acc);margin-left:8px;letter-spacing:.1em}}
.sc{{width:calc(100% * var(--ik));height:auto;display:block;border-radius:10px;margin:12px auto;background:{T['sc']}}}
p.n{{color:{T['narr']};margin:0 0 12px;text-align:justify}}
.line{{display:flex;gap:9px;margin:0 0 12px;align-items:flex-start}}
.av{{flex:0 0 56px;width:56px;height:72px;border-radius:6px;background-size:cover;background-position:top center;background-color:{T['av']}}}
.av.none{{opacity:.22}}
.sb{{flex:1;min-width:0}}
.who{{display:block;font-size:.72em;color:var(--acc);letter-spacing:.05em;margin-bottom:1px;font-family:system-ui,sans-serif}}
.sb p{{margin:0 0 2px;font-size:1em;line-height:1.85;color:{T['txt']}}}
footer{{margin-top:50px;padding-top:16px;border-top:1px solid var(--line);color:var(--dim);font-size:.76em;line-height:1.8}}
footer a{{color:var(--acc)}}
#ctl{{position:fixed;right:14px;bottom:16px;z-index:98;display:flex;gap:8px}}
@supports (padding:env(safe-area-inset-bottom)){{#ctl{{bottom:calc(16px + env(safe-area-inset-bottom))}}}}
#ctl button,#ctl a{{width:52px;height:52px;border-radius:50%;border:1px solid #ffffff3d;background:#0b0d0fe0;
 color:#efeae0;font-size:19px;line-height:1;font-family:system-ui,sans-serif;cursor:pointer;
 backdrop-filter:blur(10px);box-shadow:0 4px 18px #0009;display:flex;align-items:center;
 justify-content:center;text-decoration:none}}
#ctl button:active{{background:#ffffff2e}}
#tocPanel .tools{{display:flex;gap:8px;margin-bottom:16px;padding-bottom:14px;border-bottom:1px solid #ffffff14}}
#tocPanel .tools button{{flex:1;height:42px;border-radius:10px;border:0;background:#ffffff12;color:#eae5db;
 font-size:14px;font-family:system-ui,sans-serif;cursor:pointer}}
#tocPanel .tools button:active{{background:#ffffff28}}
#ctl.hide{{opacity:.25}}
#tocMask{{position:fixed;inset:0;background:#00000080;z-index:98;display:none}}
#tocMask.show{{display:block}}
#tocPanel{{position:fixed;left:0;top:0;bottom:0;width:min(80vw,330px);z-index:99;box-shadow:8px 0 30px #0008;
 background:#0c0f11f5;backdrop-filter:blur(12px);border-right:1px solid #ffffff14;
 transform:translateX(-102%);transition:transform .22s ease;overflow-y:auto;padding:20px 16px 40px}}
#tocPanel.open{{transform:none}}
#tocPanel .toc a{{font-size:13px}}
#viewer{{position:fixed;inset:0;background:#000000e8;display:none;align-items:center;justify-content:center;z-index:100}}
#viewer img{{max-width:96vw;max-height:92vh;border-radius:8px}}
img.sc{{cursor:zoom-in}}
/* 开关：场景图 / 头像 */
.no-sc img.sc{{display:none}}
.no-av .av{{display:none}}
.no-av .line{{gap:0}}
/* 搜索层 */
#search{{position:fixed;inset:0;background:{T['bg']};z-index:120;display:none;flex-direction:column}}
#search.on{{display:flex}}
#sbar{{display:flex;gap:9px;padding:14px clamp(12px,4vw,22px);align-items:center;
 border-bottom:1px solid var(--line)}}
#sq{{flex:1;height:44px;border-radius:11px;border:1px solid var(--line);background:{T['sc']};
 color:var(--fg);font-size:16px;padding:0 14px;outline:none;font-family:inherit}}
#sq:focus{{border-color:var(--acc)}}
#sclose{{width:44px;height:44px;border-radius:11px;border:1px solid var(--line);
 background:transparent;color:var(--dim);font-size:17px;cursor:pointer}}
#slist{{flex:1;overflow-y:auto;padding:8px clamp(12px,4vw,22px) 70px}}
.sres{{padding:9px 11px;border-radius:9px;margin:3px 0;cursor:pointer;
 border-left:2px solid transparent;transition:background .12s}}
.sres:hover{{background:{T['sc']};border-left-color:var(--acc)}}
.sres .w{{font-size:12px;color:var(--acc);letter-spacing:.05em;font-family:system-ui,sans-serif}}
.sres .t{{font-size:14px;line-height:1.65;color:{T['txt']};margin-top:2px;
 display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.sres .m{{font-size:11.5px;color:var(--dim);margin-top:2px}}
.sempty{{color:var(--dim);text-align:center;padding:56px 20px;font-size:14px;line-height:1.9}}
@keyframes hitpulse{{0%{{background:#ffffff00}}16%{{background:{T['acc']}4d}}100%{{background:#ffffff00}}}}
.hit{{animation:hitpulse 1.8s ease-out}}
"""

    page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="{T['bg']}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="generator" content="arknights-story-reader/{VERSION}">
<meta name="asr:book" content="{args.title}">
<meta name="asr:scenes" content="{len(eps)}">
<meta name="asr:lines" content="{says}">
<meta name="asr:date" content="{__import__('datetime').date.today().isoformat()}">
<title>{args.title} · 剧情全文</title><style>{CSS}{''.join(css)}</style></head><body>
<div id="page">
<header><div class="kicker">Arknights · SideStory</div>
<h1>{args.title}</h1>
<p class="sub">{len(eps)} 节剧情全文 · {says} 句台词 · 场景随剧情切换 · 说话人带脸</p>
</header>
{''.join(body)}
<footer>文本与配图来自 <a href="{args.credit}">PRTS</a>；台词一句未删，仅去掉演出指令。
<br><span style="opacity:.6">v{VERSION} · {__import__('datetime').date.today().isoformat()} 生成</span></footer>
</div>
<div id="tocMask"></div>
<div id="tocPanel">
  <div class="tools">
    <button id="fsm">A−</button><button id="fsp">A+</button>
    <button id="igm">图−</button><button id="igp">图+</button>
  </div>
  <div class="tools">
    <button id="tgSc">场景图 开</button><button id="tgAv">头像 开</button>
  </div>
  <div class="toc">{toc_html}</div>
</div>
<div id="search">
  <div id="sbar"><input id="sq" placeholder="搜台词或人名" autocomplete="off"
    autocorrect="off" autocapitalize="off" spellcheck="false"><button id="sclose">✕</button></div>
  <div id="slist"></div>
</div>
<div id="viewer"><img id="vimg" alt=""></div>
<div id="ctl">
  {shelf_btn}
  <button id="searchBtn" title="搜索">🔍</button>
  <button id="tocBtn" title="目录与设置">☰</button>
</div>
<script>
(function(){{
  // 整页等比缩放（含图片）：手机不缩，桌面拖窄时整页跟着小
  function fit(){{
    var w = window.innerWidth;
    var z = Math.max(0.3, Math.min(1, w / 940));
    var pg = document.getElementById('page');
    if (!pg) return;
    pg.style.transform = 'scale(' + z + ')';
    pg.style.marginLeft = Math.max(0, Math.round((w - 900 * z) / 2)) + 'px';
    document.body.style.height = Math.ceil(pg.offsetHeight * z) + 'px';
  }}
  fit(); window.addEventListener('resize', fit); window.addEventListener('load', fit);

  var r=document.documentElement;
  var k=parseFloat(localStorage.getItem('xs-k'))||1;
  function apply(){{r.style.setProperty('--k',k);localStorage.setItem('xs-k',k);}}
  apply();
  document.getElementById('fsm').onclick=function(){{k=Math.max(0.8,+(k-0.1).toFixed(2));apply();}};
  document.getElementById('fsp').onclick=function(){{k=Math.min(1.8,+(k+0.1).toFixed(2));apply();}};

  var ik=parseFloat(localStorage.getItem('xs-ik'))||1;
  function applyImg(){{r.style.setProperty('--ik',ik);localStorage.setItem('xs-ik',ik);}}
  applyImg();
  document.getElementById('igm').onclick=function(){{ik=Math.max(0.4,+(ik-0.1).toFixed(2));applyImg();}};
  document.getElementById('igp').onclick=function(){{ik=Math.min(1.5,+(ik+0.1).toFixed(2));applyImg();}};

  // 目录抽屉
  var panel=document.getElementById('tocPanel');
  var btn=document.getElementById('tocBtn');
  var mask=document.getElementById('tocMask');
  function openToc(){{ panel.classList.add('open'); mask.classList.add('show'); }}
  function closeToc(){{ panel.classList.remove('open'); mask.classList.remove('show'); }}
  btn.onclick=function(){{ panel.classList.contains('open') ? closeToc() : openToc(); }};
  mask.onclick=closeToc;
  panel.addEventListener('click',function(e){{
    if(e.target.closest('a')) closeToc();          // 点条目跳转后自动收起
  }});
  document.addEventListener('keydown',function(e){{ if(e.key==='Escape') closeToc(); }});



  // 场景图 / 头像开关
  function bindToggle(id,key,cls,label){{
    var b=document.getElementById(id);
    var on=localStorage.getItem(key)!=='0';
    function apply(){{
      document.body.classList.toggle(cls,!on);
      b.textContent=label+(on?' 开':' 关');
      b.style.opacity=on?'1':'.6';
      localStorage.setItem(key,on?'1':'0');
      fit();
    }}
    b.onclick=function(){{ on=!on; apply(); }};
    apply();
  }}
  bindToggle('tgSc','xs-sc','no-sc','场景图');
  bindToggle('tgAv','xs-av','no-av','头像');

  // 全文搜索：把每句台词抽成一份内存索引，输入时只在索引里找
  var IDX=null;
  function buildIdx(){{
    if(IDX) return IDX;
    IDX=[];
    var cur='';
    var nodes=document.querySelectorAll('#page h2, #page .line');
    for(var i=0;i<nodes.length;i++){{
      var el=nodes[i];
      if(el.tagName==='H2'){{ cur=el.textContent.replace(/\\s+/g,' ').trim(); continue; }}
      var sb=el.querySelector('.sb');
      IDX.push({{el:el, text:sb?sb.textContent.replace(/\\s+/g,' ').trim():'', m:cur}});
    }}
    return IDX;
  }}
  function esc(s){{
    return String(s).replace(/[&<>]/g,function(c){{
      return {{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c];
    }});
  }}
  var sBox=document.getElementById('search'),
      sInput=document.getElementById('sq'),
      sList=document.getElementById('slist');
  var HINT='<div class="sempty">输入几个字<br>整本的台词和人名都能搜到</div>';
  function openSearch(){{
    sBox.classList.add('on'); buildIdx();
    if(!sList.childNodes.length) sList.innerHTML=HINT;
    setTimeout(function(){{ sInput.focus(); }},60);
  }}
  function closeSearch(){{ sBox.classList.remove('on'); sInput.blur(); }}
  document.getElementById('searchBtn').onclick=openSearch;
  document.getElementById('sclose').onclick=closeSearch;

  function runSearch(){{
    var q=sInput.value.trim();
    if(!q){{ sList.innerHTML=HINT; return; }}
    var idx=buildIdx(), hits=[], n=0;
    for(var i=0;i<idx.length;i++){{
      var it=idx[i], p=it.text.indexOf(q);
      if(p<0) continue;
      n++;
      if(hits.length<60){{
        var st=Math.max(0,p-16), en=Math.min(it.text.length,p+q.length+26);
        var frag=(st>0?'…':'')+it.text.slice(st,en)+(en<it.text.length?'…':'');
        hits.push('<div class="sres" data-i="'+i+'"><div class="w">'+esc(it.m)+'</div>'
                 +'<div class="t">'+esc(frag)+'</div></div>');
      }}
    }}
    if(!n){{ sList.innerHTML='<div class="sempty">没找到「'+esc(q)+'」</div>'; return; }}
    sList.innerHTML='<div class="sempty" style="padding:6px 0 12px;text-align:left">找到 '
      +n+' 处'+(n>60?'　先列前 60 条':'')+'</div>'+hits.join('');
    Array.prototype.forEach.call(sList.querySelectorAll('.sres'),function(d){{
      d.onclick=function(){{
        var it=idx[+d.dataset.i];
        var y=it.el.getBoundingClientRect().top+window.scrollY-90;
        closeSearch();
        window.scrollTo(0,Math.max(0,y));
        it.el.classList.remove('hit');
        void it.el.offsetWidth;
        it.el.classList.add('hit');
        setTimeout(function(){{ it.el.classList.remove('hit'); }},1900);
      }};
    }});
  }}
  var sTimer=null;
  sInput.oninput=function(){{ clearTimeout(sTimer); sTimer=setTimeout(runSearch,150); }};
  sInput.onkeydown=function(ev){{
    if(ev.key==='Enter'){{ clearTimeout(sTimer); runSearch(); }}
    if(ev.key==='Escape'){{ closeSearch(); }}
  }};

  // 图片点开看大图
  var view=document.getElementById('viewer'), vimg=document.getElementById('vimg');
  document.querySelectorAll('img.sc').forEach(function(im){{
    im.addEventListener('click',function(){{ vimg.src=im.src; view.style.display='flex'; }});
  }});
  view.addEventListener('click',function(){{ view.style.display='none'; }});

  // 记住读到哪儿
  var posKey='xs-pos-'+location.pathname;
  window.addEventListener('scroll',function(){{
    var h=document.body.scrollHeight-window.innerHeight;
    if(h>10) localStorage.setItem(posKey,(window.scrollY/h).toFixed(4));
  }},{{passive:true}});
  window.addEventListener('load',function(){{
    setTimeout(function(){{
      var p=localStorage.getItem(posKey);
      if(p && +p>0.02){{
        var h=document.body.scrollHeight-window.innerHeight;
        if(h>10) window.scrollTo(0,Math.round(+p*h));
      }}
    }},350);
  }});
}})();
</script>
</body></html>"""

    open(args.out, "w", encoding="utf-8").write(page)
    print(f"written {args.out} {round(len(page)/1024/1024,2)} MB "
          f"(场景 {len(sc_used)} / 头像 {len(av_used)} / 台词 {says})")

    # 同目录已经有书架的话，顺手把这一本收进去，不用再手动跑一次
    try:
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.insert(0, here)
        import shelf
        outdir = os.path.dirname(os.path.abspath(args.out))
        sh = shelf.find_shelf(outdir)
        if sh:
            n, sc, ln = shelf.build(outdir, sh)
            print(f"书架已更新 {os.path.basename(sh)}（现有 {n} 本 / {sc} 幕 / {ln} 句）")
        else:
            print("这个目录还没有书架。要建的话跑一次 shelf.py --root " + outdir)
    except Exception as e:
        print("书架更新跳过：", e)


if __name__ == "__main__":
    main()
