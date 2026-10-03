# park-video-v2

口播视频加动效的流程。原则：**AI 只做规划和判断，渲染、合成、检查交给固定脚本。**

## 快速开始

```bash
python3 scripts/pv2.py init   <项目> --video 粗剪.mov --srt source.srt   # 然后填 v2/brief.yaml
python3 scripts/pv2.py prep   <项目>
python3 scripts/pv2.py check  <项目>            # AI 写好 v2/plan.json 后
python3 scripts/pv2.py sample <项目> --detach   # 10 秒样片，Park 看
python3 scripts/pv2.py approve <项目> sample -m "可以"
python3 scripts/pv2.py render <项目> --detach   # 整条 + 终检
python3 scripts/pv2.py status <项目>            # 在哪一步、百分之多少、在等谁
```

执行的 AI 看 `SKILL.md`。Remotion 依赖：`cd motion && npm install`。

## 四步

| 步骤 | 做什么 | 谁 |
|---|---|---|
| 1 准备 | 读 `brief.yaml`；用剪映 SRT 对齐音频出逐字时间 `words.json` | `pv2.py prep`（`scripts/align_srt.py`） |
| 2 方案 | AI 写 `plan.json`（镜头表）→ `scripts/check.py` 几秒内查完 → 渲染一段 10 秒样片，**停下等 Park 看** | AI + `pv2.py check` / `sample` |
| 3 渲染 | 和样片同一个脚本，一次渲染整条；`status.json` 写真实进度 | `pv2.py render`（`layers.py` + `render.py`） |
| 4 终审 | 解码、黑帧、静音、响度、字幕带、抽帧总览 → Park 看整条 | `qa.py`（`render` 末尾自动跑） |

10 秒样片和整条走**同一个渲染、合成脚本**，只是时间范围不同，所以样片批了，整条就是同样的质量。

## brief：Park 开头说清楚，AI 不猜

见 `brief.example.yaml`。每条视频只说：视频类型、动效怎么放（人脸两侧透明叠加 / B-roll / 全屏）、哪些时间段不加动效、字幕是否已经烧进画面、不能出现在画面上的词。缺了就停下来问，不自己判断。

## 风格和规则：填一次，每条沿用

`defaults.yaml`：卡片底色（默认毛玻璃半透明）、强调色、一张卡几条字、动效力度（默认克制）、表达形式（文字 / 数字 / 图表 / 示意图 / 图标，默认混着用）、能不能冲过头、什么时候退场、能不能改写原话（默认只能删减）、疏密、两张卡之间留多少秒纯人脸。某条视频要不一样，在它的 brief.yaml 里写同名字段覆盖。

## 程序检查（`scripts/check.py`）

- 文字不早于说出那个词的时刻
- 停住之后画面不再动
- 动效不进字幕带、不挡脸
- 不加动效的时间段里没有镜头
- defaults.yaml 里的每一条规则：不能出现的词、只能删减原话、每张卡最多几条、一张卡一个重点、字号不小于 56px、相邻两张形式不同、图标存在、动效力度、说完就走、两张卡之间的间隔

疏密只报覆盖率，不写死数量。

## 镜头库

- **Video-ShotCraft**（主库，按路径引用，不复制）：`~/.agents/skills/video-shotcraft`
- **Remotion 组件**：`motion/`，透明背景渲染，按 brief 给的区域摆放；14 个组件覆盖文字、数字、图表、示意图、图标五种形式（`motion/src/library/catalog.json`），图标来自 lucide（ISC）

## 不放进这个仓库的东西

客户名、项目素材、字幕、方案、渲染产物——都在各自的项目目录里（仓库是公开的）。
