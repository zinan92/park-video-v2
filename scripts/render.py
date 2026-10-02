#!/usr/bin/env python3
"""把动效层叠到原画面上：10 秒样片和整条视频走同一个函数，只是时间范围不同。

用法：
  python3 scripts/render.py <render-plan.json> <out.mp4> [--from 秒 --to 秒] [--status status.json] [--detach]

render-plan.json：
  {"base": 原视频, "canvas": [w, h],
   "shots": [{"id", "start", "end", "layer": 透明动效层(.mov), "src_rect": [x, y, w, h] 层里要裁出的那块,
              "zone": {x, y, w, h} 放到画面哪里}]}

status.json 实时写 {state, done, total, percent, unit}：state 是 rendering / done / failed。
--detach 在独立进程组里跑（调它的 agent 退出也不会把渲染带走），立刻返回。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def fit(src: tuple[int, int], zone: dict[str, int]) -> dict[str, int]:
    """等比缩放进 zone：横向居中、纵向居中。"""
    sw, sh = src
    s = min(zone["w"] / sw, zone["h"] / sh)
    w, h = round(sw * s), round(sh * s)
    return {"x": zone["x"] + (zone["w"] - w) // 2, "y": zone["y"] + (zone["h"] - h) // 2, "w": w, "h": h}


def in_range(shots: list[dict[str, Any]], start: float, end: float) -> list[dict[str, Any]]:
    return [s for s in shots if s["start"] < end and start < s["end"]]


def filtergraph(shots: list[dict[str, Any]]) -> str:
    """输入 0 是原画面，输入 1..n 是各镜头的动效层；最后一路叫 [v1]…[vN]，最终输出标签见返回值末尾。"""
    parts, prev = [], "[0:v]"
    for i, s in enumerate(shots, start=1):
        x, y, w, h = s["src_rect"]
        p = s["place"]
        parts.append(f"[{i}:v]crop={w}:{h}:{x}:{y},scale={p['w']}:{p['h']},setpts=PTS-STARTPTS+{s['start']}/TB[l{i}]")
        parts.append(f"{prev}[l{i}]overlay={p['x']}:{p['y']}:enable='between(t,{s['start']},{s['end']})':eof_action=pass[v{i}]")
        prev = f"[v{i}]"
    if not shots:
        parts.append("[0:v]null[v1]")
    return ";".join(parts)


def write_status(path: Path | None, state: str, done: float, total: float, *, stage: str = "composite",
                 weight: tuple[int, int] = (0, 100), unit: str = "seconds") -> None:
    """status.json：state = rendering / done / failed；percent 是整条流程的总进度（本阶段占 weight 这一段）。"""
    if path is None:
        return
    lo, hi = weight
    pct = hi if state == "done" else int(lo + (hi - lo) * done / total) if total else lo
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps({"state": state, "stage": stage, "done": round(done, 2), "total": round(total, 2),
                               "unit": unit, "percent": pct}, ensure_ascii=False))
    os.replace(tmp, path)


def render(plan: dict[str, Any], out: Path, status: Path | None, *, start: float = 0.0, end: float | None = None,
           weight: tuple[int, int] = (0, 100)) -> None:
    base = plan["base"]
    if end is None:
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", base],
                               capture_output=True, text=True, check=True)
        end = float(probe.stdout)
    total = end - start
    # 直接跳到 start：原画面和动效层都按输入 seek，镜头时间换成相对样片开头的秒数
    shots, inputs = [], ["-ss", f"{start:.3f}", "-t", f"{total:.3f}", "-i", base]
    for s in in_range(plan["shots"], start, end):
        x, y, w, h = s["src_rect"]
        skip = max(0.0, start - s["start"])
        inputs += (["-ss", f"{skip:.3f}"] if skip else []) + ["-i", s["layer"]]
        shots.append({**s, "start": round(max(s["start"], start) - start, 3), "end": round(min(s["end"], end) - start, 3),
                      "place": fit((w, h), s["zone"])})
    graph = filtergraph(shots)
    last = f"[v{max(len(shots), 1)}]"
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs]
    cmd += ["-filter_complex", graph + f";{last}null[out]", "-map", "[out]", "-map", "0:a?",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-progress", "pipe:1", "-nostats", str(out)]
    write_status(status, "rendering", 0.0, total, weight=weight)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    assert proc.stdout is not None
    for line in proc.stdout:
        if line.startswith("out_time_us=") and line.strip().split("=")[1].isdigit():
            write_status(status, "rendering", min(int(line.split("=")[1]) / 1e6, total), total, weight=weight)
    err = proc.stderr.read() if proc.stderr else ""
    if proc.wait() != 0:
        write_status(status, "failed", 0.0, total, weight=weight)
        raise RuntimeError(f"ffmpeg 失败：{err[-1500:]}")
    write_status(status, "rendering" if weight[1] < 100 else "done", total, total, weight=weight)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan")
    ap.add_argument("out")
    ap.add_argument("--from", dest="start", type=float, default=0.0)
    ap.add_argument("--to", dest="end", type=float)
    ap.add_argument("--status")
    ap.add_argument("--detach", action="store_true")
    a = ap.parse_args(argv[1:])
    if a.detach:
        args = [sys.executable, os.path.abspath(__file__), a.plan, a.out, "--from", str(a.start)]
        args += (["--to", str(a.end)] if a.end is not None else []) + (["--status", a.status] if a.status else [])
        log = open(Path(a.out).with_suffix(".log"), "w")
        subprocess.Popen(args, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
        print(f"后台渲染已启动，进度看 {a.status or '（未指定 --status）'}")
        return 0
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    render(plan, Path(a.out), Path(a.status) if a.status else None, start=a.start, end=a.end)
    print(f"done → {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
