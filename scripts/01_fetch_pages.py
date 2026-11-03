# -*- coding: utf-8 -*-
"""01 抓活动页与全部剧情页 wikitext。

用法：
  python 01_fetch_pages.py --base D:\\阁楼\\DS-work\\prts-xxx --name 昨日海
如果活动页的名字和剧情页代号不同，可以补 --code YW。
"""
import argparse, json, os, re, subprocess, sys, time, urllib.parse

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"
API = "https://prts.wiki/api.php"


def curl(url, out):
    subprocess.run(["curl.exe", "-s", "-L", "-m", "90", "-A", UA,
                    "-H", "Accept-Language: zh-CN,zh;q=0.9", url, "-o", out], capture_output=True)
    return os.path.exists(out) and os.path.getsize(out) > 200


def api(params):
    return API + "?" + urllib.parse.urlencode(params)


def search(q, limit=50, ns=0):
    url = api({"action": "query", "list": "search", "srsearch": q, "srlimit": limit,
               "srnamespace": ns, "format": "json", "formatversion": 2})
    out = "_s.json"
    curl(url, out)
    try:
        j = json.load(open(out, encoding="utf-8"))
        return [x["title"] for x in j.get("query", {}).get("search", [])]
    except Exception:
        return []


def allpages(prefix):
    """按标题前缀列页面。比全文搜索可靠：搜索会把 CB- 里的 - 当成排除语法。"""
    out = "_ap.json"
    url = api({"action": "query", "list": "allpages", "apprefix": prefix,
               "aplimit": 200, "format": "json", "formatversion": 2})
    curl(url, out)
    try:
        j = json.load(open(out, encoding="utf-8"))
        return [x["title"] for x in j.get("query", {}).get("allpages", [])]
    except Exception:
        return []


def wikitext(page, out):
    url = api({"action": "parse", "page": page, "prop": "wikitext",
               "format": "json", "formatversion": 2, "redirects": 1})
    if not curl(url, out):
        return None
    try:
        return json.load(open(out, encoding="utf-8"))["parse"]["wikitext"]
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--name", required=True, help="活动名，如 昨日海")
    ap.add_argument("--code", default=None, help="关卡代号前缀，如 YW；不给就从活动页里挖")
    args = ap.parse_args()
    raw = os.path.join(args.base, "raw")
    os.makedirs(raw, exist_ok=True)

    # 1) 活动页
    act = wikitext(args.name, os.path.join(raw, "act.json"))
    if not act:
        print("活动页抓取失败，先确认名字：", args.name)
        sys.exit(1)
    code = args.code
    if not code:
        codes = re.findall(r"\{\{关卡链接\|([A-Za-z]+)-", act)
        code = codes[0] if codes else None
    if not code:
        print("找不到关卡代号，用 --code 指定")
        sys.exit(1)
    print("关卡代号", code)

    # 2) 剧情页
    titles = allpages(code + "-")
    if not titles:
        titles = search(code + "-", limit=50)
    pages = [t for t in titles if "/" in t]

    # 顺序照活动页的关卡列表来（序幕 ST 可能排在最后，不能按编号排）
    order = {c: i for i, c in enumerate(re.findall(r"\{\{关卡链接\|([^}\]]+)\}\}", act))}

    def sort_key(pg):
        c = pg.split(" ")[0]
        part = pg.split("/")[-1].upper()
        seq = 0 if part in ("BEG", "NBT") else 1
        return (order.get(c, 999), seq, pg)

    pages.sort(key=sort_key)
    print("剧情页", len(pages))

    # 3) 下载
    for i, p in enumerate(pages, 1):
        safe = re.sub(r'[\\/:*?"<>|]', "_", p)   # 冒号在 Windows 上非法，会截断文件名
        out = os.path.join(raw, f"{i:02d}_" + safe + ".json")
        if os.path.exists(out) and os.path.getsize(out) > 3000:
            continue
        if wikitext(p, out):
            print(f"{i:02d} OK {p}")
        else:
            print(f"{i:02d} FAIL {p}")
        time.sleep(0.6)
    json.dump(pages, open(os.path.join(args.base, "pages.json"), "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
