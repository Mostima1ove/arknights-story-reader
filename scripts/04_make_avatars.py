# -*- coding: utf-8 -*-
"""04 按剧情立绘 id 下载立绘，裁成头像。

用法：python 04_make_avatars.py --base <dir>

产出 cast/img2/<id>.png、cast/avatar/<id>.png（168x216）
"""
import argparse, hashlib, json, os, subprocess, sys, urllib.parse
import numpy as np
from PIL import Image

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
BG = (238, 234, 226)
W, H = 168, 216


def md5path(fn):
    h = hashlib.md5(fn.encode()).hexdigest()
    return f"{h[0]}/{h[:2]}/{urllib.parse.quote(fn, safe='')}"


def fetch(cid, imgdir):
    dst = os.path.join(imgdir, cid + ".png")
    if os.path.exists(dst) and os.path.getsize(dst) > 5000:
        return True
    for fn in (f"Avg_{cid}-1$1.png", f"Avg_{cid}.png", f"Avg_{cid}$1.png", f"Avg_{cid}-2$1.png"):
        p = md5path(fn)
        for url in ("https://media.prts.wiki/" + p,
                    "https://media.prts.wiki/thumb/" + p + "/380px-" + urllib.parse.quote(fn, safe="")):
            subprocess.run(["curl.exe", "-s", "-L", "-m", "90", "-A", UA,
                            "-H", "Referer: https://prts.wiki/", url, "-o", dst], capture_output=True)
            if os.path.exists(dst) and os.path.getsize(dst) > 5000:
                with open(dst, "rb") as f:
                    if f.read(8) == b"\x89PNG\r\n\x1a\n":
                        return True
    return False


def head_crop(path):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im)
    mask = a[..., 3] > 24
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
    pw, ph = max(1, x1 - x0), max(1, y1 - y0)
    # 头顶：跳过飘带、剑尖、尾巴
    top = y0
    for yy in range(y0, min(im.height, y0 + int(ph * 0.45))):
        if mask[yy].sum() > pw * 0.08:
            top = yy
            break
    # 横向：按头部那一行的中位数
    row = min(im.height - 1, top + max(4, int(ph * 0.04)))
    cx = int(np.median(np.where(mask[row])[0])) if mask[row].sum() else (x0 + x1) // 2

    def cut(side):
        left = max(0, min(im.width - side, cx - side // 2))
        c = im.crop((left, max(0, top - int(side * 0.06)),
                     left + side, min(im.height, top + int(side * 0.94))))
        bg = Image.new("RGBA", c.size, BG + (255,))
        bg.alpha_composite(c)          # 透明区填米色，别留黑
        return bg.convert("RGB")

    for ratio in (0.16, 0.26, 0.40):
        side = max(40, int(ph * ratio))
        img = cut(side)
        arr = np.asarray(img).astype(np.int16)
        nb = (np.abs(arr - np.array(BG)).sum(axis=2) > 40).mean()
        if 0.06 < nb < 0.92 and arr.mean() > 55:
            return img.resize((W, H), Image.LANCZOS)
    return img.resize((W, H), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    args = ap.parse_args()
    imgdir = os.path.join(args.base, "cast", "img2")
    avdir = os.path.join(args.base, "cast", "avatar")
    os.makedirs(imgdir, exist_ok=True)
    os.makedirs(avdir, exist_ok=True)

    rows = json.load(open(os.path.join(args.base, "who_char.json"), encoding="utf-8"))
    ids, seen = [], set()
    for n, v, cid in rows:
        if cid and cid != "-" and cid not in seen:
            seen.add(cid)
            ids.append((cid, n))

    ok, fail = 0, []
    for cid, name in ids:
        if not fetch(cid, imgdir):
            fail.append((cid, name))
            continue
        try:
            head_crop(os.path.join(imgdir, cid + ".png")).save(os.path.join(avdir, cid + ".png"))
            ok += 1
        except Exception as e:
            fail.append((cid, name))
    print(f"头像 {ok} / 失败 {len(fail)}")
    for cid, name in fail:
        print("  FAIL", cid, name)


if __name__ == "__main__":
    main()
