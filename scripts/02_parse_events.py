# -*- coding: utf-8 -*-
"""02 把 raw/*.json 解析成事件流：bg / cg / say / narr。

用法：python 02_parse_events.py --base <dir>

产出：
  full_events.json  [{file,title,events:[(kind,value)]}]
  who_char.json     [(说话人, 台词数, 主立绘id)]
"""
import argparse, collections, glob, json, os, re, sys

BG_RE = re.compile(r'\[Background\(\s*image\s*=\s*"([^"]+)"')
CG_RE = re.compile(r'\[Image\(\s*image\s*=\s*"([^"]+)"')
CS_RE = re.compile(r"\[charslot\((.*?)\)\]")
CHAR_RE = re.compile(r'\[Character\(\s*name\s*=\s*"([^"]+)"', re.I)   # 老活动（2020 年前）用这个
ATTR_RE = re.compile(r'(\w+)\s*=\s*"?([^",$)]+)')
NAME_RE = re.compile(r'^\[name\s*=\s*"([^"]+)"\]\s*(.*)$')
TICK_RE = re.compile(r"\[[A-Za-z][^\]]*\]")


def parse_body(w):
    i = w.find("|文本数据=")
    body = w[i + len("|文本数据="):] if i >= 0 else w
    return body.rstrip("}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    args = ap.parse_args()
    raw = os.path.join(args.base, "raw")
    files = [p for p in sorted(glob.glob(os.path.join(raw, "*.json")))
             if re.match(r"^\d\d_", os.path.basename(p))]

    episodes = []
    for fp in files:
        try:
            j = json.load(open(fp, encoding="utf-8"))
        except Exception as e:
            print("跳过坏文件", os.path.basename(fp), e)
            continue
        body = parse_body(j["parse"]["wikitext"])
        events, slots, focus = [], {}, None
        for line in body.split("\n"):
            ln = line.strip()
            if not ln:
                continue
            m = BG_RE.search(ln)
            if m:
                events.append(("bg", m.group(1)))
                continue
            m = CG_RE.search(ln)
            if m:
                events.append(("cg", m.group(1)))
                continue
            m = CHAR_RE.search(ln)
            if m:
                slots = {"m": m.group(1).split("#")[0]}
                focus = "m"
                continue
            if re.fullmatch(r"\[Character\]", ln, re.I):
                slots, focus = {}, None
                continue
            m = CS_RE.search(ln)
            if m:
                attrs = dict((k, v) for k, v in ATTR_RE.findall(m.group(1)))
                slot = (attrs.get("slot") or "").strip().lower()
                slot = {"left": "l", "right": "r", "middle": "m"}.get(slot, slot)
                nm = attrs.get("name")
                if nm:
                    key = slot if slot in ("l", "r", "m") else "m"
                    slots[key] = nm.split("#")[0]
                    if focus is None:
                        focus = key
                fo = attrs.get("focus")
                if fo:
                    fo = fo.strip().lower()
                    focus = {"left": "l", "right": "r", "middle": "m"}.get(fo, fo)
                continue
            if re.fullmatch(r"\[charslot\]", ln):
                slots, focus = {}, None
                continue
            m = NAME_RE.match(ln)
            if m:
                txt = TICK_RE.sub("", m.group(2)).strip()
                if txt:
                    events.append(("say", {"who": m.group(1), "text": txt,
                                           "char": slots.get(focus) if focus else None}))
                continue
            if ln.startswith("[") and ln.endswith("]"):
                continue
            txt = TICK_RE.sub("", ln).strip()
            txt = re.sub(r'\[name\s*=\s*"[^"]*"\]', "", txt).strip()
            if txt:
                events.append(("narr", txt))
        episodes.append({"file": os.path.basename(fp), "title": j["parse"]["title"], "events": events})

    json.dump(episodes, open(os.path.join(args.base, "full_events.json"), "w", encoding="utf-8"),
              ensure_ascii=False)

    cnt = collections.Counter()
    pair = collections.defaultdict(collections.Counter)
    for e in episodes:
        for k, v in e["events"]:
            if k == "say":
                cnt[v["who"]] += 1
                pair[v["who"]][v["char"] or "-"] += 1

    # 先算每个立绘 id 的「主说话人」，用来剔除“沿用上一个人的立绘”造成的错配
    char_main = collections.defaultdict(collections.Counter)
    for who, c in pair.items():
        for ch, n in c.items():
            if ch != "-":
                char_main[ch][who] += n
    char_main = {ch: c.most_common(1)[0][0] for ch, c in char_main.items()}

    # 第一次开口时画面上的立绘最可靠（那时一定刚切到这个人）
    first = {}
    for e in episodes:
        for k, v in e["events"]:
            if k == "say" and v.get("char") and v["who"] not in first:
                first[v["who"]] = v["char"]

    rows = []
    for who, v in cnt.most_common():
        ch = first.get(who)
        if ch and char_main.get(ch) == who:
            rows.append((who, v, ch))
            continue
        cands = [(n, c) for c, n in pair[who].items() if c != "-" and char_main.get(c) == who]
        if cands:
            rows.append((who, v, max(cands)[1]))
            continue
        # 兜底：没有「确证属于自己」的立绘时，用第一次开口时画面上的那个。
        # 宁可给个候选也别判成无立绘——05 建读本时还会用 char_main 再校一次，
        # 真正的错配在那儿会被换回来；这里判死就永远找不回来了（阿米娅就是这么丢的）。
        rows.append((who, v, ch or "-"))

    json.dump(rows, open(os.path.join(args.base, "who_char.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(char_main, open(os.path.join(args.base, "char_main.json"), "w", encoding="utf-8"), ensure_ascii=False)

    says = sum(cnt.values())
    narrs = sum(1 for e in episodes for k, _ in e["events"] if k == "narr")
    print(f"幕 {len(episodes)} / 台词 {says} / 旁白 {narrs} / 说话人 {len(rows)}"
          f" / 无立绘 {sum(1 for r in rows if r[2] == '-')}")


if __name__ == "__main__":
    main()
