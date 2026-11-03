# -*- coding: utf-8 -*-
"""把同一个根目录下所有活动的读本收成一页书架。

用法：
  python shelf.py --root D:\\work --out D:\\work\\书架.html
扫描 --root 下两层内的「*剧情全文.html」，读出标题、幕数、大小，排成卡片。
"""
import argparse, os, re, glob, html, datetime

CARD = """<a class="bk" href="{href}">
  <div class="t">{title}</div>
  <div class="m">{meta}</div>
  <div class="d">{date}</div>
</a>"""

def info(path):
    t = open(path, encoding="utf-8", errors="ignore").read(6000)
    m = re.search(r"<h1[^>]*>([^<]+)</h1>", t) or re.search(r"<title>([^<·]+)", t)
    title = html.unescape(m.group(1)).strip() if m else os.path.basename(path)
    n = len(re.findall(r'<h2 id="e\d+"', t))
    sub = re.search(r'<p class="sub">([^<]+)</p>', t)
    meta = html.unescape(sub.group(1)).strip() if sub else f"{n} 幕"
    size = round(os.path.getsize(path) / 1024 / 1024, 1)
    date = datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
    return title, f"{meta} · {size} MB", date


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    files = []
    for d in [root] + [os.path.join(root, x) for x in os.listdir(root) if os.path.isdir(os.path.join(root, x))]:
        files += glob.glob(os.path.join(d, "*剧情全文.html"))
    files = sorted(set(files), key=os.path.getmtime, reverse=True)
    cards = []
    for f in files:
        title, meta, date = info(f)
        href = os.path.relpath(f, os.path.dirname(args.out or os.path.join(root, "书架.html"))).replace("\\", "/")
        cards.append(CARD.format(href=href, title=title, meta=meta, date=date))

    page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>剧情书架</title>
<style>
:root{{--bg:#121517;--fg:#d8d5cd;--dim:#8b908d;--acc:#d9a05b}}
body{{margin:0;background:var(--bg);color:var(--fg);max-width:760px;margin:0 auto;padding:34px 16px 60px;
 font-family:"Noto Serif SC","Songti SC",system-ui,sans-serif}}
h1{{font-size:22px;margin:0 0 4px}}
.sub{{color:var(--dim);font-size:13px;margin:0 0 22px}}
.bk{{display:block;text-decoration:none;color:inherit;background:#1a1f22;border:1px solid #242a2d;
 border-radius:12px;padding:14px 16px;margin-bottom:10px}}
.bk:active{{background:#20262a}}
.t{{font-size:16.5px;margin-bottom:4px}}
.m{{font-size:12.5px;color:var(--dim)}}
.d{{font-size:11.5px;color:#6d7370;margin-top:4px}}
</style></head><body>
<h1>剧情书架</h1>
<p class="sub">{len(cards)} 份读本 · 按最近生成排序</p>
{''.join(cards) if cards else '<p class="sub">还没扫到读本。</p>'}
</body></html>"""
    out = args.out or os.path.join(root, "书架.html")
    open(out, "w", encoding="utf-8").write(page)
    print("written", out, len(cards), "份")


if __name__ == "__main__":
    main()
