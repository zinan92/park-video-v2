"""证据截图（10/5 Park）：内容工作台骨架页里点过「要」的真截图，放进这条视频的 v2/evidence/。

Park：以前很多图是直接生成的，没有真实感，非常减分。证据要真——新闻、数据、原推、他自己的截图，都是工作台核对过、
他点过「要」的。这里只收工作台给的清单，不自己找、不自己画；方案里的 Proof 镜头只能用清单里的图（check 会拦）。

用法：python3 scripts/pv2.py evidence <项目> <清单.json>
清单是一个列表，每条 {path, kind, source, date, caption, claim, point, point_title, url}；再给一次就整份换掉（以他现在点的为准）。
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

FOLDER = "evidence"
MANIFEST = "evidence.json"
IMAGES = (".png", ".jpg", ".jpeg", ".webp")
MIN_SECONDS = 4.0  # 截图要看清图、再看一眼来源，至少停这么久


def line(item: dict[str, Any]) -> str:
    """画面上图下面那一行：来源 · 日期。方案里 props.source 必须一字不差用它，不许编来源。"""
    who = str(item.get("source") or "").strip()
    day = str(item.get("date") or "").strip()[:10]
    return "来源：" + " · ".join(x for x in (who, day) if x)


def load(v2: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads((v2 / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [i for i in data.get("items") or [] if isinstance(i, dict) and (v2 / FOLDER / str(i.get("file") or "")).is_file()]


def level(items: list[dict[str, Any]]) -> str:
    """brief 的「证据与素材」：全是他自己的截图是 own，有外面找来的是 search，没有就 none。"""
    if not items:
        return "none"
    return "own" if all(i.get("kind") == "mine" for i in items) else "search"


def put(v2: Path, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把清单里的图拷进 v2/evidence/（文件名取内容哈希），写 v2/evidence.json。旧的、不在清单里的图删掉。"""
    if not v2.is_dir():
        raise ValueError(f"{v2.parent} 还没有 v2/，先 init")
    folder = v2 / FOLDER
    folder.mkdir(exist_ok=True)
    out = []
    for i in items:
        src = Path(str(i.get("path") or "")).expanduser()
        if src.suffix.lower() not in IMAGES or not src.is_file():
            raise ValueError(f"找不到这张图，或者不是图片：{src}")
        name = hashlib.sha256(src.read_bytes()).hexdigest()[:12] + src.suffix.lower()
        if not (folder / name).is_file():
            shutil.copyfile(src, folder / name)
        keep = {k: i.get(k) or "" for k in ("kind", "source", "date", "caption", "claim", "point", "point_title", "url")}
        out.append({**keep, "file": name, "line": line(i)})
    names = {i["file"] for i in out}
    for f in folder.iterdir():
        if f.name not in names:
            f.unlink()
    (v2 / MANIFEST).write_text(json.dumps({"items": out}, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def rules(s: dict[str, Any], b: dict[str, Any], items: list[dict[str, Any]], add: Any) -> None:
    """Proof 镜头：只能放清单里的图、来源照抄清单、要停够时间；这条视频设了「不放」就不能有。"""
    if s.get("component") != "Proof":
        return
    props = s.get("props") or {}
    if b.get("evidence", "none") == "none":
        add("proof-off", s, "这条视频的「证据与素材」是不放，不能有截图卡（工作台把他点过「要」的证据放进来时会改成 own / search）")
    item = next((i for i in items if i["file"] == props.get("src")), None)
    if item is None:
        add("proof-unknown", s, f"「{props.get('src')}」不在 v2/evidence.json 里：截图卡只能放工作台里他点过「要」的图")
    elif props.get("source") != item["line"]:
        add("proof-source", s, f"来源要一字不差写「{item['line']}」，现在是「{props.get('source')}」")
    if s["end"] - s["start"] < MIN_SECONDS:
        add("proof-too-short", s, f"截图卡只停 {round(s['end'] - s['start'], 2)}s，至少 {MIN_SECONDS}s 才看得清图和来源")
