#!/usr/bin/env python3
"""动效图鉴：把组件库里每个组件用 catalog.json 里的 example 渲一段 4 秒演示，放进 gallery/。

背景是合成的渐变（仓库是公开的，不用任何真实视频画面）；卡片用默认外观（defaults.yaml），
放在人脸左侧那块区域，和成片里一样走 layers.py + render.py。
用法：python3 scripts/pv2.py gallery（只重渲某几个：python3 scripts/gallery.py Proof）
"""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

import brief as brief_mod
import layers
import render

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "gallery"
ASSETS = OUT / "assets"  # 演示用的图（证据截图卡的示例截图是合成的假页面，不是真网页）
SECONDS = 4.0
# 和横屏口播一样的版面：人脸在中间，字幕带在下面
STAGE = {"canvas": [1920, 1080], "face_box": [760, 180, 400, 500], "caption_band": [868, 1000],
         "motion_placement": "overlay-sides"}


def _background(path: Path) -> None:
    """深色渐变 + 几块柔和的亮斑（让毛玻璃的模糊看得出来）。"""
    graph = ("color=c=0x1d2230:s=1920x1080:d={d}:r=30,format=rgb24,"
             "geq=r='29+40*exp(-((X-420)^2+(Y-300)^2)/90000)+30*exp(-((X-1500)^2+(Y-700)^2)/120000)':"
             "g='34+30*exp(-((X-420)^2+(Y-300)^2)/90000)+45*exp(-((X-1500)^2+(Y-700)^2)/120000)':"
             "b='48+60*exp(-((X-420)^2+(Y-300)^2)/90000)+40*exp(-((X-1500)^2+(Y-700)^2)/120000)'").format(d=SECONDS)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", graph, "-pix_fmt", "yuv420p", str(path)], check=True)


def render_all(only: list[str] | None = None) -> list[Path]:
    """only：只重渲这几个组件（加了一个组件不用全部重渲）。"""
    look = {**brief_mod.defaults(), **STAGE}
    data = json.loads((ROOT / "motion" / "src" / "library" / "catalog.json").read_text(encoding="utf-8"))
    OUT.mkdir(exist_ok=True)
    made = []
    with tempfile.TemporaryDirectory() as tmp:
        t = Path(tmp)
        bg = t / "bg.mp4"
        _background(bg)
        for key, c in data.items():
            if key.startswith("_") or (only and key not in only):
                continue
            shot = {"id": key, "start": 0.0, "end": SECONDS, "zone": "left", "component": key, "props": c["example"]}
            plan = {"duration": SECONDS, "shots": [shot]}
            layers.render_layers(plan, look, t / "layers", status=None, public=ASSETS)
            rp = layers.render_plan(plan, look, base=str(bg), layer_dir=t / "layers")
            full = t / f"{key}.mp4"
            render.render(rp, full, None, start=0.0, end=SECONDS)
            z = rp["shots"][0]["zone"]
            video, poster = OUT / f"{key}.mp4", OUT / f"{key}.jpg"
            crop = f"crop={z['w'] + 80}:{z['h'] + 80}:{max(0, z['x'] - 40)}:{max(0, z['y'] - 40)},scale=480:-2"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(full), "-vf", crop, "-an", "-c:v", "libx264", "-crf", "26",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(SECONDS - 0.6), "-i", str(video), "-frames:v", "1", str(poster)],
                           check=True)
            made += [video, poster]
    return made


if __name__ == "__main__":
    import sys

    for p in render_all(sys.argv[1:] or None):
        print(p)
