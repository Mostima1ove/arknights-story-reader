# -*- coding: utf-8 -*-
"""03 下载背景与 CG，压成 640 宽 webp。

用法：python 03_fetch_assets.py --base <dir>

依赖 full_events.json（先跑 02）。第一次会顺手抓 Widget:Data_Image 建 image_map.json。
"""
import argparse, hashlib, json, os, re, subprocess, sys, urllib.parse
from PIL import Image

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
WIDGET = "https://prts.wiki/w/Widget:Data_Image"


def curl(url, out, timeout="120", referer=True):
    cmd = ["curl.exe", "-s", "-L", "-m", timeout, "-A", UA,
           "-H", "Accept-Language: zh-CN,zh;q=0.9"]
    if referer:
        cmd += ["-H", "Referer: https://prts.wiki/"]
    cmd += [url, "-o", out]
    subprocess.run(cmd, capture_output=True)
    return os.path.exists(out) and os.path.getsize(out) > 5000


def md5path(fn):
    h = hashlib.md5(fn.encode()).hexdigest()
    return f"{h[0]}/{h[:2]}/{urllib.parse.quote(fn, safe='')}"


def build_map(base):
    p = os.path.join(base, "assets", "image_map.json")
    if os.path.exists(p):
        return json.load(open(p, encoding="utf-8"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = os.path.join(base, "assets", "widget.html")
    if not curl(WIDGET, tmp, referer=False):   # 带 Referer 会被 PRTS 挡 403
        print("Widget:Data_Image 抓取失败")
        sys.exit(1)
    t = open(tmp, encoding="utf-8").read()
    pairs = re.findall(r"\n([A-Za-z0-9_]+),<a[^>]*href=\"(https://media\.prts\.wiki/[^\"]+)\"", t)
    m = {}
    for k, u in pairs:
        m.setdefault(k, u.replace("&amp;", "&"))
    json.dump(m, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("image_map", len(m), "keys")
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--quality", type=int, default=58)
    args = ap.parse_args()

    amap = build_map(args.base)
    eps = json.load(open(os.path.join(args.base, "full_events.json"), encoding="utf-8"))
    bg, cg = [], []
    for e in eps:
        for k, v in e["events"]:
            if k == "bg" and v not in bg:
                bg.append(v)
            elif k == "cg" and v not in cg:
                cg.append(v)

    out = os.path.join(args.base, "assets", "full")
    raw = os.path.join(out, "raw")
    os.makedirs(raw, exist_ok=True)
    ok = fail = 0

    for key, is_bg in [(k, True) for k in bg] + [(k, False) for k in cg]:
        if key in ("bg_black", "bg_white"):
            continue
        dst = os.path.join(out, key + ".webp")
        if os.path.exists(dst) and os.path.getsize(dst) > 2000:
            ok += 1
            continue
        u = amap.get(key) or amap.get("bg_" + key)
        if not u:
            fail += 1
            print("NOKEY", key)
            continue
        fn = u.rsplit("/", 1)[-1]
        tmp = os.path.join(raw, key + ".png")
        urls = []
        if is_bg:
            urls.append("https://media.prts.wiki/thumb/" + md5path(fn) + f"/{args.width}px-" + urllib.parse.quote(fn, safe=""))
        urls.append(u)
        got = False
        for url in urls:
            if curl(url, tmp):
                got = True
                break
        if not got:
            fail += 1
            print("FAIL", key)
            continue
        try:
            im = Image.open(tmp).convert("RGB")
            if im.width > args.width:
                im = im.resize((args.width, int(im.height * args.width / im.width)), Image.LANCZOS)
            im.save(dst, "WEBP", quality=args.quality, method=4)
            os.remove(tmp)
            ok += 1
        except Exception as e:
            fail += 1
            print("ERR", key, e)

    total = sum(os.path.getsize(os.path.join(out, f)) for f in os.listdir(out) if f.endswith(".webp"))
    print(f"ok {ok} / fail {fail} / {round(total/1024/1024,2)} MB")


if __name__ == "__main__":
    main()
