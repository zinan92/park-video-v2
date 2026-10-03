---
name: park-video-v2
description: 给口播视频加动效（Remotion 透明层叠到原画面）。Park 说「给这条视频加动效」「做动效样片」「用新流程跑这条」时使用。AI 只写方案，渲染、合成、检查都交给 scripts/pv2.py。
---

# 口播动效 v2：操作说明（给执行的 AI）

**你只做两件事：问清 brief、写 plan.json。** 渲染、合成、检查全部用 `scripts/pv2.py`，不要自己写渲染脚本、不要手动调 ffmpeg / remotion。

## 流程

1. **brief（Park 说，你不猜）**
   `python3 scripts/pv2.py init <项目> --video <粗剪> --srt <剪映SRT>`，然后把 Park 的原话填进 `<项目>/v2/brief.yaml`。
   每条视频只问 Park 这几项：视频类型、动效怎么放（`overlay-sides` 人脸居中两侧透明叠加 / `broll` / `fullscreen`）、哪些时间段不加动效、字幕是否已烧进画面、**不能出现在画面上的词**（客户名、地名…，写进项目的 `banned_words`，绝不写进本仓库）。
   人脸位置 `face_box` 和字幕带 `caption_band`：从粗剪的真实画面截两帧量，不要猜。
   风格和规则（**密度**、**努力程度**、卡片底色、强调色、能不能改写原话……）全部列在 `settings.yaml`，默认值在 `defaults.yaml`（Park 在工作台设的默认值在 `~/.config/park-video-v2/defaults.yaml`，优先），**不要再问**。他说这条要不一样，用 `pv2.py set <项目> --json '{...}'` 改（会先校验、还没做的档位会被拒），不要手改 yaml。`pv2.py settings <项目>` 看当前取值和来源。音效、背景音乐不在这个流程里（Park 在剪映加）。
2. **prep**：`python3 scripts/pv2.py prep <项目>` → `v2/words.json`（SRT 对齐音频，约 30 秒）。
3. **写 plan.json**（见下）→ `python3 scripts/pv2.py check <项目>`，输出 `[]` 才算过。
4. **样片**：`python3 scripts/pv2.py sample <项目> --detach`，用 `status` 看进度。完成后**停下**，把 `v2/sample.mp4` 发给 Park。
5. Park 认可后：`python3 scripts/pv2.py approve <项目> sample -m "<Park 原话>"`。
6. **整条**：`python3 scripts/pv2.py render <项目> --detach`（层 → 合成 → 终检，`status` 里有真实百分比）。完成后把 `v2/final.mp4`、`v2/contact.jpg` 给 Park。
7. Park 确认：`python3 scripts/pv2.py approve <项目> final -m "<Park 原话>"`。

Park 问进度时跑 `status`，报 `step` / `percent` / `waiting_for`，不要估。

## 写 plan.json 的原则

先读 brief（含 defaults.yaml 合并后的值），照着规则写，**一次写对，不要靠 check 报错再改**。check 会拦下所有违反下面规则的镜头。

- **只用他说出口的话和数字。** 每段文字的出现时刻 = 他说出这句话的时刻：`python3 scripts/pv2.py find <项目> "原话"` 查。
- `rewrite: trim-only`：卡上每一段字（含 kicker、标题）都只能从原话里删字得到，不能换词、不能加词。「非常重要」不能写成「最重要」。
- `banned_words`：一个都不能出现在卡上。
- `max_items`：lines / items / notes 每样不超过这么多条。`text_amount: one-point`：一张卡一个重点，卡上字加起来不超过 24 个。
- **一行要短**：TextLines 每行不折行、按区域宽度定字号，字号低于 56px 会被拦下。右侧窄区一行大约 7 个字以内，长句拆成两三行。
- **两把主旋钮**：
  - `density` 管**多少**：动效时长占可加动效时长（去掉 no_motion）的比例，low 10–20% / medium 30–40% / high 50% 以上；brief 里写 `coverage: [下限, 上限]` 可以直接指定。check 不在区间就拦。按内容挑够卡、每张停够时间来凑比例，不要塞空卡。
  - `effort` 管**多精**：a 文字卡 / b 图表、示意图、图标 / c 层次丰富、像专业 AE / d 先用 Codex 画图再做动画。组件的努力程度见 `motion/src/library/catalog.json`，不能超过 brief 的档；低于这一档的卡最多占 40%。
- 相邻两张卡不能同一种形式（text / number / chart / diagram / icon）。
- 每张卡至少停 2.5 秒。`exit: until-next` 时停到下一张出来前（中间留 `min_gap` 秒），但最后一句说完后最多再停 10 秒。
- 内容多的卡（三条、飞轮、对照、条形图）放左右里更宽的那块区域。
- `prefer`（偏爱的样式）优先用；`avoid`（不用的样式）check 会拦。
- `exit: after-sentence`：卡片在最后一句说完后 1.5 秒内退场。
- `min_gap`：两张卡之间至少留这么多秒纯人脸。
- `density`：low 只放关键数字和结论 / medium / high 每个论点都配。check 会报覆盖率，只做参考，不写死数量。
- 左右区域交替；不在 brief 的 `no_motion` 时间段放镜头；镜头里的静态文字也算出现，镜头 `start` 不能早于说出它。

