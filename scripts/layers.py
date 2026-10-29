"""逐个镜头渲染透明动效层（Remotion），并生成 render.py 用的 render-plan。

每个镜头的画布就是它要放的区域（brief 推出的 left / right，或自定义 {x,y,w,h}），所以层很小、渲染很快。
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from check import _zone, is_camera
from render import write_status

MOTION = Path(__file__).resolve().parents[1] / "motion"
PASS = "ShotCraft"  # ShotCraft 直通：原卡在 1920×1080 透明画布上渲（motion/src/shotcraft/），合成时裁内容框、放进区域
PANEL = {"dark": (20, 22, 28, 224), "light": (244, 241, 234, 247)}  # 直通卡背后垫的卡片底：字是浅的垫深底，字是深的垫浅底
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


def pass_props(shot: dict[str, Any]) -> dict[str, Any]:
    """直通卡的渲染参数：哪张卡、从镜头开头第几帧开始播（他说出这句话的时刻 at）、镜头几帧、字的对照表。"""
    p = shot.get("props") or {}
    return {"card": p.get("card"), "lead": max(0, round((p.get("at", shot["start"]) - shot["start"]) * 30)),
            "frames": max(1, round((shot["end"] - shot["start"]) * 30)), "texts": p.get("texts") or {},
            **({"look": p["look"]} if p.get("look") else {})}


def remotion_cmd(shot: dict[str, Any], zone: dict[str, int], out: Path, look: dict[str, Any] | None = None,
                 public: Path | None = None, scale: float = 1.0) -> list[str]:
    """public：证据截图所在的目录（项目的 v2/evidence/），Proof 卡用 staticFile 从这里读图。
    scale：原片是 canvas 的几倍（4K 是 2）。组件照 canvas 尺寸排版，Remotion 按倍数渲得更大，字不糊。"""
    passing = shot.get("component") == PASS
    props = pass_props(shot) if passing else layer_props(shot, zone, look)
    return ["npx", "remotion", "render", "src/index.ts", "ShotcraftPass" if passing else "Shot", str(out), "--codec=prores", "--prores-profile=4444",
            "--pixel-format=yuva444p10le", "--image-format=png", "--muted", "--log=error",
            *([f"--public-dir={public}"] if public else []), *([f"--scale={scale}"] if scale != 1 else []),
            "--props=" + json.dumps(props, ensure_ascii=False)]


def render_layers(plan: dict[str, Any], brief: dict[str, Any], layer_dir: Path, *, status: Path | None,
                  only: list[dict[str, Any]] | None = None, weight: tuple[int, int] = (0, 100), public: Path | None = None,
                  scale: float = 1.0) -> list[Path]:
    layer_dir.mkdir(parents=True, exist_ok=True)
    shots = [s for s in (only if only is not None else plan["shots"]) if not is_camera(s)]  # 运镜不渲层，合成时直接推原画面
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
        if s.get("component") == PASS:
            box_file(out).write_text(json.dumps(measure_layer(out, s)), encoding="utf-8")
        outs.append(out)
    write_status(status, "rendering", len(shots), len(shots), stage="layers", weight=weight, unit="shots")
    return outs


def box_file(layer: Path) -> Path:
    return layer.with_suffix(".box.json")


def measure_layer(layer: Path, shot: dict[str, Any]) -> dict[str, Any]:
    """直通卡渲好以后量一次：内容实际占画面哪一块（换成他的字以后比原卡窄或宽都按实际的裁），字是浅色还是深色（决定垫什么底）。"""
    import tempfile

    from PIL import Image

    import shotcraft

    span = shot["end"] - shot["start"]
    alphas, light = [], []
    with tempfile.TemporaryDirectory() as tmp:
        for k, t in enumerate((span * 0.45, span * 0.75, max(0.0, span - 0.4))):
            png = Path(tmp) / f"{k}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", str(layer), "-frames:v", "1", "-vf", "format=rgba", str(png)],
                           check=True)
            im = Image.open(png).convert("RGBA")
            alphas.append(im.split()[3])
            px = [p for p in im.resize((im.width // 8, im.height // 8)).getdata() if p[3] > 200]
            light += [(0.299 * r + 0.587 * g + 0.114 * b) / 255 for r, g, b, _a in px]
    box, cover = shotcraft._bbox(alphas)
    return {"box": box, "cover": cover, "ink": "light" if light and sum(light) / len(light) > 0.55 else "dark"}


def render_plan(plan: dict[str, Any], brief: dict[str, Any], *, base: str, layer_dir: Path, scale: float = 1.0,
                captions: str | None = None) -> dict[str, Any]:
    """scale ≠ 1（4K 原片配 1920×1080 的 canvas）：区域和层都换算成原片像素，render.py 照原片坐标叠，成片保住原分辨率。"""
    glass = GLASS_ALPHA if brief.get("card") == "glass" else None
    shots = []
    for s in [x for x in plan["shots"] if not is_camera(x)]:
        z = _zone(s, brief)
        if s.get("component") == PASS:
            shots.append(_pass_shot(s, z, brief, layer_dir, scale))
            continue
        if scale == 1:
            w, h = round(z["w"] / 2) * 2, round(z["h"] / 2) * 2
        else:  # Remotion --scale 出来的层是 w·scale × h·scale；往下取偶数，裁的不会超出层
            w, h = int(z["w"] * scale) // 2 * 2, int(z["h"] * scale) // 2 * 2
            z = {k: round(v * scale) for k, v in z.items()}
        shots.append({"id": s["id"], "start": s["start"], "end": s["end"], "hold": s.get("hold", s["end"]),
                      "layer": str(layer_dir / f"{s['id']}.mov"), "src_rect": [0, 0, w, h], "zone": z,
                      "glass": glass, **({"blur": round(24 * scale)} if scale != 1 else {})})
    cw, ch = brief["canvas"]
    fx, fy, fw, fh = brief.get("face_box") or [0, 0, cw, ch]  # noqa: E741
    camera = [{"id": c["id"], "start": c["start"], "end": c["end"], "move": c["move"], "from": c.get("from", 1.0), "to": c["to"],
               "vignette": c.get("vignette", 0.5), "origin": [round((fx + fw / 2) * scale), round((fy + fh / 2) * scale)]}
              for c in plan["shots"] if is_camera(c)]  # 推向人脸中心（没有 face_box 就是画面中心）
    return {"base": base, **({"camera": camera} if camera else {}), "canvas": [round(cw * scale), round(ch * scale)] if scale != 1 else brief["canvas"], "scale": scale,
            "shots": shots, **({"captions": captions} if captions else {})}


def _pass_shot(s: dict[str, Any], z: dict[str, int], brief: dict[str, Any], layer_dir: Path, scale: float) -> dict[str, Any]:
    """直通卡进合成：只裁量出来的内容框（四周留一点边），等比放进区域；brief 要卡片底就在背后垫一块（全屏镜头不垫）。"""
    layer = layer_dir / f"{s['id']}.mov"
    try:
        m = json.loads(box_file(layer).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        m = {"box": None, "ink": "dark"}
    x, y, w, h = m.get("box") or [0, 0, 1920, 1080]
    pad = 36
    x, y = max(0, x - pad), max(0, y - pad)
    w, h = min(1920 - x, w + 2 * pad), min(1080 - y, h + 2 * pad)
    rect = [round(v * scale) for v in (x, y, w, h)]
    zone = {k: round(v * scale) for k, v in z.items()}
    full = s.get("zone") == "full"
    panel = None if full or brief.get("card") == "none" else list(PANEL["dark" if m.get("ink") == "light" else "light"])
    return {"id": s["id"], "start": s["start"], "end": s["end"], "hold": s.get("hold", s["end"]), "layer": str(layer),
            "src_rect": [rect[0], rect[1], rect[2] // 2 * 2, rect[3] // 2 * 2], "zone": zone, "glass": None,
            **({"panel": panel, "radius": round(30 * scale)} if panel else {})}
