# -*- coding: utf-8 -*-
"""一条命令跑完整个流程。

用法：
  python run.py --name 月行水上 --base D:\\work\\prts-sr --theme sea
  python run.py --name 月行水上 --base ... --code SR       # 代号自动识别失败时手动给
  python run.py --name 月行水上 --base ... --audit         # 顺带出核对页
"""
import argparse, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def run(script, args):
    cmd = [sys.executable, os.path.join(HERE, script)] + args
    print("\n$", " ".join(os.path.basename(cmd[1]) if i == 1 else c for i, c in enumerate(cmd[1:], 1)))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        print(f"[失败] {script} 退出码 {r.returncode}")
        sys.exit(r.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="活动名，如 月行水上")
    ap.add_argument("--base", required=True, help="工作目录，会自动建 raw/assets/cast")
    ap.add_argument("--code", default=None, help="关卡代号前缀，如 SR；不填就自动猜")
    ap.add_argument("--theme", default="sea", choices=["dark", "sea"])
    ap.add_argument("--out", default=None, help="输出 html；默认 <base>/<活动名>-剧情全文.html")
    ap.add_argument("--audit", action="store_true", help="最后生成头像核对页")
    args = ap.parse_args()

    base = os.path.abspath(args.base)
    os.makedirs(base, exist_ok=True)
    out = args.out or os.path.join(base, f"{args.name}-剧情全文.html")

    p1 = ["--base", base, "--name", args.name]
    if args.code:
        p1 += ["--code", args.code]
    run("01_fetch_pages.py", p1)
    run("02_parse_events.py", ["--base", base])
    run("03_fetch_assets.py", ["--base", base])
    run("04_make_avatars.py", ["--base", base])
    run("05_build.py", ["--base", base, "--title", args.name, "--theme", args.theme, "--out", out])
    if args.audit:
        run("06_audit.py", ["--base", base, "--title", args.name])

    print("\n完成：", out)


if __name__ == "__main__":
    main()
