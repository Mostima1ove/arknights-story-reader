---
name: arknights-story-reader
version: 0.6.0
description: 把明日方舟某个活动的剧情做成一份可读的「带图读本」——从 PRTS 抓剧情原文、游戏内背景与 CG、每个说话人的立绘头像，排版成手机上能一页读到底的 HTML。用于「帮我把某活动的剧情做出来／整理剧情／做成能读的版本」这类请求。
---

# 明日方舟剧情读本

把一次活动的剧情做成单文件 HTML：背景图随场景切换、每句台词左边站着说话的人、同一个人连说多句只放一次头像。

已跑通四次：乌萨斯《时间啊，向前！》（24 节 / 7484 句 / 141 图）、《昨日海》（19 节 / 2889 句 / 49 图）、《喧闹法则》（27 幕 / 2847 句 / 22 图）、《月行水上》（13 幕 / 1978 句 / 52 图）。

## 前置

- Python 3.10+，依赖：`pip install pillow numpy opencv-python-headless`（opencv 用来找人脸，裁头像那步要用）。DSH 自带的 Python 也能用（`%USERPROFILE%\.dsh\dsh-runtimes\...`）。
- PRTS 的 API 不需要登录，但**必须带 UA**，重定向要 `-L`。
- 工作目录自选，建议 `<你的工作区>\prts-<活动代号>\`，脚本会自己建 `raw/`、`assets/`、`cast/`。

## 一条命令

```
python scripts/run.py --name 月行水上 --base D:\work\prts-sr --theme sea --audit
```

六步串起来跑完；`--theme` 选 dark/sea，`--audit` 顺带出核对页，`--code` 在自动识别代号失败时手动给。

想单独跑某一步，下面就一步一条。

## 五步流程

### 0. 顺序别信编号

**排序永远读活动页里的 `{{关卡链接|…}}` 列表**，不要按文件名/编号排。序幕 `SR-ST-1` 在列表最前面，按编号排会掉到最后；`CB-ST1` 要插在第五关之后。同一关里 BEG 在前、END 在后。

### 1. 找到活动与剧情页

```
GET https://prts.wiki/api.php?action=query&list=search&srsearch=<活动名>&srlimit=20&format=json&formatversion=2
GET https://prts.wiki/api.php?action=parse&page=<活动页>&prop=wikitext&format=json&formatversion=2&redirects=1
```

活动页的 wikitext 里有关卡代号（`{{关卡链接|YW-1}}` 这种）。再搜 `srsearch=<代号>-` 拿全页面标题，剧情页命名是 `<代号>-<序号> <关卡名>/BEG|END|NBT`（纯剧情是 NBT）。

跑 `scripts/01_fetch_pages.py --base <dir> --pages <列表>` 批量下 wikitext。

### 2. 解析成事件流

跑 `scripts/02_parse_events.py --base <dir>`，产出 `full_events.json`（每幕的事件数组）和 `who_char.json`（说话人 → 立绘 id）。

**这一步是质量的关键**，三个坑：

1. **charslot 的写法不统一**：`[charslot(slot="l", name="avg_npc_2274_1#1$1")]` 和 `[charslot(slot = "l", name = "avg_npc_2274_1#1$1")]` 都有，正则要容忍空格：`name\s*=\s*"([^"]+)"`。
2. **同一屏有三个人**：必须跟踪 `slot`（l/r/m）和 `focus`，台词归给当前 focus 那个槽，不能"取最近设置的立绘"。
3. 角色会有多个立绘 id（换装），按出现频率取主 id，但**渲染时按每句的 char 走**，别只存一个。

### 3. 抓背景与 CG

PRTS 的资源 key 在 `Widget:Data_Image` 里（一个 680KB 的 HTML）：

```
GET https://prts.wiki/w/Widget:Data_Image
```

解析出 `key,<a href="https://media.prts.wiki/1/1d/Avg_bg_bg_coldforest.png">`，地图存成 `image_map.json`。

- 背景 key = `bg_` + wikitext 里的名字（`Background(image="bg_coldforest")` → key `bg_bg_coldforest`）。
- CG key 直接用（`79_i01` → `Avg_79_i01.png`）。
- 文件 URL 走 MediaWiki 的 md5 规则：`<h[0]>/<h[0:2]>/<文件名>`，文件名里的 `$` 编码成 `%24`。
- 新活动的图常常没有 thumb（302 或 403），**直接下原图**再压缩。

