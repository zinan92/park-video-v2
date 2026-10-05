"""标杆库：Park 认可过的镜头。精品档的重点镜头做完，要和意思最接近的一条左右对比，不低于它才拿给 Park 看。

标杆是他以前的成片片段（客户画面），所以库只在本机：~/.config/park-video-v2/benchmarks.yaml，不进这个公开仓库。
测试用 PV2_BENCHMARKS 指到临时文件。

  抓重点-20个因素:
    video: /path/to/之前交付的成片.mp4
    start: 59.0
    end: 72.2
    shows: 从一群并列对象里挑出唯一重点（筛选/聚焦）   # 写方案时按这句挑最接近的标杆

方案里重点镜头写 "key": true, "benchmark": "抓重点-20个因素"。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

ENV = "PV2_BENCHMARKS"


def path() -> Path:
    return Path(os.environ.get(ENV) or Path.home() / ".config" / "park-video-v2" / "benchmarks.yaml")


def load() -> dict[str, dict[str, Any]]:
    f = path()
    if not f.is_file():
        return {}
    data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
    return {str(k): v for k, v in data.items() if isinstance(v, dict)}


def resolve(name: str) -> dict[str, Any]:
    """一条标杆：{name, video, start, end, shows}。找不到、或视频不在（移动硬盘没插）就报清楚。"""
    entry = load().get(name)
    if entry is None:
        raise SystemExit(f"标杆库（{path()}）里没有「{name}」")
    video = Path(str(entry.get("video", ""))).expanduser()
    if not video.is_file():
        raise SystemExit(f"标杆「{name}」的视频不在：{video}（移动硬盘插了吗？）")
    return {"name": name, "video": str(video), "start": float(entry["start"]), "end": float(entry["end"]), "shows": entry.get("shows", "")}
