"""Park 在开头说清楚的东西（brief.yaml）。缺字段就停下来问他，不让 AI 猜。"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

REQUIRED = ("video_type", "canvas", "motion_placement", "no_motion", "captions_burned_in", "sfx", "bgm")
PLACEMENTS = ("overlay-sides", "broll", "fullscreen")


class NeedsPark(Exception):
    """brief 缺了只有 Park 能回答的字段。"""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__("brief 缺这些字段，停下来问 Park：" + "、".join(missing))


def load(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    missing = [k for k in REQUIRED if k not in data]
    if data.get("motion_placement") == "overlay-sides" and "face_box" not in data:
        missing.append("face_box")
    if data.get("captions_burned_in") and "caption_band" not in data:
        missing.append("caption_band")
    if missing:
        raise NeedsPark(missing)
    if data["motion_placement"] not in PLACEMENTS:
        raise ValueError(f"motion_placement 只能是 {' / '.join(PLACEMENTS)}，收到 {data['motion_placement']!r}")
    return data


def side_zones(b: dict[str, Any], margin: int = 40) -> tuple[dict[str, int], dict[str, int]]:
    """人脸居中时左右两块可放动效的区域：人脸两侧留 margin，下沿停在字幕带上方 margin。"""
    width, height = b["canvas"]
    fx, _fy, fw, _fh = b["face_box"]
    bottom = (b.get("caption_band") or [height])[0] - margin
    top = margin
    left = {"x": margin, "y": top, "w": fx - 2 * margin, "h": bottom - top}
    rx = fx + fw + margin
    right = {"x": rx, "y": top, "w": width - margin - rx, "h": bottom - top}
    return left, right
