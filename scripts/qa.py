#!/usr/bin/env python3
"""终检：机器能判的全部用脚本查，几十秒出结果。

用法：python3 scripts/qa.py <成片.mp4> <render-plan.json> <brief.yaml> <输出 qa.json> [--contact 总览.jpg]

查：整片解码、时长、黑帧（≥0.1s）、静音（-50dB ≥2s）、响度、每个镜头摆放不进字幕带不盖人脸、
动效层停住后不再动（plan 里镜头带 hold 时）、抽帧总览图。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import brief as brief_mod
from render import fit


def _ff(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["ffmpeg", "-hide_banner", "-nostats", *args], capture_output=True, text=True)


def _duration(path: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout)


def video_checks(path: Path, *, expected_duration: float | None = None) -> dict[str, Any]:
    decode = _ff(["-v", "error", "-i", str(path), "-f", "null", "-"]).stderr.strip()
    dur = _duration(path)
    black_log = _ff(["-i", str(path), "-vf", "blackdetect=d=0.1:pic_th=0.98", "-an", "-f", "null", "-"]).stderr
    black = [{"start": float(a), "end": float(b)} for a, b in re.findall(r"black_start:([\d.]+) black_end:([\d.]+)", black_log)]
    has_audio = bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index",
                                     "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout.strip())
    silence, loud = [], {}
    if has_audio:
        s_log = _ff(["-i", str(path), "-af", "silencedetect=noise=-50dB:d=2", "-vn", "-f", "null", "-"]).stderr
        starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", s_log)]
        ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", s_log)]
        silence = [{"start": a, "end": (ends[i] if i < len(ends) else dur)} for i, a in enumerate(starts)]
        l_log = _ff(["-i", str(path), "-af", "ebur128", "-vn", "-f", "null", "-"]).stderr
        summary = l_log[l_log.rfind("Summary:"):]
        i_m = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
        lra_m = re.search(r"LRA:\s+([\d.]+) LU", summary)
        loud = {"integrated_lufs": float(i_m.group(1)) if i_m else None, "lra": float(lra_m.group(1)) if lra_m else None}
    duration_ok = expected_duration is None or abs(dur - expected_duration) <= 0.1
    report = {
        "decode": {"errors": decode, "pass": decode == ""},
        "duration": {"seconds": round(dur, 3), "expected": expected_duration, "pass": duration_ok},
        "black": black, "silence": silence, "loudness": loud, "has_audio": has_audio,
    }
    report["status"] = "pass" if (report["decode"]["pass"] and duration_ok and not black and not silence and has_audio) else "fail"
    return report


def _frame_md5(path: Path, t: float) -> str:
    # 按画面上实际显示的 8 位 RGBA 比：ProRes 4444 的 12 位里有编码噪声，像素相同的两帧原生校验值也会不同
    # 只看画面：Remotion 的层里带一条静音音轨，framemd5 也会输出它的包
    r = _ff(["-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-map", "0:v:0", "-an", "-frames:v", "1", "-vf", "format=rgba",
             "-f", "framemd5", "-"])
    lines = [ln for ln in r.stdout.splitlines() if ln and not ln.startswith("#")]
    return lines[-1].split(",")[-1].strip() if lines else ""


def hold_is_static(layer: Path, *, hold_offset: float, end_offset: float) -> bool:
    """动效层从 hold 起到退场前是否一帧不变（只比两帧：停住后和退场前）。"""
    a, b = _frame_md5(layer, hold_offset), _frame_md5(layer, end_offset)
    return bool(a) and a == b


def placement_checks(plan: dict[str, Any], b: dict[str, Any]) -> list[dict[str, str]]:
    out = []
    band = b.get("caption_band")
    face = b.get("face_box") if b.get("motion_placement") == "overlay-sides" else None
    for s in plan.get("shots") or []:
        _x, _y, w, h = s["src_rect"]
        p = fit((w, h), s["zone"])
        if band and p["y"] < band[1] and band[0] < p["y"] + p["h"]:
            out.append({"rule": "caption-band", "shot": s["id"], "detail": f"摆放 y{p['y']}–{p['y'] + p['h']} 进了字幕带"})
        if face:
            fx, fy, fw, fh = face
            if p["x"] < fx + fw and fx < p["x"] + p["w"] and p["y"] < fy + fh and fy < p["y"] + p["h"]:
                out.append({"rule": "covers-face", "shot": s["id"], "detail": f"摆放 {p} 盖到人脸"})
    return out


def contact_sheet(video: Path, times: list[float], out: Path, *, width: int = 480) -> None:
    """每个时刻一张缩略图，拼成一张总览（4 列）。"""
    tiles = []
    tmp = out.parent / f".{out.stem}-tiles"
    tmp.mkdir(parents=True, exist_ok=True)
    for i, t in enumerate(times):
        tile = tmp / f"{i:03d}.png"
        _ff(["-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(video), "-frames:v", "1", "-vf", f"scale={width}:-2", str(tile)])
        tiles.append(tile)
    cols = min(4, len(tiles)) or 1
    rows = (len(tiles) + cols - 1) // cols
    _ff(["-v", "error", "-y", "-framerate", "1", "-i", str(tmp / "%03d.png"), "-vf", f"tile={cols}x{rows}", "-frames:v", "1", str(out)])
    for tile in tiles:
        tile.unlink(missing_ok=True)
    tmp.rmdir()


def run(video: Path, plan: dict[str, Any], b: dict[str, Any], out: Path, *, expected_duration: float | None = None,
        contact: Path | None = None) -> dict[str, Any]:
    report = video_checks(video, expected_duration=expected_duration)
    report["placement"] = placement_checks(plan, b)
    holds = []
    for s in plan.get("shots") or []:
        if "hold" in s and s.get("layer"):
            ok = hold_is_static(Path(s["layer"]), hold_offset=s["hold"] - s["start"] + 0.05, end_offset=s["end"] - s["start"] - 0.4)
            holds.append({"shot": s["id"], "static": ok})
    report["hold_static"] = holds
    if contact and plan.get("shots"):
        contact_sheet(video, [(s["start"] + s["end"]) / 2 for s in plan["shots"]], contact)
        report["contact_sheet"] = str(contact)
    if report["placement"] or any(not h["static"] for h in holds):
        report["status"] = "fail"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("plan")
    ap.add_argument("brief")
    ap.add_argument("out")
    ap.add_argument("--contact")
    ap.add_argument("--expected-duration", type=float)
    a = ap.parse_args(argv[1:])
    plan = json.loads(Path(a.plan).read_text(encoding="utf-8"))
    report = run(Path(a.video), plan, brief_mod.load(Path(a.brief)), Path(a.out),
                 expected_duration=a.expected_duration, contact=Path(a.contact) if a.contact else None)
    print(json.dumps({k: report[k] for k in ("status", "duration", "black", "silence", "loudness", "placement", "hold_static")},
                     ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
