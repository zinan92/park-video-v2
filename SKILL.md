---
name: park-video-v2
description: Park 的口播视频全流程：标 Hook、切 Hook、给口播加动效（Remotion 透明层叠到原画面）、出样片和成片。Park 说「剪 Hook」「切 Hook」「给这条视频加动效」「做动效样片」「用新流程跑这条」「口播 workflow」时使用。AI 只做判断和写方案，切片、渲染、合成、检查都交给 scripts/pv2.py。10/21 起旧的 ask-park-video（14 步）和 videocut 已归档，全部用这一个。
---

# 口播 v2：操作说明（给执行的 AI）

**你只做判断：问清 brief、帮 Park 标 Hook、写 plan.json。** 切片、渲染、合成、检查全部用 `scripts/pv2.py`，不要自己写渲染脚本、不要手动调 ffmpeg / remotion。

## 全流程：12 个环节，3 次等 Park 确认

剪辑本身（删口误、停顿、调顺序）Park 在剪映里做完，导出**粗剪 + SRT** 放进项目文件夹，这个流程从这里开始。不剪 Hook 就跳过 2–3；不加动效就跳过 4–11。

| # | 环节 | 命令 / 谁 | 产物 |
|---|---|---|---|
| **剪 Hook** ||||
| 1 | 放进来：粗剪视频 + 剪映 SRT | Park | 项目根目录的视频、`subtitles/source.srt`（或根目录的 .srt） |
| 2 | 标 Hook：出表，Park 在表里标开头用哪几句（顺手写视觉想法）→ **等 Park ①** | `pv2.py worktable <项目>` | `analysis/worktable.html` → Park 存回 `analysis/worktable.json` |
| 3 | 切 Hook：原话对到词级时间，切点挪到停顿，切出的声音再听首尾字 | `pv2.py hook <项目>` | `part-a-hook/individual/h1.mp4…hN.mp4`、`edit.json`、`qa.json`（Park 拖进剪映拼到开头） |
| **加动效** ||||
| 4 | brief：建 v2/，问清这条的版式、哪些时间段不加、字幕是否烧录、不能出现的词；有工作台的渲染包就一起放进来 | `pv2.py init <项目> --video 粗剪 [--pack 渲染包]`（SRT 自己找，找不到问用户，确实没有 `pv2.py transcribe`） | `v2/brief.yaml`、`v2/pack-beats.json` |
| 5 | 对齐：SRT 对齐音频，拿到每个字的时间 | `pv2.py prep <项目>` | `v2/words.json` |
| 6 | 写方案：逐个时刻判断这句要观众明白什么、用什么画面；**不需要画面就不放**（保留真人也是决定） | AI | `v2/plan.json` |
| 7 | **ShotCraft 直通**：方案要的画面，直接用 ShotCraft 原卡（`"component": "ShotCraft"`，见「ShotCraft 直通」）；原仓库更新了先 `pv2.py shotcraft-sync` + `shotcraft-measure` | AI | `motion/src/shotcraft/manifest.json` |
| 8 | 检查：程序查方案（时机、遮挡、密度、禁用词、字号…）；精品档每个重点镜头和标杆左右对比 | `pv2.py check` / `pv2.py compare` | `check` 输出 `[]`、`v2/compare/` |
| 8½ | 有渲染包 / motion-picks 时：没照方案做的每一镜 + 原因列给 Park → **他看过才出样片** | `pv2.py deviations <项目>`，认可后 `approve <项目> deviations -m "原话"` | `v2/deviations.json` |
| 9 | 样片 → **等 Park ②** | `pv2.py sample <项目> --detach`，认可后 `approve <项目> sample -m "原话"` | `v2/sample.mp4` |
| 10 | 整条：层 → 合成 → 终检 | `pv2.py render <项目> --detach` | `v2/final.mp4`、`qa.json`、`contact.jpg` |
| 11 | 成片 → **等 Park ③** | `pv2.py approve <项目> final -m "原话"` | 批准记录 |
| **交付** ||||
| 12 | 封面、标题、发布 | 内容工作台（封面风格参考在 `assets/covers/`）；背景音乐、音效 Park 在剪映加 | 封面、各平台文案 |

ShotCraft 只在第 7 环节进来，而且只借它的镜头配方和源码；它自己那套整片导演流程不启动，第 8 环节起又回到 pv2。

Park 问进度时跑 `status`，报 `step` / `percent` / `waiting_for`，不要估。

