# arknights-story-reader

一个 DSH skill：把明日方舟某个活动的剧情，从 PRTS 抓成一份**带图读本**——背景图随场景切换、每句台词左边站着说话的人、手机上能一页读到底，整本可全文搜索。

跑通过：乌萨斯《时间啊，向前！》、《昨日海》、《喧闹法则》、《月行水上》。

## 装它

把链接丢给你的 DSH：

> 帮我装这个 skill：https://github.com/Mostima1ove/arknights-story-reader

或者一行命令：

```powershell
irm https://raw.githubusercontent.com/Mostima1ove/arknights-story-reader/main/install.ps1 | iex
```

macOS / Linux：

```bash
curl -fsSL https://raw.githubusercontent.com/Mostima1ove/arknights-story-reader/main/install.sh | bash
```

装完**重启 DSH**，技能列表里出现 `arknights-story-reader` 就能用。

> `~/.dsh` 就是 `%USERPROFILE%\.dsh`。改过 `DSH_HOME` 的换成对应目录。

## 用它

跟 DSH 说：

> 帮我把《月行水上》的剧情做成读本

它会自己找活动页、抓全部剧情、下背景和 CG、给每个说话人裁头像、排成一份 HTML，几分钟后给你一个 1–7 MB 的单文件，图上全内嵌，手机能直接开。

想指定：

> 做一下《喧闹法则》，要海边那个青色主题

主题有 `dark`（暖红）和 `sea`（青蓝）。

## 一条命令（不走模型也行）

```bash
python scripts/run.py --name 月行水上 --base D:\work\prts-sr --theme sea --audit
```

`--audit` 顺带生成头像核对页，`--code` 在自动识别代号失败时手动给。

## 它做了什么

| 步骤 | 脚本 | 干什么 |
| --- | --- | --- |
| 1 | `01_fetch_pages.py` | 活动页 → 关卡代号 → 全部剧情页（顺序照活动页的关卡列表） |
| 2 | `02_parse_events.py` | 跟踪左/右/中立绘槽与焦点，按“第一次开口”校准归属 |
| 3 | `03_fetch_assets.py` | 从 `Widget:Data_Image` 拿资源映射，md5 拼 URL 下图 |
| 4 | `04_make_avatars.py` | 先用二次元人脸模型找脸，失败退回行宽扫描 |
| 5 | `05_build.py` | 图片只存一份挂 CSS 类，排成单文件 HTML |
| 6 | `06_audit.py` | 「名字 + 头像」核对页 |

读本里带：全文搜索（输台词或人名，点结果直接跳过去）、场景图与头像各一个开关（关了就剩纯文字，关一次会记住）、目录抽屉、图片点开放大、字号与图片缩放按钮、整页等比缩放、阅读位置记忆。

细节和踩过的坑都写在 [SKILL.md](SKILL.md)。

## 要求

- Python 3.10+，依赖 `pillow`、`numpy`、`opencv-python-headless`
- 能访问 `prts.wiki` 与 `media.prts.wiki`
- 一次活动下 50–150 张图，顺序跑 3–5 分钟，不是秒出
- 第一次裁头像时会自动下一份人脸检测模型（约 240KB，来自 [nagadomi/lbpcascade_animeface](https://github.com/nagadomi/lbpcascade_animeface)），存到 `~/.cache/arknights-story-reader/`。原作者没写许可证，这个文件就不随仓库分发；下载不通的话，按报错里给的路径手动放一份也能用

## 许可

MIT。剧情与图片版权归鹰角网络所有，产出仅供自用。
