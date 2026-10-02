"""方案的程序检查：几秒内跑完，不靠 AI 评审。

用法：python3 scripts/check.py <plan.json> <words.json> <brief.yaml>
没有问题时输出 []、退出码 0；有问题时逐条列出、退出码 1。

plan.json 里每个镜头：{id, start, end, zone, component, reveals: [{at, text}], hold}
- zone：left / right / full，或者 {x, y, w, h}
- reveals：每段文字出现的时刻和它显示的原话，用来查「文字不早于说出口」
- hold：从这一刻起画面不再动（渲染后由 qa.py 实测）
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

import brief as brief_mod

FRAME = 1 / 30
SEARCH = 5.0  # 在镜头前后多少秒内找原话


def _clean(text: str) -> str:
    return re.sub(r"[^\w]", "", text)


def _spoken_at(words: list[dict[str, Any]], text: str, lo: float, hi: float) -> float | None:
    """这句话在 [lo, hi] 附近第一次被说出的时刻（第一个字所在词的开始）。"""
    target = _clean(text)
    if not target:
        return None
    flat, owner = [], []
    for i, w in enumerate(words):
        for ch in _clean(w["w"]):
            flat.append(ch)
            owner.append(i)
    stream = "".join(flat)
    at = stream.find(target)
    best = None
    while at >= 0:
        start = words[owner[at]]["start"]
        if lo <= start <= hi:
            best = start if best is None else min(best, start)
        at = stream.find(target, at + 1)
    return best


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


def run(plan: dict[str, Any], words: dict[str, Any], b: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    ws = words.get("words") or []

    def add(rule: str, shot: dict[str, Any], detail: str) -> None:
        out.append({"rule": rule, "shot": shot["id"], "detail": detail})

    shots = plan.get("shots") or []
    for s in shots:
        if s["start"] < 0 or s["end"] > plan["duration"]:
            add("outside-video", s, f"{s['start']}–{s['end']}s 超出视频 0–{plan['duration']}s")
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
        for r in s.get("reveals") or []:
            spoken = _spoken_at(ws, r["text"], s["start"] - SEARCH, s["end"] + SEARCH)
            if spoken is None:
                add("text-not-spoken", s, f"「{r['text']}」在 {s['start']}–{s['end']}s 附近没说过")
            elif r["at"] < spoken - FRAME - 1e-9:
                add("text-before-speech", s, f"「{r['text']}」{r['at']}s 出现，{spoken}s 才说")

    for i, a in enumerate(shots):
        for c in shots[i + 1:]:
            if a["start"] < c["end"] and c["start"] < a["end"] and _overlap(_zone(a, b), _zone(c, b)):
                add("zone-overlap", c, f"和 {a['id']} 在同一区域、时间重叠")
    return out


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print(__doc__)
        return 2
    plan = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    words = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
    found = run(plan, words, brief_mod.load(Path(argv[3])))
    print(json.dumps(found, ensure_ascii=False, indent=2))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