## 剪 Hook（环节 2–3）

- 表里的时间是字幕插值出来的**近似值**，只用来定位；切片一律用 `pv2.py hook` 重新对到词级时间，不要拿近似时间直接切。
- 同一句话前面可能说过：`hook` 只在 Park 标的大概位置前后 6 秒里找。
- 剪映烧录的字幕切不掉：开头落在一条字幕中间、带着上一句的字，`qa.json` 会记一条，告诉 Park 听一下。
- `pv2.py hook <项目> --check` 只数表里标了几个 Hook，不切。粗剪没有烧录字幕时加 `--no-burned-captions`。

## 加动效（环节 4–11）

1. **brief（Park 说，你不猜）**
   `python3 scripts/pv2.py init <项目> --video <粗剪> [--pack <渲染包文件夹>]`，然后把 Park 的原话填进 `<项目>/v2/brief.yaml`。
   - **字幕**：不给 `--srt` 时，`init` 在视频旁边找（同名 .srt → 旁边唯一一个 .srt → `subtitles/source.srt`），找到会打印路径。**没找到就问用户有没有剪映导出的 SRT**，有就 `init --srt`；确实没有，跑 `python3 scripts/pv2.py transcribe <项目>`，在本机转写一份 `v2/source.srt`（要 mlx-whisper），后面照常 prep。
   - **烧字幕**：先问画面里有没有字幕（`captions_burned_in`）。没有、用户又要字幕，brief 写 `burn_captions: true`：样片和成片都会把 SRT 按 Park 的字幕样式烧进去（苹方、浅色字、深色半透明底板、底部居中，`scripts/captions.py`），字幕带自动算出来，动效会避开。转写出来的字幕先对照 `pack-script.md` / 稿子改错别字（只改识别错的字，不改他说的话），用户在样片里一起看。两个都是 true 会报错（字幕不能烧两遍）。
   - **4K 原片**：`canvas` 照旧写 `[1920, 1080]`，`face_box` / `caption_band` 在缩到 1920 宽的截图上量。`prep` 会读原片分辨率：同比例更大（4K）就合成时整体放大（动效层用 Remotion `--scale` 渲，字不糊），成片保住原分辨率，**不要先转 1080p 工作副本**；比例不同会直接报错，照提示改 canvas。
   每条视频只问 Park 这几项：视频类型、动效怎么放（`overlay-sides` 人脸居中两侧透明叠加 / `broll` / `fullscreen`）、哪些时间段不加动效、字幕是否已烧进画面、**不能出现在画面上的词**（客户名、地名…，写进项目的 `banned_words`，绝不写进本仓库）。
   人脸位置 `face_box` 和字幕带 `caption_band`：从粗剪的真实画面截两帧量，不要猜。
   风格和规则（**密度**、**努力程度**、卡片底色、强调色、能不能改写原话……）全部列在 `settings.yaml`，默认值在 `defaults.yaml`（Park 在工作台设的默认值在 `~/.config/park-video-v2/defaults.yaml`，优先），**不要再问**。他说这条要不一样，用 `pv2.py set <项目> --json '{...}'` 改（会先校验、还没做的档位会被拒），不要手改 yaml。`pv2.py settings <项目>` 看当前取值和来源。音效、背景音乐不在这个流程里（Park 在剪映加）。
2. **prep**：`python3 scripts/pv2.py prep <项目>` → `v2/words.json`（SRT 对齐音频，约 30 秒）。
3. **写 plan.json**（见下）→ `python3 scripts/pv2.py check <项目>`，输出 `[]` 才算过。
4. **偏离清单**（有渲染包或 `v2/motion-picks.json` 时，见下「有渲染包时」）：`pv2.py deviations <项目>` 没问题才往下走。
5. **样片**（精品档先 `compare`，见下）：`python3 scripts/pv2.py sample <项目> --detach`，用 `status` 看进度。完成后**停下**，把 `v2/sample.mp4` 发给 Park。
6. Park 认可后：`python3 scripts/pv2.py approve <项目> sample -m "<Park 原话>"`。
7. **整条**：`python3 scripts/pv2.py render <项目> --detach`（层 → 合成 → 终检，`status` 里有真实百分比）。完成后把 `v2/final.mp4`、`v2/contact.jpg` 给 Park。
8. Park 确认：`python3 scripts/pv2.py approve <项目> final -m "<Park 原话>"`。

## 有渲染包时：渲染包就是方案，不是参考

