"""方案的程序检查：几秒内跑完，不靠 AI 评审。

用法：python3 scripts/check.py <plan.json> <words.json> <brief.yaml>
没有问题时输出 []、退出码 0；有问题时逐条列出、退出码 1。

plan.json 里每个镜头：{id, start, end, zone, component, reveals: [{at, text}], hold}
- zone：left / right / full，或者 {x, y, w, h}
- reveals：每段文字出现的时刻和它显示的原话，用来查「文字不早于说出口」
- hold：从这一刻起画面不再动（渲染后由 qa.py 实测）

风格和规则来自 defaults.yaml（brief.yaml 可覆盖）：密度（动效占比区间）、努力程度（能用哪些组件、
不能大部分偷懒）、不能出现的词、每张卡最多几条、一张卡一个重点、能不能改写原话、什么时候走、
两张卡之间留多少秒纯人脸、相邻两张形式不同。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import bench as bench_mod
import brief as brief_mod
import proof as proof_mod

FRAME = 1 / 30
SEARCH = 5.0  # 在镜头前后多少秒内找原话
ONE_POINT_CHARS = 24  # text_amount: one-point 时一张卡上所有字加起来最多几个
EXIT_GRACE = 1.5  # exit: after-sentence 时最后一个字说完后最多再停几秒
MIN_SHOT = 2.5  # 一张卡至少停几秒，太短来不及看
UNTIL_NEXT_MAX = 10.0  # exit: until-next 时最后一个字说完后最多再停几秒（不让一张卡挂太久）
LOW_EFFORT_SHARE = 0.4  # 低于这条视频努力程度的卡最多占多少（不能大部分都偷懒做成文字卡）
KEY_SHOTS = (2, 3)  # 精品档挑几个重点时刻：功夫集中花在这几张上，其余可以是 b 档
MOTION = Path(__file__).resolve().parents[1] / "motion"
CATALOG_FILE = MOTION / "src" / "library" / "catalog.json"
ICON_DIR = MOTION / "node_modules" / "lucide-react" / "dist" / "esm" / "icons"
EFFORT = {"a": 0, "b": 1, "c": 2, "d": 3}
LISTS = ("lines", "items", "notes", "nodes", "layers", "bars", "steps")
MIN_TEXT_PX = 56  # TextLines 每行不折行、按卡片宽度定字号；比这小就看不清，要拆行
SHADOW_MARGIN, PAD_X = 28, 42  # 和 motion/src/kit/Card.tsx 一致


def is_key(shot: dict[str, Any]) -> bool:
    """重点时刻（旧方案写的 sample 也算）：精品档功夫花在这几张上，样片只渲它们。"""
    return bool(shot.get("key") or shot.get("sample"))


def _clean(text: str) -> str:
    return re.sub(r"[^\w]", "", text)


def _stream(words: list[dict[str, Any]]) -> tuple[str, list[int]]:
    flat, owner = [], []
    for i, w in enumerate(words):
        for ch in _clean(w["w"]):
            flat.append(ch)
            owner.append(i)
    return "".join(flat), owner


def _spoken_span(words: list[dict[str, Any]], text: str, lo: float, hi: float) -> tuple[float, float] | None:
    """这句话在 [lo, hi] 附近第一次被说出的 (开始, 结束) 秒。"""
    target = _clean(text)
    if not target:
        return None
    stream, owner = _stream(words)
    at = stream.find(target)
    best = None
    while at >= 0:
        span = (words[owner[at]]["start"], words[owner[at + len(target) - 1]]["end"])
        if lo <= span[0] <= hi and (best is None or span[0] < best[0]):
            best = span
        at = stream.find(target, at + 1)
    return best


def _spoken_at(words: list[dict[str, Any]], text: str, lo: float, hi: float) -> float | None:
    """这句话在 [lo, hi] 附近第一次被说出的时刻（第一个字所在词的开始）。"""
    span = _spoken_span(words, text, lo, hi)
    return span[0] if span else None


def _trimmed_from_speech(words: list[dict[str, Any]], text: str, lo: float, hi: float) -> bool:
    """卡片上的字是不是原话删减出来的：按顺序都能在一小段原话里找到，没有换词、没有加词。"""
    target = _clean(text)
    if not target:
        return True
    nearby = [w for w in words if lo <= w["start"] <= hi]
    stream, _ = _stream(nearby)
    limit = 2 * len(target) + 4  # 删减出来的字不会散在太长一段话里
    for begin, ch in enumerate(stream):
        if ch != target[0]:
            continue
        k, end = 0, begin
        while end < len(stream) and k < len(target):
            if stream[end] == target[k]:
                k += 1
            end += 1
        if k == len(target) and end - begin <= limit:
            return True
    return False


def _texts(props: Any) -> list[str]:
    """props 里所有会显示在画面上的字（数字、时刻不算）。"""
    if isinstance(props, str):
        return [props]
    if isinstance(props, dict):
        return [t for k, v in props.items() if k not in ("at", "ats", "lockAt", "symbolAt", "accent", "icon", "symbol", "arc", "pick", "hours", "days", "sheets", "count", "src") for t in _texts(v)]
    if isinstance(props, list):
        return [t for v in props for t in _texts(v)]
    return []


TIME_KEYS = ("at", "ats", "lockAt", "symbolAt", "iconAt", "captionAt", "centerAt", "coreAt", "sourceAt")


def _times(props: Any) -> list[float]:
    """props 里所有出现时刻（秒）。"""
    if isinstance(props, dict):
        out = []
        for k, v in props.items():
            if k in TIME_KEYS:
                out += [float(x) for x in (v if isinstance(v, list) else [v]) if isinstance(x, (int, float)) and not isinstance(x, bool)]
            else:
                out += _times(v)
        return out
    if isinstance(props, list):
        return [t for v in props for t in _times(v)]
    return []


def _at_path(props: Any, path: str) -> list[str]:
    """props 里某条路径上的字，如 nodes.text → 每个节点的 text；items → 每条。"""
    head, _, rest = path.partition(".")
    v = props.get(head) if isinstance(props, dict) else None
    if v is None:
        return []
    vals = v if isinstance(v, list) else [v]
    if rest:
        return [t for x in vals for t in _at_path(x, rest)]
    return [x for x in vals if isinstance(x, str)]


def _catalog() -> dict[str, dict[str, str]]:
    return {k: v for k, v in json.loads(CATALOG_FILE.read_text(encoding="utf-8")).items() if not k.startswith("_")}


def _icons(props: Any) -> list[str]:
    if isinstance(props, dict):
        return [v for k, v in props.items() if k == "icon" and isinstance(v, str)] + [i for v in props.values() for i in _icons(v)]
    if isinstance(props, list):
        return [i for v in props for i in _icons(v)]
    return []


def _form(shot: dict[str, Any]) -> str | None:
    return _catalog().get(shot.get("component", ""), {}).get("form")


def _em_width(text: str) -> float:
    """一行字大约占几个字宽（和 Card.tsx 的 emWidth 一致）：汉字 1，数字和英文约 0.6。"""
    return sum((0.85 if ch in "%@MW" else 0.6) if ord(ch) < 256 else 1 for ch in text)


def line_px(text: str, zone_w: int, i: int) -> int:
    """TextLines 里这一行实际会用的字号（px）。"""
    k = (zone_w - 2 * SHADOW_MARGIN) / 600
    inner = zone_w - 2 * SHADOW_MARGIN - 2 * PAD_X * k
    return int(min((96 if i == 0 else 72) * k, inner // max(1.0, _em_width(text))))


def coverage(plan: dict[str, Any], b: dict[str, Any]) -> float:
    """动效时长占可加动效时长（去掉 no_motion）的比例。密度检查用它。"""
    usable = plan["duration"] - sum(z - a for a, z in b.get("no_motion") or [])
    return round(sum(s["end"] - s["start"] for s in plan.get("shots") or []) / usable, 3) if usable > 0 else 0.0


def _zone(shot: dict[str, Any], b: dict[str, Any]) -> dict[str, int]:
    z = shot["zone"]
    if isinstance(z, dict):
        return z
    if z == "full":
        w, h = b["canvas"]
        return {"x": 0, "y": 0, "w": w, "h": h}
    left, right = brief_mod.side_zones(b)
    return {"left": left, "right": right}[z]


def _overlap(a: dict[str, int], b: dict[str, int]) -> bool:
    return a["x"] < b["x"] + b["w"] and b["x"] < a["x"] + a["w"] and a["y"] < b["y"] + b["h"] and b["y"] < a["y"] + a["h"]


def run(plan: dict[str, Any], words: dict[str, Any], b: dict[str, Any], evidence: list[dict[str, Any]] | None = None) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    ws = words.get("words") or []

    def add(rule: str, shot: dict[str, Any], detail: str) -> None:
        out.append({"rule": rule, "shot": shot["id"], "detail": detail})

    shots = plan.get("shots") or []
    for s in shots:
        if s["start"] < 0 or s["end"] > plan["duration"]:
            add("outside-video", s, f"{s['start']}–{s['end']}s 超出视频 0–{plan['duration']}s")
        if s["end"] - s["start"] < MIN_SHOT:
            add("too-short", s, f"只停 {round(s['end'] - s['start'], 2)}s，至少 {MIN_SHOT}s 才看得清")
        if not s["start"] <= s["hold"] <= s["end"]:
            add("hold-outside-shot", s, f"hold {s['hold']}s 不在镜头 {s['start']}–{s['end']}s 内")
        for a, z in b.get("no_motion") or []:
            if s["start"] < z and a < s["end"]:
                add("no-motion-range", s, f"镜头 {s['start']}–{s['end']}s 碰到不加动效的时间段 {a}–{z}s")
        zone = _zone(s, b)
        band = b.get("caption_band") if b.get("captions_burned_in", True) else None
        if band and s["zone"] != "full" and zone["y"] < band[1] and band[0] < zone["y"] + zone["h"]:
            add("caption-band", s, f"区域 y{zone['y']}–{zone['y'] + zone['h']} 碰到字幕带 y{band[0]}–{band[1]}")
        if b.get("motion_placement") == "overlay-sides" and s["zone"] != "full" and b.get("face_box"):
            fx, fy, fw, fh = b["face_box"]
            if _overlap(zone, {"x": fx, "y": fy, "w": fw, "h": fh}):
                add("covers-face", s, f"区域 {zone} 盖到人脸 {b['face_box']}")
        last_end = None
        for r in s.get("reveals") or []:
            span = _spoken_span(ws, r["text"], s["start"] - SEARCH, s["end"] + SEARCH)
            if span is None:
                add("text-not-spoken", s, f"「{r['text']}」在 {s['start']}–{s['end']}s 附近没说过")
                continue
            if r["at"] < span[0] - FRAME - 1e-9:
                add("text-before-speech", s, f"「{r['text']}」{r['at']}s 出现，{span[0]}s 才说")
            last_end = span[1] if last_end is None else max(last_end, span[1])
        style_rules(s, b, ws, add, last_end)
        proof_mod.rules(s, b, evidence or [], add)

    for i, a in enumerate(shots):
        for c in shots[i + 1:]:
            if a["start"] < c["end"] and c["start"] < a["end"] and _overlap(_zone(a, b), _zone(c, b)):
                add("zone-overlap", c, f"和 {a['id']} 在同一区域、时间重叠")
    by_time = sorted(shots, key=lambda x: x["start"])
    premium = b.get("effort") in ("c", "d")
    if premium:
        # 精品：先想清楚这句话要观众明白什么、用什么画面讲，再挑 / 做镜头；同一个组件整条只用一次
        for x in shots:
            it = x.get("intent") or {}
            if not (str(it.get("means", "")).strip() and str(it.get("picture", "")).strip()):
                add("no-intent", x, "精品档每张卡要写 intent.means（这句话要观众明白什么）和 intent.picture（用什么画面讲出来）")
        seen: dict[str, str] = {}
        for x in by_time:
            comp = x.get("component", "")
            if comp in seen:
                add("repeated-component", x, f"{comp} 已经在 {seen[comp]} 用过，精品档整条每个组件只用一次")
            else:
                seen[comp] = x["id"]
        # 重点时刻：功夫集中花在 2–3 张上（按标杆单独做），每张都要指一条标杆，做完左右对比
        keys = [x for x in shots if is_key(x)]
        if len(keys) < KEY_SHOTS[0]:
            out.append({"rule": "no-key-shots", "shot": "plan",
                        "detail": f"精品档挑 {KEY_SHOTS[0]}–{KEY_SHOTS[1]} 个重点时刻标 \"key\": true（功夫花在这几张，样片就渲它们），现在 {len(keys)} 个"})
        elif len(keys) > KEY_SHOTS[1]:
            out.append({"rule": "too-many-key-shots", "shot": "plan",
                        "detail": f"重点时刻最多 {KEY_SHOTS[1]} 个，现在标了 {len(keys)} 个，功夫会摊薄"})
        library = bench_mod.load()
        for x in keys:
            if EFFORT.get(_catalog().get(x.get("component", ""), {}).get("effort", "d"), 3) < EFFORT["c"]:
                add("key-effort-too-low", x, f"重点时刻要用 c 档以上的组件（比喻组件或照意思新做），{x.get('component')} 不够")
            name = x.get("benchmark")
            if not name:
                add("no-benchmark", x, f"重点时刻要写 benchmark：标杆库（{bench_mod.path()}）里意思最接近的一条")
            elif name not in library:
                add("unknown-benchmark", x, f"标杆库（{bench_mod.path()}）里没有「{name}」")
    if b.get("effort", "a") != "a":
        for a, c in zip(by_time, by_time[1:]):
            if _form(a) and _form(a) == _form(c):
                add("same-form", c, f"和前一张 {a['id']} 都是「{_form(c)}」形式，相邻两张换一种")
        want = EFFORT[b["effort"]]
        # 证据截图是内容不是做工；精品档功夫集中在重点时刻，其余的卡也不算「偷懒」
        made = [x for x in shots if _form(x) != "image" and not (premium and not is_key(x))]
        low = [x for x in made if EFFORT.get(_catalog().get(x.get("component", ""), {}).get("effort", "d"), 3) < want]
        if made and len(low) / len(made) > LOW_EFFORT_SHARE:
            out.append({"rule": "effort-too-low", "shot": "plan",
                        "detail": f"{len(low)}/{len(made)} 张卡低于努力程度 {b['effort']}，最多 {LOW_EFFORT_SHARE:.0%}"})
    if "density" in b or "coverage" in b:
        lo, hi = brief_mod.coverage_range(b)
        got = coverage(plan, b)
        if not lo - 1e-9 <= got <= hi + 1e-9:
            out.append({"rule": "density", "shot": "plan",
                        "detail": f"动效占 {got:.0%}，这条视频要 {lo:.0%}–{hi:.0%}（密度 {b.get('density')}）"})
    gap = b.get("min_gap") or 0
    ordered = sorted(shots, key=lambda x: x["start"])
    for a, c in zip(ordered, ordered[1:]):
        if gap and c["start"] - a["end"] < gap:
            add("gap", c, f"和 {a['id']} 之间只留了 {round(c['start'] - a['end'], 2)}s 纯人脸，要至少 {gap}s")
    return out


def style_rules(s: dict[str, Any], b: dict[str, Any], ws: list[dict[str, Any]], add: Any, last_end: float | None) -> None:
    """defaults.yaml / brief.yaml 里 Park 定的风格和规则。"""
    props = s.get("props") or {}
    texts = _texts(props) + [r["text"] for r in s.get("reveals") or []]
    for word in b.get("banned_words") or []:
        if any(_clean(word) and _clean(word) in _clean(t) for t in texts):
            add("banned-word", s, f"画面上出现了不能出现的词「{word}」")
    for key in LISTS:
        if isinstance(props.get(key), list) and len(props[key]) > b.get("max_items", 99):
            add("too-many-items", s, f"{key} 有 {len(props[key])} 条，一张卡最多 {b['max_items']} 条")
    entry_limits = _catalog().get(s.get("component", ""), {}).get("limits")
    proof = s.get("component") == "Proof"  # 截图卡上的字是来源一行，不是他说的话：不套字数、不查原话删减
    if b.get("text_amount") == "one-point" and not entry_limits and not proof:  # 讲过程的组件有自己每段字数的上限（limits），不再套总字数
        n = sum(len(_clean(t)) for t in _texts(props))
        if n > ONE_POINT_CHARS:
            add("not-one-point", s, f"卡上一共 {n} 个字，一张卡一个重点最多 {ONE_POINT_CHARS} 个")
    if s.get("component") == "TextLines":
        w = _zone(s, b)["w"]
        for i, line in enumerate(props.get("lines") or []):
            if line_px(line, w, i) < MIN_TEXT_PX:
                add("text-too-small", s, f"「{line}」在这块区域里只能用 {line_px(line, w, i)}px 字号，拆短一点（至少 {MIN_TEXT_PX}px）")
    entry = _catalog().get(s.get("component", ""), {})
    if s.get("component") in (b.get("avoid") or []):
        add("avoided-component", s, f"{s.get('component')}（{entry.get('name', '')}）在「不用的样式」里")
    if not entry:
        add("unknown-component", s, f"组件库里没有 {s.get('component')}（见 motion/src/library/catalog.json）")
    if entry.get("settle") is not None and (_times(props) or s.get("reveals")):
        done = max(_times(props) + [r["at"] for r in s.get("reveals") or []]) + entry["settle"]
        if s["hold"] + 1e-9 < done:
            add("hold-before-settle", s, f"{s.get('component')} 要到 {round(done, 2)}s 才做完动作，hold 写的是 {s['hold']}s")
        if s["end"] < done + 0.5:
            add("too-short", s, f"{s.get('component')} 动作做完（{round(done, 2)}s）后至少再停 0.5s，镜头到 {s['end']}s 就走了")
    if entry.get("min_zone_w") and _zone(s, b)["w"] < entry["min_zone_w"]:
        add("zone-too-narrow", s, f"{s.get('component')} 至少要 {entry['min_zone_w']}px 宽的区域，这块只有 {_zone(s, b)['w']}px（换到另一侧，或换组件）")
    for path, limit in (entry.get("limits") or {}).items():
        for t in _at_path(props, path):
            if len(_clean(t)) > limit:
                add("label-too-long", s, f"「{t}」{len(_clean(t))} 个字，{s.get('component')} 的 {path} 最多 {limit} 个字")
    for name in _icons(props):
        if ICON_DIR.is_dir() and not (ICON_DIR / f"{name}.mjs").is_file():
            add("unknown-icon", s, f"图标库里没有「{name}」（lucide 的短横线名字，见 https://lucide.dev/icons）")
    if entry and "effort" in b and EFFORT[entry["effort"]] > EFFORT[b["effort"]]:
        add("effort-too-high", s, f"{s.get('component')} 是努力程度 {entry['effort']} 的组件，这条视频定的是 {b['effort']}")
    if b.get("rewrite") == "trim-only" and not proof:
        for t in _texts(props):
            if not _trimmed_from_speech(ws, t, s["start"] - SEARCH, s["end"] + SEARCH):
                add("rewritten", s, f"「{t}」不是原话删减出来的（换了词或加了词）")
    grace = {"after-sentence": EXIT_GRACE, "until-next": UNTIL_NEXT_MAX}.get(b.get("exit", ""))
    if grace is not None and last_end is not None and s["end"] > last_end + grace:
        add("stays-too-long", s, f"最后一句 {last_end}s 说完，卡片到 {s['end']}s 才走，最多再停 {grace}s")


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2
    plan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    words = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    found = run(plan, words, brief_mod.load(Path(argv[3])), proof_mod.load(Path(argv[3]).parent))
    print(json.dumps(found, ensure_ascii=False, indent=2))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
