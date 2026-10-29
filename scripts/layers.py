"""逐个镜头渲染透明动效层（Remotion），并生成 render.py 用的 render-plan。

每个镜头的画布就是它要放的区域（brief 推出的 left / right，或自定义 {x,y,w,h}），所以层很小、渲染很快。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from check import _zone
from render import write_status

MOTION = Path(__file__).resolve().parents[1] / "motion"
GLASS_ALPHA = 0.45  # 毛玻璃卡片那层半透明白的不透明度；render.py 用 1/它 把层的 alpha 放大成「这里要模糊」的蒙版


def shots_between(plan: dict[str, Any], start: float, end: float) -> list[dict[str, Any]]:
    return [s for s in plan["shots"] if s["start"] < end and start < s["end"]]


def sample_window(plan: dict[str, Any], length: float = 10.0) -> tuple[float, float]:
    """10 秒样片：从第一个镜头前 0.5 秒开始。Park 说随便选一段就好。"""
    first = min(s["start"] for s in plan["shots"])
    a = max(0.0, first - 0.5)
    return (round(a, 3), round(min(a + length, plan["duration"]), 3))


def style(brief: dict[str, Any]) -> dict[str, Any]:
    """这条视频的卡片外观，传给 Remotion。"""
    return {"card": brief.get("card", "paper"), "accent": brief.get("accent", "#E2461F"),
            "overshoot": bool(brief.get("overshoot", False)), "glassAlpha": GLASS_ALPHA}


def layer_props(shot: dict[str, Any], zone: dict[str, int], look: dict[str, Any] | None = None) -> dict[str, Any]:
    side = shot["zone"] if shot.get("zone") in ("left", "right") else "left"
    return {"component": shot["component"], "zone": {"w": zone["w"], "h": zone["h"]}, "start": shot["start"],
            "end": shot["end"], "props": shot.get("props") or {}, "style": {**(look or {}), "side": side}}


def saved_props(shot: dict[str, Any], zone: dict[str, int], look: dict[str, Any] | None = None, scale: float = 1.0) -> dict[str, Any]:
    """存在层旁边的那份：渲染它的 props，原片放大过（4K）再记上倍数，倍数变了层也算过期。"""
    props = layer_props(shot, zone, look)
    return props if scale == 1 else {**props, "renderScale": scale}


def props_file(layer: Path) -> Path:
    """每个层旁边存一份渲染它用的 props：方案或外观一变，就知道这个层过期了。"""
    return layer.with_suffix(".props.json")


def remotion_cmd(shot: dict[str, Any], zone: dict[str, int], out: Path, look: dict[str, Any] | None = None,
                 public: Path | None = None, scale: float = 1.0) -> list[str]:
    """public：证据截图所在的目录（项目的 v2/evidence/），Proof 卡用 staticFile 从这里读图。
    scale：原片是 canvas 的几倍（4K 是 2）。组件照 canvas 尺寸排版，Remotion 按倍数渲得更大，字不糊。"""
    props = layer_props(shot, zone, look)
    return ["npx", "remotion", "render", "src/index.ts", "Shot", str(out), "--codec=prores", "--prores-profile=4444",
            "--pixel-format=yuva444p10le", "--image-format=png", "--muted", "--log=error",
            *([f"--public-dir={public}"] if public else []), *([f"--scale={scale}"] if scale != 1 else []),
            "--props=" + json.dumps(props, ensure_ascii=False)]


def render_layers(plan: dict[str, Any], brief: dict[str, Any], layer_dir: Path, *, status: Path | None,
                  only: list[dict[str, Any]] | None = None, weight: tuple[int, int] = (0, 100), public: Path | None = None,
                  scale: float = 1.0) -> list[Path]:
    layer_dir.mkdir(parents=True, exist_ok=True)
    shots = only if only is not None else plan["shots"]
    outs = []
    for i, s in enumerate(shots):
        write_status(status, "rendering", i, len(shots), stage="layers", weight=weight, unit="shots")
        out = layer_dir / f"{s['id']}.mov"
        props_file(out).unlink(missing_ok=True)
        r = subprocess.run(remotion_cmd(s, _zone(s, brief), out, style(brief), public, scale), cwd=MOTION, capture_output=True, text=True)
        if r.returncode != 0:
            write_status(status, "failed", i, len(shots), stage="layers", weight=weight, unit="shots")
            raise RuntimeError(f"{s['id']} 渲染失败：{(r.stderr or r.stdout)[-1500:]}")
        props_file(out).write_text(json.dumps(saved_props(s, _zone(s, brief), style(brief), scale), ensure_ascii=False, sort_keys=True),
                                   encoding="utf-8")
        outs.append(out)
    write_status(status, "rendering", len(shots), len(shots), stage="layers", weight=weight, unit="shots")
    return outs


def render_plan(plan: dict[str, Any], brief: dict[str, Any], *, base: str, layer_dir: Path, scale: float = 1.0,
                captions: str | None = None) -> dict[str, Any]:
    """scale ≠ 1（4K 原片配 1920×1080 的 canvas）：区域和层都换算成原片像素，render.py 照原片坐标叠，成片保住原分辨率。"""
    glass = GLASS_ALPHA if brief.get("card") == "glass" else None
    shots = []
    for s in plan["shots"]:
        z = _zone(s, brief)
        if scale == 1:
            w, h = round(z["w"] / 2) * 2, round(z["h"] / 2) * 2
        else:  # Remotion --scale 出来的层是 w·scale × h·scale；往下取偶数，裁的不会超出层
            w, h = int(z["w"] * scale) // 2 * 2, int(z["h"] * scale) // 2 * 2
            z = {k: round(v * scale) for k, v in z.items()}
        shots.append({"id": s["id"], "start": s["start"], "end": s["end"], "hold": s.get("hold", s["end"]),
                      "layer": str(layer_dir / f"{s['id']}.mov"), "src_rect": [0, 0, w, h], "zone": z,
                      "glass": glass, **({"blur": round(24 * scale)} if scale != 1 else {})})
    cw, ch = brief["canvas"]
    return {"base": base, "canvas": [round(cw * scale), round(ch * scale)] if scale != 1 else brief["canvas"], "scale": scale,
            "shots": shots, **({"captions": captions} if captions else {})}