渲染包是用户在选题工作台看过、挑过的镜头表（每镜 `line` 原句 / `motion` ShotCraft 卡 / `why` / `preview`）。`init --pack` 把它放进 `v2/pack-beats.json`，`settings.json` 里的密度、努力合进 brief（`density: mid` 按 `medium` 读）。`v2/motion-picks.json` 同样对待。

1. **每一镜都照它的 `motion` 做。** 先按意思把 `line` 落到录音时刻：`pv2.py find <项目> "原句"`；找不到时它会给 `near`（意思最接近的几处和他实际说的话）。在 plan.json 里给这个镜头标 `"beat": <n>`。
2. **卡上的字以录音（SRT / words.json）为准，不抄渲染包的 `line`。** 稿子写「十分好用」、他录的是「非常好用」，卡上就是「非常好用」，照样只删不换（`rewrite: trim-only`）。
3. **组件库里没有这张卡的组件（`pv2.py catalog` 里没有哪个组件的 `shotcraft` 写着它），就走第 7 环节去 ShotCraft 改编**，登记进 catalog 时把这张卡名写进 `shotcraft`。不准拿「效果最接近」的现成组件顶替。
4. **努力档位按改编后的实际做工定，不按 ShotCraft 原档。** 花括号拉开这类文字动效，改编成区域组件后是 b 档就登记 b。渲染包的 motion 和 brief 的 effort 还是冲突（改编后确实超出这一档），**先问 Park**，不准自己降级替换。
5. **做不了的（改编不出来、和 brief 的规矩冲突），出样片之前列给 Park**：写进 `v2/deviations.json`：
   ```json
   [{"beat": 2, "motion": "brace-expand", "instead": "IconList", "why": "为什么做不了 / 为什么这样换"}]
   ```
   全照做了就写 `[]`。跑 `pv2.py deviations <项目>`：没照方案做、又不在清单里的镜头会被点名。把清单发给 Park，他认可后 `pv2.py approve <项目> deviations -m "<原话>"`。**`sample` 会拒绝**：有渲染包却没有清单、清单漏了镜头、清单没批或批过又改了。
6. **镜头放几张由 pv2 定，不由渲染包定。** 工作台不限镜头数（10/29 Park：前端只是 wrapper，不加限制），渲染包从稿子开头到结尾每个论点都可能有一镜，常常比密度要的多。按 brief 的密度（`check` 的 density：动效占可加动效时长的比例）挑：留意思最重、最需要画面的那几镜，其余不放，每个没放的都写进偏离清单（`{"beat": 9, "why": "密度中，这一段已经有 V07"}`）。不够就自己补（见下一条）。
7. **渲染包不一定覆盖整条，pv2 拿原片自己对。** `init` 记下原片时长；`deviations` 把每一镜落到录音里，报出方案覆盖到第几秒（`pack_until`），以及说着话却连续很久一张卡都没有的时间段（`empty`：密度 low 60 秒 / medium 30 秒 / high 20 秒）。方案没写到的段落照平常的规矩自己排镜头（不标 `beat`），每个都写进偏离清单（`{"shot": "V11", "why": "渲染包没写到这一段"}`），Park 才知道哪些是你排的。`plan.json` 的 `duration` 必须是原片时长。有空段、或自己排的镜头没进清单，`sample` 都会拒绝。
8. 密度、字数、交替、no_motion 这些规矩照样要过 check；方案和规矩冲突时同样写进偏离清单问 Park，不在最后汇报里顺带一句。

## 精品档（effort c / d）的流程：先意思、功夫集中在 2–3 个重点时刻、每张都过标杆

Park 的判断：组件做得再细，表达错了就是 10–20 分；16 张卡平均用力，每张都只有 50 分。所以精品档按这个顺序做，不能跳：

