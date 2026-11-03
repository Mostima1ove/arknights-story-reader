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
                cid = v.get("char") or who_main.get(v["who"])
                if cid and cid not in av_idx and os.path.exists(os.path.join(avdir, cid + ".png")):
                    av_idx[cid] = len(av_used)
                    av_used.append(cid)

    css = [f".s{i}{{background-image:url(data:image/webp;base64,{b64(os.path.join(full,k+'.webp'),640)})}}"
           for i, k in enumerate(sc_used)]
    css += [f".a{i}{{background-image:url(data:image/webp;base64,{b64(os.path.join(avdir,c+'.png'),112,76)})}}"
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
                    flush(); fn(); body.append(f'<div class="sc s{sc_idx[v]}"></div>')
            elif k == "cg":
                if v in sc_idx:
                    flush(); fn(); body.append(f'<div class="sc s{sc_idx[v]} iscg"></div>')
            elif k == "narr":
                flush(); narr.append(v)
            else:
                fn()
                cid = v.get("char") or who_main.get(v["who"])
                if buf and buf[0][0] == v["who"] and buf[0][1] == cid:
                    buf[0][2].append(v["text"])
                else:
                    flush(); buf.append((v["who"], cid, [v["text"]]))
        flush(); fn()

    toc_html = "".join(f'<a href="#{a}"><b>{t}</b><i>{l}</i></a>' for a, t, l in toc)
    says = sum(1 for e in eps for k, _ in e["events"] if k == "say")

    CSS = f"""
:root{{--bg:{T['bg']};--fg:{T['fg']};--dim:{T['dim']};--line:{T['line']};--acc:{T['acc']}}}
*{{box-sizing:border-box}} html{{-webkit-text-size-adjust:100%}}
body{{margin:0;background:var(--bg);color:var(--fg);max-width:680px;margin:0 auto;
 font-family:"Noto Serif SC","Songti SC",Georgia,"Microsoft YaHei",serif;font-size:16.5px;line-height:1.9;padding:0 16px 80px}}
header{{padding:40px 0 14px}}
.kicker{{font-size:12px;letter-spacing:.22em;color:var(--acc);margin-bottom:10px;font-family:system-ui,sans-serif}}
h1{{font-size:25px;margin:0 0 6px;color:{T['strong']}}}
.sub{{color:var(--dim);font-size:13px;line-height:1.7;margin:0}}
.toc{{margin:16px 0 26px;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:10px 0}}
.toc a{{display:flex;justify-content:space-between;color:var(--fg);text-decoration:none;font-size:13.5px;padding:5px 0;border-bottom:1px dotted #212628}}
.toc a i{{color:var(--dim);font-style:normal;font-size:12px}}
h2{{font-size:19px;margin:40px 0 12px;color:{T['strong']};border-top:1px solid var(--line);padding-top:18px}}
h2 .lb{{font-size:11.5px;color:var(--acc);margin-left:8px;letter-spacing:.1em}}
.sc{{height:170px;border-radius:10px;background-size:cover;background-position:center;margin:12px 0;background-color:{T['sc']}}}
.sc.iscg{{height:210px}}
@media (max-width:520px){{.sc{{height:130px}}.sc.iscg{{height:160px}}}}
p.n{{color:{T['narr']};margin:0 0 12px;text-align:justify}}
.line{{display:flex;gap:9px;margin:0 0 12px;align-items:flex-start}}
.av{{flex:0 0 56px;width:56px;height:72px;border-radius:6px;background-size:cover;background-position:top center;background-color:{T['av']}}}
.av.none{{opacity:.22}}
.sb{{flex:1;min-width:0}}
.who{{display:block;font-size:11.5px;color:var(--acc);letter-spacing:.05em;margin-bottom:1px;font-family:system-ui,sans-serif}}
.sb p{{margin:0 0 2px;font-size:16px;line-height:1.85;color:{T['txt']}}}
footer{{margin-top:50px;padding-top:16px;border-top:1px solid var(--line);color:var(--dim);font-size:12px;line-height:1.8}}
footer a{{color:var(--acc)}}
"""

    page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{args.title} · 剧情全文</title><style>{CSS}{''.join(css)}</style></head><body>
<header><div class="kicker">Arknights · SideStory</div>
<h1>{args.title}</h1>
<p class="sub">{len(eps)} 节剧情全文 · {says} 句台词 · 场景随剧情切换 · 说话人带脸</p>
<div class="toc">{toc_html}</div></header>
{''.join(body)}
<footer>文本与配图来自 <a href="{args.credit}">PRTS</a>；台词一句未删，仅去掉演出指令。</footer>
</body></html>"""

    open(args.out, "w", encoding="utf-8").write(page)
    print(f"written {args.out} {round(len(page)/1024/1024,2)} MB "
          f"(场景 {len(sc_used)} / 头像 {len(av_used)} / 台词 {says})")


if __name__ == "__main__":
    main()
