# -*- coding: utf-8 -*-
"""06 生成「名字 + 头像」核对页，人工扫一遍有没有认错人。

用法：python 06_audit.py --base <dir> [--title 活动名]
"""
import argparse, base64, io, json, os
from PIL import Image


def b64(p, w=96, h=124):
    im = Image.open(p).convert("RGB").resize((w, h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=80, method=4)
    return base64.b64encode(buf.getvalue()).decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--title", default="核对")
    ap.add_argument("--avdir", default="cast/avatar")
    args = ap.parse_args()

    base = args.base
    avdir = os.path.join(base, args.avdir)
    rows = json.load(open(os.path.join(base, "who_char.json"), encoding="utf-8"))
    seen = {}
    for n, v, cid in rows:
        if cid and cid != "-" and cid not in seen:
            seen[cid] = n
    items = []
    for cid, n in seen.items():
        p = os.path.join(avdir, cid + ".png")
        if os.path.exists(p):
            items.append((n, b64(p)))

    cards = "".join(
        f'<figure><img src="data:image/webp;base64,{b}"><figcaption>{n}</figcaption></figure>'
        for n, b in items
    )
    CSS = """
:root{--bg:#121517;--fg:#d8d5cd;--dim:#8b908d;--acc:#d9a05b;--line:#242a2d}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);max-width:1100px;margin:0 auto;padding:0 14px 50px;
 font-family:"Noto Serif SC","Songti SC",system-ui,sans-serif}
header{padding:34px 0 6px}
h1{font-size:22px;margin:0 0 6px}
.sub{color:var(--dim);font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(108px,1fr));gap:10px;margin-top:18px}
figure{margin:0;background:#1a1f22;border-radius:8px;overflow:hidden}
figure img{width:100%;display:block;aspect-ratio:96/124;object-fit:cover}
figcaption{font-size:11.5px;color:var(--dim);padding:5px 6px;text-align:center;line-height:1.3}
"""
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{args.title} · 头像核对</title><style>{CSS}</style></head><body>
<header><h1>{args.title} · 头像核对</h1>
<p class="sub">{len(items)} 人 · 按出场次数排 · 看着不对的记名字</p></header>
<div class="grid">{cards}</div></body></html>"""
    out = os.path.join(base, f"{args.title}-头像核对.html")
    open(out, "w", encoding="utf-8").write(html)
    print("written", out, len(items), "人")


if __name__ == "__main__":
    main()