1. **逐个时刻写意思和画面**：每张候选卡先写 `intent.means`（这句话要观众明白什么，用他的原意，不用关键词）和 `intent.picture`（用什么画面讲出来）。时刻按「意思能不能画出来」挑，不按关键词挑。旧流程项目里 visual-plan 的 `design.relation` 是很好的底子。
2. **挑 2–3 个重点时刻，功夫集中花在这里**：标 `"key": true`。先考虑开头，但开头的内容撑不起画面（比如只是几个数字）就不硬选。重点时刻用「画面比喻」组件（抓重点、积累成结论、两个条件、断裂、生意链路……），或照意思新写一个（写成通用组件，放进库）。**做工照标杆一个元素一个元素地对**：标杆里的小卡是圆角方块 + 灰条 + 状态点，你就不能拿一个圆点糊弄；先读标杆的源码或逐帧看，列出它每个元素长什么样、怎么错开出现、哪句话触发哪个变化，再照着做到不低于它。其余的卡用 b 档图表、图标，甚至不放，不算偷懒（check 只要求重点时刻是 c 档以上）。
3. **每个重点时刻指一条标杆**：标杆库在本机 `~/.config/park-video-v2/benchmarks.yaml`（Park 认可过的成片片段，客户画面，**不进本仓库**），每条有 `shows`（它讲的是什么关系）。按意思挑最接近的一条写进 `"benchmark": "<名字>"`。库里没有接近的，就拿 Park 最近认可过的成片里同类的一段补进库。
4. **和标杆左右对比，不低于标杆才往下走**：`python3 scripts/pv2.py compare <项目>`，每个重点镜头出一段左右对比视频和一张两行逐帧图（`v2/compare/`）。自己逐帧看：每个元素的做工、出现的层次、跟着哪句话变，有一项比标杆差就回去改。版面和底色的差别（区域窄、毛玻璃）不算，做工差才算。重点镜头没对比过、或对比后又改过，`sample` 会拒绝。
5. **整条不重复**：同一个组件、同一种画面比喻整条只用一次（check 拦 `repeated-component`）。两个时刻的意思像（都是「筛选」），只留一个。
6. **自己先核对意思**：出样片前逐张问「这张卡有没有讲出 intent.means」。讲不出的重做或删，不拿去给 Park 看。他不看文字规格表，只看画面。
7. **样片就是重点时刻**：`pv2 sample` 只渲 `key` 的镜头（拼成一段）。发给 Park 时把 `v2/compare.mp4` 一起发。
8. **看动作不看截图**：用连续帧（从出现到停住均匀取帧）检查，不只看停住后的样子。

## 写 plan.json 的原则

先读 brief（含 defaults.yaml 合并后的值），照着规则写，**一次写对，不要靠 check 报错再改**。check 会拦下所有违反下面规则的镜头。

- **有 `v2/motion-picks.json` 或渲染包（`v2/pack-beats.json`）就照它做**，规则见上面「有渲染包时」：每句原话（`line`）配哪张 ShotCraft 卡（`shotcraft` / `motion`）、引擎里现成的组件（`component`，空 = 还没接进引擎）、为什么（`why`）。有 `component` 直接用，没有就照那张卡改编；做不了的写进偏离清单，Park 看过才出样片。
- **只用他说出口的话和数字。** 每段文字的出现时刻 = 他说出这句话的时刻：`python3 scripts/pv2.py find <项目> "原话"` 查。
- `rewrite: trim-only`：卡上每一段字（含 kicker、标题）都只能从原话里删字得到，不能换词、不能加词。「非常重要」不能写成「最重要」。
- `banned_words`：一个都不能出现在卡上。
- `max_items`：lines / items / notes 每样不超过这么多条。`text_amount: one-point`：一张卡一个重点，卡上字加起来不超过 24 个。
- **一行要短**：带字的组件每行都不折行、按区域宽度缩字号，主要文字低于 56px（1080p；canvas 写 4K 时是 112px）会被拦下（`text-too-small`，TextLines、Quote、ListSteps、IconPoint、IconList、Flow、Bars、Cycle、Funnel、Compare 都查；c 档组件看 `min_zone_w` 和 `limits`）。区域宽度由 face_box 推出，下面是一行最多几个汉字（数字、英文约 0.6 个字）：

  | 区域宽 | TextLines / Quote / IconPoint | IconList | Flow | Compare | ListSteps | Bars 标签 | Funnel（自上而下） | Cycle 节点 |
  |---|---|---|---|---|---|---|---|---|
  | 440px | 只有 TextLines 第一行 ≤5 字，第 2 行起放不下 | 放不下 | 放不下 | 放不下 | 放不下 | 放不下 | 放不下 | 放不下 |
  | 560px | 7（Quote / IconPoint 第 2 行起放不下） | 5 | 6 | 6 | 放不下 | 放不下 | 放不下 | 放不下 |
  | 620px | 8 | 6 | 7 | 7 | 7 | 8 | 6 / 5 / 4 | 3 |
  | 760px | 10 | 8 | 9 | 9 | 8 | 10 | 7 / 6 / 5 | 4 |

  窄的一侧（440px 这种）只放一个短词的 TextLines、数字卡或截图，内容多的卡放宽的一侧；长句拆成两三行。kicker、注释、来源这些小字是固定小号，不查。
