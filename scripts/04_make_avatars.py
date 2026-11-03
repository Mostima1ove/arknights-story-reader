# -*- coding: utf-8 -*-
"""04 按剧情立绘 id 下载立绘，裁成头像。

用法：python 04_make_avatars.py --base <dir>

产出 cast/img2/<id>.png、cast/avatar/<id>.png（168x216）
"""
import argparse, hashlib, json, os, subprocess, sys, urllib.parse
import numpy as np
import cv2
from PIL import Image

CASCADE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lbpcascade_animeface.xml")
_cascade = None

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


def face_box(path, w, h):
    """先用二次元人脸模型找脸：有光环、戴帽子的角色靠它定位。找不到返回 None。"""
    global _cascade
    if _cascade is None:
        _cascade = cv2.CascadeClassifier(CASCADE_PATH)
        if _cascade.empty():
            _cascade = False
    if _cascade is False:
        return None
    try:
        data = np.fromfile(path, np.uint8)
        bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if bgr is None:
            return None
        gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
        faces = _cascade.detectMultiScale(gray, 1.06, 3, minSize=(40, 40))
        cands = []
        for f in faces:
            fx, fy, fw, fh = [int(v) for v in f]
            if fy > h * 0.45 or fw > w * 0.55:      # 脸不该在画布下半部分，也不该比肩还宽
                continue
            if not (0.6 < fw / max(1, fh) < 1.6):   # 差不多是方的
                continue
            cands.append(f)
        if not cands:
            return None
        # 一张图上偶尔会误检出手、腿；脸总在最上面，取 y 最小的
        return min(cands, key=lambda f: int(f[1]))
    except Exception:
        return None


def head_crop(path):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im)
    mask = a[..., 3] > 24

    fb = face_box(path, im.width, im.height)
    if fb is not None:
        fx, fy, fw, fh = [int(v) for v in fb]
        cx, cy = fx + fw // 2, fy + fh // 2
        side = max(40, int(max(fw, fh) * 2.0))
        left = max(0, min(im.width - side, cx - side // 2))
        top = max(0, min(im.height - side, cy - int(side * 0.42)))
        c = im.crop((left, top, left + side, top + side))
        bg = Image.new("RGBA", c.size, BG + (255,))
        bg.alpha_composite(c)
        return bg.convert("RGB").resize((W, H), Image.LANCZOS)
    a = np.asarray(im)
    mask = a[..., 3] > 24
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max(), ys.max()
    pw, ph = max(1, x1 - x0), max(1, y1 - y0)
    # 回退：找第一段「连续够宽」的头顶；扫到的位置太靠下就说明被手/袋子骗了，退回 bbox 顶
    need = max(3, int(ph * 0.02))
    run = 0
    top = y0
    for yy in range(y0, min(im.height, y0 + int(ph * 0.55))):
        if mask[yy].sum() > pw * 0.10:
            run += 1
            if run >= need:
                top = yy - run + 1
                break
        else:
            run = 0
    if top - y0 > ph * 0.15:      # 头顶不该离人物顶端这么远
        top = y0
    # 横向：按头顶往下一点那一行取中位数
    row = min(im.height - 1, top + max(4, int(ph * 0.04)))
    cx = int(np.median(np.where(mask[row])[0])) if mask[row].sum() else (x0 + x1) // 2
    head_side = max(40, int(ph * 0.13 * 2.0))   # 和 cv 分支的「3.2 倍脸宽」对齐

    def cut(side):
        left = max(0, min(im.width - side, cx - side // 2))
        c = im.crop((left, max(0, top - int(side * 0.10)),
                     left + side, min(im.height, top + int(side * 0.90))))
        bg = Image.new("RGBA", c.size, BG + (255,))
        bg.alpha_composite(c)
        return bg.convert("RGB")

    return cut(head_side).resize((W, H), Image.LANCZOS)


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
