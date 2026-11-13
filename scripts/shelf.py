# -*- coding: utf-8 -*-
"""把同一个目录下由本 skill 生成的读本收成一页书架。

用法：
  python shelf.py --root D:\\work                 # 生成/更新 D:\\work 里的书架
  python shelf.py --root D:\\work --out 我的书架.html

只收「带 arknights-story-reader 标记」的 HTML，别的网页不会被收进来。
如果目录里已经有书架，默认就地更新它（保持原来的文件名）。
"""
import argparse, datetime, glob, html, os, re, sys

GENERATOR = "arknights-story-reader/"
SHELF_TAG = "arknights-story-reader-shelf/"
DEFAULT_NAME = "剧情书架.html"

# 老读本的 CSS 里没有 #ctl a 这条，注入按钮时要连样式一起补
BTN_CSS = ('<style>#ctl a{width:52px;height:52px;border-radius:50%;'
           'border:1px solid #ffffff3d;background:#0b0d0fe0;color:#efeae0;'
           'font-size:19px;display:flex;align-items:center;justify-content:center;'
           'text-decoration:none;box-shadow:0 4px 18px #0009}</style>')


def inject_back(path, shelf_file):
    """给读本塞一个「回书架」的圆钮；已经有了就只改 href。返回是否动过。"""
    try:
        with open(path, encoding="utf-8") as f:
            s = f.read()
    except Exception:
        return False
    btn = f'<a id="shelfBtn" href="{shelf_file}" title="回书架">📚</a>'
    changed = False
    if 'id="shelfBtn"' in s:
        new = re.sub(r'<a id="shelfBtn" href="[^"]*"',
                     f'<a id="shelfBtn" href="{shelf_file}"', s, count=1)
        if new != s:
            s, changed = new, True
    elif '<div id="ctl">' in s:
        s = s.replace('<div id="ctl">', '<div id="ctl">\n  ' + btn, 1)
        changed = True
    if changed:
        if "#ctl a{" not in s:
            s = s.replace("</head>", BTN_CSS + "</head>", 1)
        with open(path, "w", encoding="utf-8") as f:
            f.write(s)
    return changed

CARD = """<a class="bk" href="{href}">
  <div class="tt">{title}</div>
  <div class="mm">{scenes} 幕 · {lines} 句</div>
  <div class="ff">{date} · {size} MB</div>
</a>"""


def read_edges(path, head_n=8192, tail_n=4096):
    size = os.path.getsize(path)
    with open(path, "rb") as f:
        head = f.read(head_n).decode("utf-8", "ignore")
        f.seek(max(0, size - tail_n))
        tail = f.read().decode("utf-8", "ignore")
    return head, tail, size


def is_reader(path):
    try:
        head, _, _ = read_edges(path, 4096, 64)
        return GENERATOR in head and SHELF_TAG not in head
    except Exception:
        return False


def is_shelf(path):
    try:
        head, _, _ = read_edges(path, 4096, 64)
        return SHELF_TAG in head
    except Exception:
        return False


def book_info(path):
    head, tail, size = read_edges(path)
    m = re.search(r'<meta name="asr:book" content="([^"]*)"', head)
    title = html.unescape(m.group(1)) if m else None
    if not title:
        m = re.search(r"<h1[^>]*>([^<]+)</h1>", head)
        title = html.unescape(m.group(1)).strip() if m else os.path.basename(path)
    # 幕数 / 台词数优先读 meta —— 老一点的文件没有这两个，就退回页面里的那句副标题。
    # 不能直接扫 <p class="sub">：CSS 里几十个 base64 头像能把头部撑到 8KB 之外。
    scenes = lines = 0
    m = re.search(r'<meta name="asr:scenes" content="(\d+)"', head)
    if m:
        scenes = int(m.group(1))
    m = re.search(r'<meta name="asr:lines" content="(\d+)"', head)
    if m:
        lines = int(m.group(1))
    if not scenes or not lines:
        m = re.search(r"(\d+)\s*节剧情全文[^\d]{0,40}(\d+)\s*句台词", head)
        if m:
            scenes = scenes or int(m.group(1))
            lines = lines or int(m.group(2))
    # 日期优先读 meta —— footer 在正文中间，文件末尾是脚本，尾巴上根本读不到
    m = re.search(r'<meta name="asr:date" content="([^"]+)"', head)
    if m:
        date = m.group(1)
    else:
        m = re.search(r"v\d+\.\d+(?:\.\d+)?\s*·\s*(\d{4}-\d{2}-\d{2})", tail)
        date = m.group(1) if m else datetime.datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d")
    return {"path": path, "title": title, "scenes": scenes, "lines": lines,
            "date": date, "size": round(size / 1024 / 1024, 2),
            "mtime": os.path.getmtime(path)}