- **两把主旋钮**：
  - `density` 管**多少**：动效时长占可加动效时长（去掉 no_motion）的比例，这是唯一的标准（10/29 定）。张数从它换算，一张卡平均停 5 秒（`brief.cards_for`）：

    | 密度 | 动效占比 | 每分钟 | 3 分半的视频 |
    |---|---|---|---|
    | low 低 | 10–20% | 1–2 张 | 5–8 张 |
    | medium 中 | 30–40% | 4–5 张 | 13–16 张 |
    | high 高 | 50–60% | 6–7 张 | 21–25 张 |

    brief 里写 `coverage: [下限, 上限]` 可以直接指定。check 不在区间就拦。按内容挑够卡、每张停够时间来凑比例，不要塞空卡。
  - `effort` 管**多精**：a 文字卡 / b 图表、示意图、图标 / c 层次丰富、像专业 AE / d 先用 Codex 画图再做动画。组件的努力程度见 `motion/src/library/catalog.json`，不能超过 brief 的档；低于这一档的卡最多占 40%（精品档例外：只要求重点时刻是 c 档以上）。
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

## 运镜（`"kind": "camera"`）：直接推原画面

ShotCraft 的 tension-camera-moves（情绪运镜）里，口播能用的是 C 式**慢推**（slow-push-in）：画面越推越快地推近人脸，四周暗角跟着加深，推到头硬切回原样——那一下是「蓄力→释放」，用在大数字、宣言、反转的前一刻。它不叠卡片，合成时直接推原画面（`render.py` 的 `camera_chain`，ffmpeg 逐帧放大 + 暗角），4K 原片照样按原分辨率推。

```json
{"id": "C08", "kind": "camera", "move": "slow-push", "start": 61.2, "end": 65.2, "from": 1.0, "to": 1.14, "vignette": 0.5, "beat": 8}
```

- `start` / `end`：推的时间段，2.5–6 秒（ShotCraft 是 4 秒）；`end` 落在要释放的那句话前。
- `to`：推到多少，1.04–1.2（ShotCraft 定的 1.14；超过 1.2 就成了普通推镜头）。`vignette`：暗角强度 0–1，默认 0.5。
- 推向人脸中心（brief 的 `face_box`）。
- check 会拦：不认识的运镜（camera-unknown）、时长不对（camera-length）、推太多（camera-amount）、整条用了第二次（camera-repeat）、推的时候画面上还有卡片（camera-with-card：人脸一放大就顶到卡片）。
- 运镜也算动效时长（密度）；渲染包里写 tension-camera-moves / slow-push-in 的那一镜标 `beat`，就算照做了。
- 其余三式（冻结环绕、斜角滚正、拉远孤立）是给图表、整页界面用的，口播画面上不做；渲染包推荐了就写进偏离清单。

## ShotCraft 直通：不改源码，把原卡叠在人脸两侧（SOP）

ShotCraft（github.com/Vincentwei1021/video-shotcraft）是调校过很多轮的镜头库。**不再一张张重做**：原卡原样渲染，pv2 统一做三件事——去底、换字、裁出内容放进人脸旁边。

**ShotCraft 更新时（谁都能跑，不用 Park）：**
1. `python3 scripts/pv2.py shotcraft-sync`：拉原仓库最新到本机缓存（`~/.cache/park-video-v2/video-shotcraft`），生成注册表，报告新增和下架的卡。
2. `python3 scripts/pv2.py shotcraft-measure [卡 ...]`：每张卡在透明画布上渲几帧，自动量出：内容占画面哪一块、去底以后还剩不剩东西、能不能缩进侧边（`auto`：side 侧边 / full 只能全屏 / skip 用不了）、卡上有哪几段字可以换（`slots`）。写进 `motion/src/shotcraft/manifest.json`（进库）。
3. Park 看图鉴片段，在 manifest 的 `verdict` 里改成 side / full / skip（不改就按 `auto`）。