跑 `scripts/03_fetch_assets.py --base <dir>`：背景下 640px 缩略、CG 下原图，统一转 webp 640/q58，跳过 `bg_black`/`bg_white`。

### 4. 立绘 → 头像

跑 `scripts/04_make_avatars.py --base <dir>`。这版是第 12 次试出来的，别自己改顺序：

1. 立绘是 **RGBA 透明底**，用 alpha 通道找人（`alpha > 24`），**不要用颜色差**——白底/渐变会骗人。
2. 头顶用**行宽扫描**：从上往下，第一行宽度 > 人物宽 8% 的位置。这样能跳过飘带、剑尖、尾巴。
3. 横向中心用**头部那一行的中位数**，不是整张画布的中间（人物常常偏左，旁边还立着武器）。
4. 裁 `人物高 × 0.16` 的正方形，从头顶往下取，左下填米色 `(238,234,226)`——透明区域直接转 RGB 会变黑，看着全是杂色。
5. 裁出来如果几乎全是背景色，按 0.16 → 0.26 → 0.40 放大重试；还不行就是立绘本身遮脸（兜帽、面具），接受。

### 5. 生成读本

跑 `scripts/05_build.py --base <dir> --title <活动名> --out <file.html> --theme dark|sea`。

排版要点：

- 图片全部 base64 内嵌；**同一张图只出现一次**，用 CSS 类挂 `background-image`，HTML 里只写类名（不然 100 个头像能把文件撑到 10MB）。
- 台词块：左侧 56×72 头像 + 右侧名字（暖色小字）+ 台词；连续同一说话人合并成一个块，头像只放一次。
- 场景：`<div class="sc">` 高 130–190，跟背景一起切换；CG 高一点。
- 深色底（`#17181b` / 暖字）比白底更耐看，手机晚上读不刺眼。
- **整页缩放用 `transform: scale()`，不要用 `zoom`**：`zoom` 只缩文字、图片不跟；transform 把整页包一层 `#page`（宽 900）再整体缩，字图一起变。窗口 `< 940px` 时按 `w/940` 缩，下限 0.3；body 高度要跟着 `page.offsetHeight * z` 补，不然底部会被切。
- 字号给个 `A− / A+` 按钮调倍率（`--k`，0.8–1.8），存 localStorage；边距用 `clamp(14px, 4.2vw, 26px)` 自适应，不设按钮。
- 场景图用 `<img>` 直接完整显示（`width:100%;height:auto;border-radius:10px`），不要固定高度 + `cover`，那是裁图。代价是文件会大（时间啊 7MB / 月行水上 3.4MB），可接受。

## 核对

跑 `scripts/06_audit.py --base <dir>` 生成 `audit.html`：所有「名字 + 头像」按出场次数排开，一眼能扫出错位的。

已知会"看着不对"但其实是立绘本身的情况：兜帽遮脸（瓦列里奥）、面具（惩戒军）、纯生物（海嗣）、画外音（「稳重的男声」没有立绘）。

## 硬性提醒

- 下载**顺序执行**，别并发；一次活动 100–150 张图，总共 2–4 分钟。
- 每张图下完就转 webp 并删原图，别把几百 MB 堆在盘上。
- 最终 HTML 控制在 3.5MB 以内（乌萨斯 3.0MB、昨日海 1.1MB 是正常值）。
- 中文路径下 OpenCV 读不了图（`imread` 返回 None），要 `np.fromfile` + `cv2.imdecode`；CascadeClassifier 也要放纯英文路径。

## 变更记录

- **v0.6** 一键 `run.py`；目录抽屉、图片点开放大、阅读位置记忆；（`shelf.py` 留作内部用，暂不对外）

- **v0.5** 整页 `transform` 缩放（`zoom` 只缩字不缩图）、字号倍率按钮、场景图不裁只圆角、顺序改为读活动页关卡列表
- **v0.4** 人脸检测优先（光环/帽子靠脸定位），裁切 2.0 倍脸宽，误检取最靠上的框
- **v0.3** 立绘归属按「第一次开口」校准，修同屏沿用上一个人的问题
- **v0.2** 兼容老活动的 `[Character(name=...)]`、文件名冒号转义、Widget 免 Referer
- **v0.1** 抓页、解析、下图、裁头像、排版六步跑通
