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
   风格和规则（卡片底色、强调色、动效力度、能不能改写原话、疏密……）在仓库根目录 `defaults.yaml`，是 Park 填好的默认值，**不要再问**；他说这条要不一样，才在项目 brief.yaml 里写同名字段覆盖。音效、背景音乐不在这个流程里（Park 在剪映加）。
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
- `intensity`：组件力度见 `motion/src/library/levels.json`，不能超过 brief 的力度。`restrained` 时只能用 TextLines，且一张卡上的字要在 1.5 秒内全部出来（整张卡一起出，不逐条出）。
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

| 组件 | 力度 | 用在 | props |
|---|---|---|---|
| `TextLines` | restrained | 一个重点（大字），或要点逐行出现 | `kicker?`, `lines[]`, `ats[]`, `accent?[]`（用强调色的行号） |
| `NumberRoll` | medium | 一个关键数字 | `value`, `unit?`, `lockAt`, `notes?[{text, at}]` |
| `ListSteps` | medium | 先后步骤 | `kicker?`, `items[]`, `ats[]` |
| `Compare` | medium | 两件事对照（≠ / → / +） | `kicker?`, `top{title, sub?, at}`, `bottom{…}`, `symbol`, `symbolAt` |
| `Gauge` | medium | 一个比例 | `kicker?`, `value`(0–100), `at`, `label?` |

卡片外观（毛玻璃 / 纸卡 / 深色 / 无卡片、强调色、能不能冲过头）由 brief 决定，组件里用 `useLook()` 取颜色和弹出曲线，不要写死颜色。毛玻璃的模糊在合成时由 `render.py` 用原画面做。

需要新样式：从 Video-ShotCraft（`~/.agents/skills/video-shotcraft`，主库）挑卡，照它的 demo 源码改编成区域原生组件（用 `Card` / `useU` / `useSec` / `useLook`，停住后不再动），注册进 `motion/src/library/index.ts`，并在 `levels.json` 登记力度（ShotCraft 的复杂运镜是 `rich`）。
