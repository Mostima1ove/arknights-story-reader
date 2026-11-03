# arknights-story-reader

一个 DSH skill：把明日方舟某个活动的剧情，从 PRTS 抓成一份**带图读本**——背景图随场景换、每句台词左边站着说话的人、手机上能一页读到底。

跑通过两次：乌萨斯《时间啊，向前！》（24 节 / 7484 句 / 141 张图）、《昨日海》（19 节 / 2889 句 / 49 张图）。

---

## 装它（三种都行，选一种）

### ① 让 DSH 自己装（最省事）

把这个链接丢给你的 DSH，加一句话：

> 帮我安装这个 skill：https://github.com/Mostima1ove/arknights-story-reader
> 做法：git clone 到 `~/.dsh/skills/` 下面，然后 `pip install pillow numpy`，装完告诉我。

DSH 会自己克隆、装依赖、告诉你重启。

### ② 一行命令

Windows PowerShell：

```powershell
irm https://raw.githubusercontent.com/Mostima1ove/arknights-story-reader/main/install.ps1 | iex
```

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/Mostima1ove/arknights-story-reader/main/install.sh | bash
```

### ③ 手动

```bash
git clone https://github.com/Mostima1ove/arknights-story-reader ~/.dsh/skills/arknights-story-reader
pip install pillow numpy
```

装完**重启 DSH**，技能列表里出现 `arknights-story-reader` 就成了。

> `~/.dsh` 就是 `%USERPROFILE%\.dsh`。如果你的 DSH 改过 `DSH_HOME`，换成对应的目录。

---

## 用它会怎样

跟 DSH 说：

> 帮我把《昨日海》的剧情做成读本

它会自己去 PRTS 找活动页、抓全部剧情、下背景和 CG、给每个说话人裁头像、排成一份 HTML，几分钟后给你一个 1–3 MB 的单文件，图上全内嵌，手机能直接开。

想指定的话：

> 做一下《时间啊，向前！》，要深色那个主题

主题有 `dark`（暖红）和 `sea`（青蓝）两套。

---

## 它做了什么

| 步骤 | 脚本 | 干什么 |
| --- | --- | --- |
| 1 | `01_fetch_pages.py` | 活动页 → 关卡代号 → 全部剧情页 wikitext |
| 2 | `02_parse_events.py` | 跟踪左/右/中立绘槽与焦点，把台词归给对的人 |
| 3 | `03_fetch_assets.py` | 从 `Widget:Data_Image` 拿资源映射，md5 拼 URL 下图 |
| 4 | `04_make_avatars.py` | alpha 找人 → 行宽扫描定头顶 → 头部行居中 |
| 5 | `05_build.py` | 图片只存一份挂 CSS 类，排成单文件 HTML |
| 6 | `06_audit.py` | 「名字 + 头像」核对页，人工扫一遍 |

细节（踩过的坑、参数怎么调）都在 [SKILL.md](SKILL.md) 里。

---

## 要求

- Python 3.10+，依赖 `pillow`、`numpy`
- 能访问 `prts.wiki` 与 `media.prts.wiki`
- 一次活动下 100–150 张图，顺序跑 3–5 分钟，不是秒出

---

## 许可

MIT。剧情文本与图片版权归鹰角网络所有，本工具只做抓取与排版，产出的文件请自用。