def find_books(root):
    """root 和它下面一层的子目录，所有带标记的读本。"""
    dirs = [root] + [os.path.join(root, d) for d in os.listdir(root)
                     if os.path.isdir(os.path.join(root, d))]
    out = []
    for d in dirs:
        for p in glob.glob(os.path.join(d, "*.html")):
            if is_reader(p):
                out.append(p)
    return sorted(set(out))


def find_shelf(root, explicit=None):
    """优先用指定的；否则找目录里已有的书架，没有返回 None。"""
    if explicit:
        return explicit
    for p in glob.glob(os.path.join(root, "*.html")):
        if is_shelf(p):
            return p
    return None


def build(root, out):
    books = [book_info(p) for p in find_books(root)]
    books.sort(key=lambda b: b["mtime"], reverse=True)

    # 顺手把「回书架」的钮塞进每本读本——先做读本、后建书架的那批就是靠这一步补上的
    shelf_file = os.path.basename(out)
    for b in books:
        inject_back(b["path"], shelf_file)

    base = os.path.dirname(os.path.abspath(out))
    total_scenes = sum(b["scenes"] for b in books)
    total_lines = sum(b["lines"] for b in books)
    total_mb = sum(b["size"] for b in books)

    cards = []
    for b in books:
        href = os.path.relpath(b["path"], base).replace("\\", "/")
        cards.append(CARD.format(href=html.escape(href), title=html.escape(b["title"]),
                                 scenes=b["scenes"], lines=b["lines"],
                                 date=b["date"], size=b["size"]))
    body = "".join(cards) if cards else '<p class="empty">这个目录里还没有读本。</p>'

    page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#141a1d">
<meta name="generator" content="{SHELF_TAG}1">
<title>剧情书架</title>
<style>
:root{{--bg:#121517;--fg:#d8d5cd;--dim:#8b908d;--acc:#d9a05b;--card:#1a1f22;--line:#242a2d}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--fg);max-width:780px;margin:0 auto;
 padding:36px clamp(16px,4vw,26px) 70px;
 font-family:"Noto Serif SC","Songti SC",Georgia,system-ui,sans-serif}}
h1{{font-size:23px;margin:0 0 6px;letter-spacing:.02em}}
.sub{{color:var(--dim);font-size:13px;margin:0 0 26px;line-height:1.8}}
.bk{{display:block;text-decoration:none;color:inherit;background:var(--card);
 border:1px solid var(--line);border-radius:13px;padding:15px 17px;margin-bottom:10px;
 transition:background .15s,border-color .15s}}
.bk:hover{{background:#20262a;border-color:#333c40}}
.tt{{font-size:16.5px;margin-bottom:5px}}
.mm{{font-size:12.5px;color:var(--dim)}}
.ff{{font-size:11.5px;color:#6d7370;margin-top:5px;font-family:system-ui,sans-serif}}
.empty{{color:var(--dim);font-size:14px;padding:40px 0}}
footer{{margin-top:40px;padding-top:14px;border-top:1px solid var(--line);
 color:#6d7370;font-size:11.5px;line-height:1.9}}
</style></head><body>
<h1>剧情书架</h1>
<p class="sub">{len(books)} 份读本 · 共 {total_scenes} 幕 {total_lines} 句 · {total_mb:.1f} MB</p>
{body}
<footer>只收录由 arknights-story-reader 生成的读本。新做了一本，重跑一次本页对应的脚本就会自动收进来。</footer>
</body></html>"""
    open(out, "w", encoding="utf-8").write(page)
    return len(books), total_scenes, total_lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, help="读本所在的目录（会连它下面一层子目录一起扫）")
    ap.add_argument("--out", default=None, help="书架文件；不给就更新已有的，没有就新建剧情书架.html")
    args = ap.parse_args()
    root = os.path.abspath(args.root)
    out = find_shelf(root, args.out)
    if out is None:
        out = os.path.join(root, DEFAULT_NAME)
    n, sc, ln = build(root, out)
    print(f"书架 {out} —— 收了 {n} 本 / {sc} 幕 / {ln} 句")


if __name__ == "__main__":
    main()
