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


def shots_between(plan: dict[str, Any], start: float, end: float) -> list[dict[str, Any]]:
    return [s for s in plan["shots"] if s["start"] < end and start < s["end"]]


def sample_window(plan: dict[str, Any], length: float = 10.0) -> tuple[float, float]:
    """10 秒样片：从第一个镜头前 0.5 秒开始。Park 说随便选一段就好。"""
    first = min(s["start"] for s in plan["shots"])
    a = max(0.0, first - 0.5)
    return (round(a, 3), round(min(a + length, plan["duration"]), 3))


def remotion_cmd(shot: dict[str, Any], zone: dict[str, int], out: Path) -> list[str]:
    props = {"component": shot["component"], "zone": {"w": zone["w"], "h": zone["h"]}, "start": shot["start"],
             "end": shot["end"], "props": shot.get("props") or {}}
    return ["npx", "remotion", "render", "src/index.ts", "Shot", str(out), "--codec=prores", "--prores-profile=4444",
            "--pixel-format=yuva444p10le", "--image-format=png", "--log=error",
            "--props=" + json.dumps(props, ensure_ascii=False)]


def render_layers(plan: dict[str, Any], brief: dict[str, Any], layer_dir: Path, *, status: Path | None,
                  only: list[dict[str, Any]] | None = None, weight: tuple[int, int] = (0, 100)) -> list[Path]:
    layer_dir.mkdir(parents=True, exist_ok=True)
    shots = only if only is not None else plan["shots"]
    outs = []
    for i, s in enumerate(shots):
        write_status(status, "rendering", i, len(shots), stage="layers", weight=weight, unit="shots")
        out = layer_dir / f"{s['id']}.mov"
        r = subprocess.run(remotion_cmd(s, _zone(s, brief), out), cwd=MOTION, capture_output=True, text=True)
        if r.returncode != 0:
            write_status(status, "failed", i, len(shots), stage="layers", weight=weight, unit="shots")
            raise RuntimeError(f"{s['id']} 渲染失败：{(r.stderr or r.stdout)[-1500:]}")
        outs.append(out)
    write_status(status, "rendering", len(shots), len(shots), stage="layers", weight=weight, unit="shots")
    return outs


def render_plan(plan: dict[str, Any], brief: dict[str, Any], *, base: str, layer_dir: Path) -> dict[str, Any]:
    shots = []
    for s in plan["shots"]:
        z = _zone(s, brief)
        w, h = round(z["w"] / 2) * 2, round(z["h"] / 2) * 2
        shots.append({"id": s["id"], "start": s["start"], "end": s["end"], "hold": s.get("hold", s["end"]),
                      "layer": str(layer_dir / f"{s['id']}.mov"), "src_rect": [0, 0, w, h], "zone": z})
    return {"base": base, "canvas": brief["canvas"], "shots": shots}