```json
{"duration": 577.97,
 "shots": [{"id": "V01", "start": 1.2, "end": 13.4, "zone": "left", "component": "NumberRoll",
            "props": {"value": "6000", "unit": "粉丝", "lockAt": 2.22, "notes": [{"text": "3个小时", "at": 3.82}]},
            "reveals": [{"at": 2.22, "text": "6000粉丝"}, {"at": 3.82, "text": "3个小时"}],
            "hold": 12.0}]}
```

- `zone`：`left` / `right`（由 brief 的人脸位置推出）、`full`，或 `{x, y, w, h}`
- `reveals`：每段文字的出现时刻和原话，给 check 查「不早于说出口」
- `hold`：从这一刻起画面不再动（终检会实测）
- `props` 里所有时刻都是原片绝对秒

## 组件（`motion/src/library/`）

组件的努力程度和表达形式登记在 `motion/src/library/catalog.json`。**相邻两张卡不能是同一种形式**；按内容挑最贴的形式（数字就用数字卡，比例用图表，先后/因果用流程，循环用飞轮，筛选用漏斗，对照用对照，概念配图标），不要全用文字。

| 组件 | 形式 | 努力程度 | 用在 | props |
|---|---|---|---|---|
| `TextLines` | text | a | 一个重点（大字） | `kicker?`, `lines[]`, `ats[]`, `accent?[]` |
| `Quote` | text | a | 他问的一句话、一句原话金句 | `lines[]`, `ats[]`, `accent?[]` |
| `ListSteps` | text | a | 编号要点 | `kicker?`, `items[]`, `ats[]` |
| `BigNumber` | number | a | 一个关键数字整块出现 | `value`, `unit?`, `at`, `caption?`, `captionAt?` |
| `NumberRoll` | number | b | 数字滚动锁定 | `value`, `unit?`, `lockAt`, `notes?[{text, at}]` |
| `Ratio` | chart | b | 一个百分比（环形） | `value`(0–100), `at`, `caption?`, `captionAt?` |
| `Bars` | chart | b | 2–3 个数量对比（横条） | `kicker?`, `bars[{label, value, display?, at}]`, `accent?[]` |
| `Gauge` | chart | b | 仪表指针 | `kicker?`, `value`(0–100), `at`, `label?` |
| `Flow` | diagram | b | 先后、因果（A ↓ B） | `kicker?`, `steps[{text, at}]`, `accent?[]` |
| `Cycle` | diagram | b | 飞轮、循环 | `nodes[{text, at}]`, `center?`, `centerAt?`, `accent?[]` |
| `Funnel` | diagram | b | 层层筛选，最后一层是结论 | `kicker?`, `layers[{text, at}]` |
| `Compare` | diagram | b | 两件事对照（≠ / → / +） | `kicker?`, `top{title, sub?, at}`, `bottom{…}`, `symbol`, `symbolAt` |
| `IconPoint` | icon | b | 一个概念配一个图标 | `icon`, `iconAt`, `lines[]`, `ats[]`, `accent?[]` |
| `IconList` | icon | b | 2–3 条，每条配图标 | `kicker?`, `items[{icon, text, at}]`, `accent?[]` |

Park 说的样式名对不上组件时，查 `pv2.py catalog`：每个组件有中文名、他可能的叫法（keywords）和形态来源的 ShotCraft 卡；图鉴演示片段在 `gallery/`（改了组件或加了组件后跑 `pv2.py gallery` 重渲）。

图标用 lucide 的短横线名字（`users`、`clock`、`wallet`、`trending-up`…，全表见 https://lucide.dev/icons ），check 会核对图标存在。图表里的数值（`value`）必须是他说出口的数，不要编比例。真实图片暂不在这个流程里。

卡片外观（毛玻璃 / 纸卡 / 深色 / 无卡片、强调色、能不能冲过头）由 brief 决定，组件里用 `useLook()` 取颜色和弹出曲线，不要写死颜色。毛玻璃的模糊在合成时由 `render.py` 用原画面做。

需要新样式：从 Video-ShotCraft（主库，Park 的私有快照 `~/work/video-shotcraft-snapshot`，`pv2.py shotcraft` 列全部卡）挑卡，照它的 demo 源码改编成区域原生组件（用 `Card` / `useU` / `useSec` / `useLook`，停住后不再动），注册进 `motion/src/library/index.ts`，并在 `catalog.json` 登记努力程度和形式（ShotCraft 级的多层镜头是 `c`，先用 Codex 画图再做动画的是 `d`；这两档的组件还没有）。