**原卡是怎么变成侧边动效的（`motion/src/shotcraft/`，原卡源码一行不改）：**
- 去底：原卡共用的舞台件（Look 的 Stage、Polish 的 Backdrop / Grain / Vignette、Motion 的 DesignStage）换成透明版；渲染时再把铺满整个画面的元素的底色去掉。
- 去品牌：video-shotcraft 的标志、字标不画；宣传语默认换成空。
- 换字：原卡里每段字都过一遍对照表（`slot-loader.cjs`），方案给了就换成他的原话。
- 放置：原卡在 1920×1080 上渲，渲完按实际内容裁出那一块，等比放进左 / 右区域；字是浅的垫深色卡片底，字是深的垫浅色卡片底（brief 的 `card: none` 不垫）。
- 时间：从他说出这句话（`at`）开始播，播完停在最后一帧。

**方案里这样写：**
```json
{"id": "V03", "start": 21.0, "end": 27.0, "zone": "left", "component": "ShotCraft", "hold": 24.0,
 "props": {"card": "marker-underline-title", "at": 21.4, "texts": {"Meet the": "先说", "new": "结论", "video-shotcraft": "再讲原因"}},
 "reveals": [{"at": 21.4, "text": "先说结论"}]}
```
- `card` 是 manifest 里的样式名（`pv2.py shotcraft` 里每张卡的 `pass` 列出它的样式和能怎么用）。
- `texts`：卡上**每一段**原文（manifest 的 `slots`）都要换成他的原话，不要的写空字符串；video-shotcraft 这类品牌字（字标往往就是标题）也可以拿来当标题槽。换上去的字不能比原文长太多（原卡版式是定死的）。
- check 会拦：清单里没有（shotcraft-unknown）、用不了（shotcraft-skip）、只能全屏却放侧边（shotcraft-full-only）、字没换完（shotcraft-text-left）、换的字太长（shotcraft-text-long）、卡上没有这段字（shotcraft-slot）。
- **全屏镜头（`zone: full`，盖住人脸）一共不超过可加动效时长的 10%**（too-much-fullscreen），人脸要大部分时间在画面上。
- 直通卡算 b 档、形式按原卡分类；字号、原话删减、禁用词这些规矩照样查。

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

从 ShotCraft 文字类卡改编的组件（effort b，都是 text 形式；渲染包推荐这些卡时直接用，`shotcraft` 字段写着原卡名）：

| 组件 | 原卡 | 用在 | props | 限制 |
|---|---|---|---|---|
| `BraceExpand` | brace-expand | 一个词 / 短句：花括号撑开，字从中间露出来 | `kicker?`, `kickerAt?`, `text`, `at` | text ≤6 字，区域 ≥560px |
| `CelFlashStomp` | cel-flash-stomp | 三四个词一拍一个砸下来，底色闪（高能开场、口号；靠音效撑，一条最多一次） | `words[{text, at}]` | 每词 ≤6 字，区域 ≥520px |
| `WeightPump` | type-rhythm-sync（font-weight-pump） | 他加重语气那一刻，那行字笔画变粗再弹回（一条最多一次；两次脉冲隔 ≥0.7s） | `kicker?`, `lines[]`, `ats[]`, `pumps?[{at, line}]`, `accent?[]` | 区域 ≥500px |
| `SpotlightSweep` | spotlight-sweep-moves | 一道光从左往右匀速扫过，字被点亮（揭晓一句话） | `kicker?`, `lines[]`, `ats[]`, `accent?[]` | 区域 ≥500px |
| `DrawTrace` | draw-svg-trace | 笔沿卡片边画一圈再出字，重点那行补下划线（字比画慢一拍，镜头可以早于他说出口 1s 开始） | `kicker?`, `lines[]`, `ats[]`, `accent?[]`, `drawAt?` | 下划线一张卡最多一条，区域 ≥500px |

这五个都是文字形式：相邻两张不能同形式，渲染包里连着几镜都是文字卡时，中间换一种形式或留纯人脸，写进偏离清单。

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

手工改编（只用在最常用、要精修的卡上，平时走上面的直通）：从 Video-ShotCraft 挑卡，照它的 demo 源码改编成区域原生组件（用 `Card` / `useU` / `useSec` / `useLook`，停住后不再动），注册进 `motion/src/library/index.ts`，并在 `catalog.json` 登记努力程度、形式和 `shotcraft`（从哪张卡改编的）。努力程度按改编后的实际做工定，不照搬 ShotCraft 原档：文字类、单层动作的是 `b`，多层质感、像专业 AE 的是 `c`，先用 Codex 画图再做动画的是 `d`（`d` 的组件还没有）。新的 c 组件：所有光晕、阴影收在卡片里，动作在 settle 内做完后一帧不动（`tests/test_layers.py` 的 still_after 测试会实测）。
