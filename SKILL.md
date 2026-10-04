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

## 精品档（effort c / d）的流程：先意思、再画面、关键时刻专门做

Park 的判断：组件做得再细，表达错了就是 10–20 分。所以精品档按这个顺序做，不能跳：

1. **逐个时刻写意思和画面**：每张候选卡先写 `intent.means`（这句话要观众明白什么，用他的原意，不用关键词）和 `intent.picture`（用什么画面讲出来）。时刻按「意思能不能画出来」挑，不按关键词挑。旧流程项目里 visual-plan 的 `design.relation` 是很好的底子。
2. **关键时刻用比喻组件或新做**：一条挑 5–6 个最有画面感的时刻，用「画面比喻」组件（抓重点、积累成结论、两个条件、断裂、生意链路、少数派、时间换算……），库里没有合适的就照意思新写一个（写成通用组件，放进库）。普通时刻才用现成的卡片组件。
3. **整条不重复**：同一个组件、同一种画面比喻整条只用一次（check 拦 `repeated-component`）。两个时刻的意思像（都是「筛选」），只留一个。
4. **自己先核对意思**：出样片前逐张问「这张卡有没有讲出 intent.means」。讲不出的重做或删，不拿去给 Park 看。他不看文字规格表，只看画面。
5. **样片挑最难的**：在最难、最能代表这一版水平的 2–3 张卡上标 `"sample": true`，`pv2 sample` 只渲它们（拼成一段）。
6. **看动作不看截图**：用连续帧（从出现到停住均匀取帧）检查，不只看停住后的样子。

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
| `Proof` | image | a | 证据截图：他点过「要」的新闻、数据、原推、后台截图 | `src`, `at`, `source`, `sourceAt?` |
| `HaloNumber` | number | c | 关键数字：滚动锁定 + 光晕 + 下划线 + 高光扫过 | `value`, `unit?`, `at`, `caption?`, `captionAt?` |
| `HatchBars` | chart | c | 2–3 个数量对比：斜纹草稿擦出再蜕变实色 | `kicker?`, `bars[{label, value, display?, at}]`, `accent?[]` |
| `GlassCycle` | diagram | c | 飞轮：玻璃球托起、弧线箭头走一圈、整组推近 | `nodes[{text, at}]`, `center?`, `centerAt?`, `accent?[]` |
| `RingCore` | diagram | c | 一个核心概念向心收拢 + 1–3 条注释 | `core`, `coreAt`, `notes?[{text, at}]` |
| `StackPress` | text | c | 2–3 条要点一张张压进来 | `kicker?`, `items[]`, `ats[]` |
| `QuoteMarker` | text | c | 一句原话，关键行马克笔涂一下 | `lines[]`, `ats[]`, `accent?[]` |
| `IconBloom` | icon | c | 概念配图标：玻璃圆盘擦出 + 三圈涟漪 | `icon`, `iconAt`, `lines[]`, `ats[]`, `accent?[]` |

画面比喻组件（effort c，精品档的关键时刻用，都可以加 `arc: "hero"` / `"light"` 选进场方式）：

| 组件 | 形式 | 意思 | props |
|---|---|---|---|
| `PickOne` | diagram | 一堆并列的东西里只有一个是关键 | `stages[{count, label, at}]`, `focus{text, at}`, `spread?{at}`, `pick?` |
| `Accumulate` | diagram | 越来越多、每份都具体，所以结论成立 | `counts[{text, at, sheets}]`, `unit?`, `details[{text, at}]`, `verdict{text, at}` |
| `Quadrant` | chart | 两个条件都满足才成立 | `x{text, at}`, `y{text, at}`, `both{at}`, `result{text, at}` |
| `BrokenPath` | diagram | 过去走通的路延伸不到未来 | `from{text, at}`, `to{text, at}`, `breakAt?` |
| `Journey` | diagram | 一条有先后的链路走到结果 | `title?{text, at}`, `stops[{text, at}]`, `result?{text, at}` |
| `CrowdSplit` | chart | 大多数在一边，我在另一边 | `total?`, `crowd{text, at}`, `minority{text, at}` |
| `TimeCompress` | number | 小投入换大回报（几小时 ≈ 一个月） | `small?{text, at}`, `clock{text, at, hours}`, `month{text, at, days?}` |

effort c 的组件动作多：`catalog.json` 里写了 `settle`（最后一次出现后几秒做完）、`min_zone_w`（最窄区域）、`limits`（每段字最多几个字），check 会拦。`hold` 写成「最后一次出现 + settle」之后；`effort: c` 时至少 60% 的卡要用 c 组件，其余可以用 a / b。

Park 说的样式名对不上组件时，查 `pv2.py catalog`：每个组件有中文名、他可能的叫法（keywords）和形态来源的 ShotCraft 卡；图鉴演示片段在 `gallery/`（改了组件或加了组件后跑 `pv2.py gallery` 重渲）。

图标用 lucide 的短横线名字（`users`、`clock`、`wallet`、`trending-up`…，全表见 https://lucide.dev/icons ），check 会核对图标存在。图表里的数值（`value`）必须是他说出口的数，不要编比例。

## 证据截图（`Proof`）

真截图只从 `v2/evidence.json` 来：内容工作台骨架页里按论点找的新闻、数据、原推，和他自己传的后台截图，**都是他点过「要」的**（工作台用 `pv2.py evidence <项目> <清单.json>` 放进来，brief 的 `evidence` 随之是 own / search）。不要自己找图、画图、编来源。

- 每条清单项有 `point` / `point_title`（骨架里哪个论点）、`caption`、`claim`（它证明哪句话）。用 `pv2.py find` 找他讲到这个论点的时刻，截图卡放在那里；他没讲到的就不放，方案写完在回报里说哪几张没放、为什么。
- `props.src` 写清单里的 `file`，`props.source` 一字不差写清单里的 `line`（「来源：… · 日期」）；`at` 不早于他说出这个论点。
- 至少停 4 秒（看图 + 看来源）；放在 left / right，不挡脸、不进字幕带（和别的卡一样）。截图卡不算「偷懒」的低档卡，但相邻两张仍要换形式，两张截图之间插一张别的或留纯人脸。
- check 会拦：清单外的图（proof-unknown）、来源不对（proof-source）、停太短（proof-too-short）、这条视频设了不放证据（proof-off）。

卡片外观（毛玻璃 / 纸卡 / 深色 / 无卡片、强调色、能不能冲过头）由 brief 决定，组件里用 `useLook()` 取颜色和弹出曲线，不要写死颜色。毛玻璃的模糊在合成时由 `render.py` 用原画面做。

需要新样式：从 Video-ShotCraft（主库，Park 的私有快照 `~/work/video-shotcraft-snapshot`，`pv2.py shotcraft` 列全部卡）挑卡，照它的 demo 源码改编成区域原生组件（用 `Card` / `useU` / `useSec` / `useLook`，停住后不再动），注册进 `motion/src/library/index.ts`，并在 `catalog.json` 登记努力程度和形式（ShotCraft 级的多层质感是 `c`，先用 Codex 画图再做动画的是 `d`，`d` 的组件还没有）。新的 c 组件：所有光晕、阴影收在卡片里，动作在 settle 内做完后一帧不动（`tests/test_layers.py` 的 still_after 测试会实测）。
