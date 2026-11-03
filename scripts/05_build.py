# -*- coding: utf-8 -*-
"""05 生成单文件 HTML 读本。

用法：
  python 05_build.py --base <dir> --title 昨日海 --theme sea --out 昨日海-剧情全文.html
主题：dark（乌萨斯那种暖红）/ sea（伊比利亚那种青蓝）
"""
import argparse, base64, io, json, os
from PIL import Image

THEMES = {
    "dark": dict(bg="#17181b", fg="#d3cec3", dim="#8d867a", line="#2a2c31", acc="#d4705f",
                 sc="#23262b", av="#262a30", strong="#e9e2d4", txt="#ddd7cb", narr="#9b9488"),
    "sea": dict(bg="#141a1d", fg="#cfd6d4", dim="#8b9694", line="#263134", acc="#5fb3b3",
                sc="#1e282c", av="#233034", strong="#e2ecea", txt="#dbe4e2", narr="#95a09d"),
}


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
        """某句的立绘如果其实是别人的（沿用上一个人），换回这个说话人自己的。"""
        if cid and char_main and char_main.get(cid, who) != who:
            return who_main.get(who) or cid
        return cid or who_main.get(who)
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

    CSS = f"""
:root{{--bg:{T['bg']};--fg:{T['fg']};--dim:{T['dim']};--line:{T['line']};--acc:{T['acc']};--k:1;--ik:1;--pad:clamp(14px, 4.2vw, 26px)}}
html{{background:{T['bg']};-webkit-text-size-adjust:100%}}
img,table,pre{{max-width:100%}}
*{{min-width:0}}
*{{box-sizing:border-box}} html{{-webkit-text-size-adjust:100%}}
body{{margin:0;background:var(--bg);color:var(--fg);overflow-x:hidden;
 font-family:"Noto Serif SC","Songti SC",Georgia,"Microsoft YaHei",serif}}
#page{{width:900px;transform-origin:top left;font-size:calc(16.5px * var(--k));line-height:1.9;
 padding:0 max(var(--pad), env(safe-area-inset-right)) 90px max(var(--pad), env(safe-area-inset-left))}}
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
#ctl{{position:fixed;right:12px;bottom:calc(14px + env(safe-area-inset-bottom));display:flex;gap:6px;z-index:99;
 padding:6px;border-radius:12px;background:#00000066;backdrop-filter:blur(8px);border:1px solid #ffffff1a}}
#ctl button{{width:36px;height:36px;border-radius:9px;border:0;background:#ffffff14;color:#e8e4da;
 font-size:15px;font-family:system-ui,sans-serif;cursor:pointer}}
#ctl button:active{{background:#ffffff2e}}
#ctl.hide{{opacity:.25}}
#tocBtn{{position:fixed;left:12px;top:calc(12px + env(safe-area-inset-top));z-index:98;
 padding:11px 16px;border-radius:12px;border:1px solid #ffffff26;background:#00000080;color:#efeae0;
 font-size:14.5px;font-family:system-ui,sans-serif;backdrop-filter:blur(10px);cursor:pointer;
 transition:opacity .2s ease,transform .2s ease}}
#tocBtn.dim{{opacity:.22;transform:scale(.94)}}
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
"""

    page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="{T['bg']}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<title>{args.title} · 剧情全文</title><style>{CSS}{''.join(css)}</style></head><body>
<div id="page">
<header><div class="kicker">Arknights · SideStory</div>
<h1>{args.title}</h1>
<p class="sub">{len(eps)} 节剧情全文 · {says} 句台词 · 场景随剧情切换 · 说话人带脸</p>
<button id="tocBtn">☰ 目录</button></header>
{''.join(body)}
<footer>文本与配图来自 <a href="{args.credit}">PRTS</a>；台词一句未删，仅去掉演出指令。
<br><span style="opacity:.6">v0.6 · {__import__('datetime').date.today().isoformat()} 生成</span></footer>
</div>
<div id="tocMask"></div>
<div id="tocPanel"><div class="toc">{toc_html}</div></div>
<div id="viewer"><img id="vimg" alt=""></div>
<div id="ctl">
  <button id="fsm" title="字号-">A−</button>
  <button id="fsp" title="字号+">A+</button>
  <button id="igm" title="图片-">−图</button>
  <button id="igp" title="图片+">图+</button>
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

  // 向下滚时按钮淡出，往上滚回来
  var lastY=0;
  window.addEventListener('scroll',function(){{
    var y=window.scrollY;
    if(y>lastY && y>140) btn.classList.add('dim'); else btn.classList.remove('dim');
    lastY=y;
  }},{{passive:true}});

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


if __name__ == "__main__":
    main()
