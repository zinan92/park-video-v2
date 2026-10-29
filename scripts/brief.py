"""Park 在开头说清楚的东西（brief.yaml）。缺字段就停下来问他，不让 AI 猜。

风格和规则（密度、努力程度、卡片底色、能不能改写原话……）在仓库根目录 defaults.yaml 里填一次；
brief.yaml 里写同名字段就覆盖这一条视频。"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / "defaults.yaml"
SETTINGS = ROOT / "settings.yaml"
USER_DEFAULTS_ENV = "PV2_USER_DEFAULTS"  # 测试时指到临时文件
REQUIRED = ("video_type", "canvas", "motion_placement", "no_motion", "captions_burned_in")
PLACEMENTS = ("overlay-sides", "broll", "fullscreen")
DENSITY = {"low": (0.10, 0.20), "medium": (0.30, 0.40), "high": (0.50, 0.60)}  # 动效占可加动效时长的比例
# 密度的标准（10/29 Park：「低中高要定一个标准」）：比例是唯一的标准，张数从它换算——一张卡平均停 5 秒，
# 高密度按 60% 算上限（再多人脸就太少了）。口播大约每秒 4 个字，没有视频时（工作台排镜头表）按字数估时长。
CARD_SECONDS = 5.0
HIGH_CAP = 0.60
CHARS_PER_SECOND = 4.0
ALIASES = {"density": {"mid": "medium"}}  # 工作台渲染包的 settings.json 写过 mid


class NeedsPark(Exception):
    """brief 缺了只有 Park 能回答的字段。"""

    def __init__(self, missing: list[str]):
        self.missing = missing
        super().__init__("brief 缺这些字段，停下来问 Park：" + "、".join(missing))


def schema() -> dict[str, Any]:
    return yaml.safe_load(SETTINGS.read_text(encoding="utf-8")) or {}


def user_defaults_path() -> Path:
    return Path(os.environ.get(USER_DEFAULTS_ENV) or Path.home() / ".config" / "park-video-v2" / "defaults.yaml")


def _yaml(path: Path) -> dict[str, Any]:
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError:
        return {}


def defaults() -> dict[str, Any]:
    """仓库默认值 + Park 在工作台设的默认值（后者覆盖前者）。"""
    return {**_yaml(DEFAULTS), **_yaml(user_defaults_path())}


def normalize(key: str, value: Any) -> Any:
    """别名换成正式取值（density: mid → medium）；其余原样。"""
    return ALIASES.get(key, {}).get(value, value) if isinstance(value, str) else value


def check_value(key: str, value: Any) -> None:
    """按 settings.yaml 校验一个设置的取值；不认识的 key 不管（brief 里还有 face_box 之类）。"""
    value = normalize(key, value)
    sc = schema()
    for sl in sc.get("sliders") or []:
        if sl["key"] == key:
            level = next((lv for lv in sl["levels"] if lv["value"] == value), None)
            if level is None:
                raise ValueError(f"{key}（{sl['name']}）只能是 {' / '.join(lv['value'] for lv in sl['levels'])}，收到 {value!r}")
            if level.get("available") is False:
                raise ValueError(f"{sl['name']}「{level['label']}」这一档还没做，先选别的档")
            return
    for ch in (sc.get("choices") or []) + (sc.get("per_video") or []):
        if ch["key"] != key:
            continue
        if "options" in ch and value not in [o["value"] for o in ch["options"]]:
            raise ValueError(f"{key}（{ch['name']}）只能是 {' / '.join(o['value'] for o in ch['options'])}，收到 {value!r}")
        kind = ch.get("type")
        if kind == "bool" and not isinstance(value, bool):
            raise ValueError(f"{key}（{ch['name']}）要写 true / false")
        if kind in ("int", "number"):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or (kind == "int" and not isinstance(value, int)):
                raise ValueError(f"{key}（{ch['name']}）要写数字")
            if not ch.get("min", value) <= value <= ch.get("max", value):
                raise ValueError(f"{key}（{ch['name']}）要在 {ch.get('min')}–{ch.get('max')} 之间")
        if kind == "components" and not (isinstance(value, list) and all(isinstance(v, str) for v in value)):
            raise ValueError(f"{key}（{ch['name']}）要写组件名列表")
        if kind == "color" and not (isinstance(value, str) and value.startswith("#")):
            raise ValueError(f"{key}（{ch['name']}）要写 #rrggbb 颜色")
        return


def load(path: Path) -> dict[str, Any]:
    own = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    data = {k: normalize(k, v) for k, v in {**defaults(), "banned_words": [], **own}.items()}
    missing = [k for k in REQUIRED if k not in data]
    if data.get("motion_placement") == "overlay-sides" and "face_box" not in data:
        missing.append("face_box")
    if data.get("captions_burned_in") and "caption_band" not in data:
        missing.append("caption_band")
    if data.get("burn_captions") and data.get("captions_burned_in"):
        raise ValueError("字幕已经烧在画面里（captions_burned_in: true），就不能再烧一遍（burn_captions）")
    if data.get("burn_captions") and "caption_band" not in data and "canvas" in data:
        import captions
        data["caption_band"] = captions.band(data["canvas"])  # 我们自己烧的字幕在哪，动效就避开哪
    if missing:
        raise NeedsPark(missing)
    if data["motion_placement"] not in PLACEMENTS:
        raise ValueError(f"motion_placement 只能是 {' / '.join(PLACEMENTS)}，收到 {data['motion_placement']!r}")
    cov = data.get("coverage")
    if cov is not None and not (isinstance(cov, list) and len(cov) == 2 and 0 <= cov[0] <= cov[1] <= 1):
        raise ValueError(f"coverage 要写成 [下限, 上限]，0–1 之间，收到 {cov!r}")
    for key, value in data.items():
        check_value(key, value)
    return data


def coverage_range(b: dict[str, Any]) -> tuple[float, float]:
    """这条视频的动效比例区间：brief 里写了 coverage: [下限, 上限] 就用它，否则按 density 档。"""
    if b.get("coverage"):
        lo, hi = b["coverage"]
        return float(lo), float(hi)
    return DENSITY[normalize("density", b.get("density", "medium"))]


def cards_for(seconds: float, density: str = "medium") -> tuple[int, int]:
    """这么长（可加动效的秒数）、这个密度，大约放几张卡：(最少, 最多)。工作台排镜头表照这个数排。"""
    import math
    lo, hi = DENSITY[normalize("density", density)]
    return max(1, math.ceil(seconds * lo / CARD_SECONDS)), max(1, math.floor(seconds * min(hi, HIGH_CAP) / CARD_SECONDS))


def min_text_px(b: dict[str, Any], base: int = 56) -> float:
    """卡上主要文字的最小字号：1080p 画布是 base px，canvas 写成 4K 就跟着翻倍。"""
    return base * (b.get("canvas") or [1920, 1080])[1] / 1080


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
