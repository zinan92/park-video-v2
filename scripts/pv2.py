#!/usr/bin/env python3
"""口播动效 v2：一条命令走完四步。所有文件在 <项目目录>/v2/ 下。

  pv2.py init    <项目> --video 粗剪.mov --srt source.srt   建 v2/，写 brief 模板（Park 填）
  pv2.py prep    <项目>                 SRT 对齐音频 → words.json
  pv2.py check   <项目>                 程序检查 plan.json（AI 写好方案后）
  pv2.py compare <项目> [--detach]      精品档：每个重点镜头和它的标杆左右对比 → v2/compare/（不低于标杆才出样片）
  pv2.py sample  <项目> [--detach]      渲染样片 → sample.mp4（精品档只渲重点镜头；和整条同一个渲染函数）
  pv2.py approve <项目> sample|final -m "Park 原话"
  pv2.py render  <项目> [--detach]      全部镜头 + 整条合成 + 终检 → final.mp4、qa.json、contact.jpg
  pv2.py qa      <项目>                 只重跑终检（不重渲）
  pv2.py status  <项目>                 现在在哪一步、进度多少、在等谁
  pv2.py evidence <项目> <清单.json>    工作台里他点过「要」的证据截图放进 v2/evidence/（方案的 Proof 卡只能用这些）
  pv2.py settings [<项目>]              全部设置（settings.yaml）+ 当前取值和来源，JSON；工作台用它画滑杆
  pv2.py set <项目>|default --json '{"density": "low"}'   改设置：写进项目 brief.yaml，或 Park 的默认值
  pv2.py catalog                        动效图鉴：每个组件的中文名、形式、努力程度、演示片段，JSON
  pv2.py gallery [组件名 ...]           重新渲染图鉴里组件的演示片段（gallery/；不写组件名就全部）
  pv2.py shotcraft                      Video-ShotCraft 全部样式卡的名字、一句话、分类、预览：Park 叫不出名字时翻它挑

进度：样片写 v2/sample-status.json，整条写 v2/status.json，都是 {state, stage, done, total, unit, percent}。
--detach 在独立进程组里跑：调它的 agent 退出也不会把渲染带走。
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import bench as bench_mod
import brief as brief_mod
import check as check_mod
import layers as layers_mod
import proof as proof_mod
import qa as qa_mod
import render as render_mod

ROOT = Path(__file__).resolve().parents[1]
GATES = ("sample", "final")


def _v2(project: Path) -> Path:
    return Path(project) / "v2"


def _json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def init(project: Path, *, video: str, srt: str | None) -> Path:
    d = _v2(project)
    d.mkdir(parents=True, exist_ok=True)
    (d / "project.json").write_text(json.dumps({"rough_cut": video, "srt": srt}, ensure_ascii=False), encoding="utf-8")
    b = d / "brief.yaml"
    if not b.exists():
        template = (ROOT / "brief.example.yaml").read_text(encoding="utf-8")
        b.write_text("# Park 填好后去掉每行前面的 #。AI 不猜这些。\n" + "\n".join("# " + ln if ln and not ln.startswith("#") else ln
                                                                       for ln in template.splitlines()) + "\n", encoding="utf-8")
    return d


def approve(project: Path, gate: str, *, message: str) -> dict[str, Any]:
    if gate not in GATES:
        raise ValueError(f"只能批准 {' / '.join(GATES)}")
    if not message.strip():
        raise ValueError("批准要带 Park 的原话")
    path = _v2(project) / "approvals.json"
    data = _json(path, {}) or {}
    data[gate] = {"by": "Park", "at": datetime.now().astimezone().isoformat(timespec="seconds"), "message": message.strip()}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return data[gate]


def summary(project: Path) -> dict[str, Any]:
    """工作台读这个：四步里在哪一步、真实进度、在等谁。"""
    d = _v2(project)
    out: dict[str, Any] = {"step": "准备", "percent": None, "waiting_for": None, "failed": False, "detail": "",
                           "sample": None, "final": None}
    for name in ("sample-status.json", "status.json"):
        st = _json(d / name) or {}
        if st.get("state") == "failed":
            out["failed"], out["detail"] = True, f"{name} 在 {st.get('stage')} 阶段失败"
    try:
        brief_mod.load(d / "brief.yaml")
    except (brief_mod.NeedsPark, OSError, ValueError) as e:  # ValueError：brief 里写了不认识的选项，比如 card: 毛玻璃
        out.update(waiting_for="Park 确认 brief", detail=out["detail"] or str(e))
        return out
    if not (d / "words.json").is_file():
        return {**out, "waiting_for": "跑 prep"}
    out["step"] = "方案"
    if not (d / "plan.json").is_file():
        return {**out, "waiting_for": "AI 写 plan.json"}
    approvals = _json(d / "approvals.json", {}) or {}
    if (d / "sample.mp4").is_file():
        out["sample"] = "v2/sample.mp4"
    if "sample" not in approvals:
        st = _json(d / "sample-status.json") or {}
        if st.get("state") == "rendering":
            return {**out, "percent": st.get("percent")}
        if out["sample"]:
            return {**out, "waiting_for": "Park 看样片"}
        try:
            b = brief_mod.load(d / "brief.yaml")
            missing = compare_missing(project, _json(d / "plan.json"), b)
        except (OSError, ValueError, KeyError):
            missing = []
        return {**out, "waiting_for": "和标杆对比（compare）" if missing else "跑 sample"}
    out["step"] = "渲染"
    st = _json(d / "status.json") or {}
    qa_ok = (_json(d / "qa.json") or {}).get("status") == "pass"
    if (d / "final.mp4").is_file() and qa_ok and st.get("state") == "done":
        out.update(step="终审", percent=100, final="v2/final.mp4")
        if "final" in approvals:
            return {**out, "step": "已交付"}
        return {**out, "waiting_for": "Park 看成片"}
    if st.get("state") == "rendering":
        return {**out, "percent": st.get("percent")}
    return {**out, "waiting_for": "跑 render"}


def _raw_brief(project: Path) -> dict[str, Any]:
    import yaml
    try:
        return yaml.safe_load((_v2(project) / "brief.yaml").read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return {}


def settings(project: Path | None = None) -> dict[str, Any]:
    """工作台画滑杆用：设置清单 + 每一项现在的值 + 值从哪来（repo / user / project）。"""
    import yaml
    sc = brief_mod.schema()
    repo = yaml.safe_load(brief_mod.DEFAULTS.read_text(encoding="utf-8")) or {}
    user = brief_mod._yaml(brief_mod.user_defaults_path())
    own = _raw_brief(project) if project else {}
    keys = [x["key"] for x in (sc.get("sliders") or []) + (sc.get("choices") or [])]
    if project:
        keys += [x["key"] for x in sc.get("per_video") or []]
    values, source = {}, {}
    for k in keys:
        for name, layer in (("project", own), ("user", user), ("repo", repo)):
            if k in layer:
                values[k], source[k] = layer[k], name
                break
    levels = {sl["key"]: {lv["value"]: lv.get("available", True) for lv in sl["levels"]} for sl in sc.get("sliders") or []}
    presets = [{**pr, "available": all(levels.get(k, {}).get(v, True) for k, v in pr["values"].items())} for pr in sc.get("presets") or []]
    return {"schema": {**sc, "presets": presets}, "values": values, "source": source,
            "components": [{"key": c["key"], "name": c["name"], "form": c["form"], "effort": c["effort"]} for c in catalog()]}


def _write_keys(path: Path, updates: dict[str, Any]) -> None:
    """改 yaml 里几个顶层字段，其余行（含注释）原样保留；没有的字段追加在末尾。"""
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    for key, val in updates.items():
        new = f"{key}: {json.dumps(val, ensure_ascii=False)}"
        at = next((i for i, ln in enumerate(lines) if ln.split("#")[0].rstrip().startswith(f"{key}:") and not ln.startswith(" ")), None)
        if at is None:
            lines.append(new)
            continue
        end = at + 1
        while end < len(lines) and (lines[end].startswith((" ", "\t", "-")) or not lines[end].strip()):
            if not lines[end].strip() and (end + 1 >= len(lines) or not lines[end + 1].startswith((" ", "-"))):
                break
            end += 1
        lines[at:end] = [new]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def set_values(target: str, updates: dict[str, Any]) -> dict[str, Any]:
    """target 是项目目录（写进它的 v2/brief.yaml）或 "default"（写进 Park 的默认值）。先全部校验，再写。"""
    for k, v in updates.items():
        brief_mod.check_value(k, v)
    if target == "default":
        path = brief_mod.user_defaults_path()
    else:
        path = _v2(Path(target)) / "brief.yaml"
        if not path.parent.is_dir():
            raise ValueError(f"{target} 还没有 v2/，先 init")
    _write_keys(path, updates)
    return {"written": str(path), "values": updates}


def catalog() -> list[dict[str, Any]]:
    """动效图鉴：组件库里每个组件（catalog.json）+ 演示片段（gallery/ 里有才给）。"""
    data = json.loads((ROOT / "motion" / "src" / "library" / "catalog.json").read_text(encoding="utf-8"))
    out = []
    for key, c in data.items():
        if key.startswith("_"):
            continue
        video, poster = ROOT / "gallery" / f"{key}.mp4", ROOT / "gallery" / f"{key}.jpg"
        out.append({"key": key, **c, "video": str(video) if video.is_file() else None, "poster": str(poster) if poster.is_file() else None})
    return out


SHOTCRAFT_ENV = "PV2_SHOTCRAFT"
# 默认用 Park 的私有快照（github.com/zinan92/video-shotcraft-snapshot，2026-09-07 版，原仓库已下线）；
# 没有快照时退回 skill 安装目录（会被「更新全部 skill」覆盖，不建议长期依赖）
SHOTCRAFT_SNAPSHOT = Path.home() / "work" / "video-shotcraft-snapshot"
SHOTCRAFT_INSTALLED = Path.home() / ".agents" / "skills" / "video-shotcraft"


def shotcraft_home() -> Path:
    if os.environ.get(SHOTCRAFT_ENV):
        return Path(os.environ[SHOTCRAFT_ENV]).expanduser()
    return SHOTCRAFT_SNAPSHOT if SHOTCRAFT_SNAPSHOT.is_dir() else SHOTCRAFT_INSTALLED


def shotcraft() -> list[dict[str, Any]]:
    """Video-ShotCraft 的全部样式卡（它自己的 gallery/api/library.json）：名字、一句话、适用、分类、
    海报图、预览视频本地有就给路径（预览是快照里在本机重渲的）。改编成我们的组件时按 name 找源码。"""
    home = shotcraft_home()
    lib = _json(home / "gallery" / "api" / "library.json") or {}
    cats = lib.get("categories") or {}
    adapted = {}
    for c in catalog():
        for name in c.get("shotcraft") or []:
            adapted.setdefault(name, []).append(c["key"])
    out = []
    for card in lib.get("cards") or []:
        poster = home / "gallery" / "media" / "poster" / f"{card['name']}.jpg"
        # 一张卡有几个样式时，取第一个有预览的
        keys = [st.get("key") for st in card.get("styles") or [] if st.get("key")] or [card["name"]]
        video = next((v for v in (home / "gallery" / "media" / f"{k}.mp4" for k in keys) if v.is_file()),
                     home / "gallery" / "media" / f"{keys[0]}.mp4")
        out.append({"name": card["name"], "summary": card.get("summary", ""), "use": card.get("use", ""),
                    "category": card.get("category", ""), "category_zh": (cats.get(card.get("category"), {}) or {}).get("zh", ""),
                    "poster": str(poster) if poster.is_file() else None,
                    "video": str(video) if video.is_file() else None,
                    "source": card.get("source", ""),
                    "adapted_as": adapted.get(card["name"], [])})
    return out


def _motion_mtime() -> float:
    """组件代码最近一次修改的时间：改了组件，旧的层就过期。"""
    src = ROOT / "motion" / "src"
    return max((p.stat().st_mtime for p in src.rglob("*.ts*")), default=0.0)


def find(words: list[dict[str, Any]], text: str) -> list[float]:
    """这句原话每一次被说出的时刻（秒）。写 plan.json 的 reveals / ats 时用。"""
    target = check_mod._clean(text)
    flat, owner = [], []
    for i, w in enumerate(words):
        for ch in check_mod._clean(w["w"]):
            flat.append(ch)
            owner.append(i)
    stream, hits, at = "".join(flat), [], -1
    while target and (at := stream.find(target, at + 1)) >= 0:
        hits.append(words[owner[at]]["start"])
    return hits


def layers_to_render(project: Path, shots: list[dict[str, Any]], b: dict[str, Any]) -> list[dict[str, Any]]:
    """层要重渲：文件不存在、渲染它的 props（方案 + 外观）变了、或组件代码改过。其余直接复用（样片渲过的镜头整条时不重渲）。"""
    d = _v2(project)
    code_m = _motion_mtime()
    out = []
    for s in shots:
        f = d / "layers" / f"{s['id']}.mov"
        want = json.loads(json.dumps(layers_mod.layer_props(s, check_mod._zone(s, b), layers_mod.style(b)), sort_keys=True))
        if not f.is_file() or f.stat().st_mtime < code_m or _json(layers_mod.props_file(f)) != want:
            out.append(s)
    return out


def _load(project: Path) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
    d = _v2(project)
    b = brief_mod.load(d / "brief.yaml")
    plan = _json(d / "plan.json")
    if plan is None:
        raise SystemExit("还没有 plan.json")
    meta = _json(d / "project.json", {})
    return d, b, plan, meta


def _checked(project: Path) -> tuple[Path, dict[str, Any], dict[str, Any], dict[str, Any]]:
    d, b, plan, meta = _load(project)
    found = check_mod.run(plan, _json(d / "words.json", {}), b, proof_mod.load(d))
    if found:
        print(json.dumps(found, ensure_ascii=False, indent=2))
        raise SystemExit("程序检查没过，先改 plan.json")
    return d, b, plan, meta


def _public(d: Path) -> Path | None:
    """证据截图目录：有就交给 Remotion 当 public 目录。"""
    return d / proof_mod.FOLDER if (d / proof_mod.FOLDER).is_dir() else None


def evidence(project: Path, manifest: Path) -> dict[str, Any]:
    """工作台给的证据清单（他点过「要」的）放进项目；brief 的「证据与素材」跟着改成 own / search（清单空就是 none）。"""
    items = json.loads(Path(manifest).read_text(encoding="utf-8"))
    d = _v2(project)
    out = proof_mod.put(d, items if isinstance(items, list) else [])
    _write_keys(d / "brief.yaml", {"evidence": proof_mod.level(out)})
    return {"items": out, "evidence": proof_mod.level(out)}


def _base(project: Path, meta: dict[str, Any]) -> str:
    return str((Path(project) / meta["rough_cut"]).resolve())


def do_prep(project: Path) -> None:
    d = _v2(project)
    brief_mod.load(d / "brief.yaml")
    meta = _json(d / "project.json", {})
    if not meta.get("srt"):
        raise SystemExit("没有 SRT：先在剪映导出 SRT 放进项目，再 init --srt")
    subprocess.run([sys.executable, str(ROOT / "scripts/align_srt.py"), _base(project, meta), str((Path(project) / meta["srt"]).resolve()),
                    str(d / "words.json")], check=True)


def shot_window(s: dict[str, Any]) -> tuple[float, float]:
    """一个镜头值得看的那段：出现前 0.4s 到停住后 1s。"""
    return round(max(0.0, s["start"] - 0.4), 3), round(min(s["end"], s.get("hold", s["end"]) + 1.0), 3)


def sample_windows(plan: dict[str, Any]) -> list[tuple[float, float]]:
    """样片要渲的时间段：重点镜头（key，旧方案的 sample）各取一段；没标就取开头 10 秒。"""
    marked = [s for s in plan["shots"] if check_mod.is_key(s)]
    if not marked:
        return [layers_mod.sample_window(plan)]
    return [shot_window(s) for s in sorted(marked, key=lambda x: x["start"])]


FONT = Path("/System/Library/Fonts/STHeiti Medium.ttc")  # 对比片上的「标杆 / 这版」字样；没有这个字体就不写字


def _label(text: str) -> str:
    if not FONT.is_file():
        return "null"
    safe = text.replace("\\", "").replace("'", "").replace(":", "：")
    return (f"drawtext=fontfile='{FONT}':text='{safe}':x=24:y=20:fontsize=40:fontcolor=white:"
            "box=1:boxcolor=black@0.55:boxborderw=12")


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def side_by_side(bench_clip: Path, ours: Path, out: Path, *, bench_label: str, strip: Path, frames: int = 6) -> None:
    """左标杆、右这版，各缩到 960 宽；短的那段停在最后一帧等长的；声音用这版的。再出一张两行的逐帧对比图。"""
    def dur(p: Path) -> float:
        r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)],
                           capture_output=True, text=True, check=True)
        return float(r.stdout.strip())
    da, db = dur(bench_clip), dur(ours)
    longest = max(da, db)
    pad = lambda d: f"tpad=stop_mode=clone:stop_duration={longest - d + 0.05:.3f}"
    _ffmpeg("-i", str(bench_clip), "-i", str(ours), "-filter_complex",
            f"[0:v]fps=30,scale=960:540,{pad(da)},{_label('标杆：' + bench_label)}[l];"
            f"[1:v]fps=30,scale=960:540,{pad(db)},{_label('这版')}[r];[l][r]hstack[v];[1:a]apad[a]",
            "-map", "[v]", "-map", "[a]", "-t", f"{longest:.3f}", "-c:v", "libx264", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(out))
    rows = []
    for i, (clip, d, name) in enumerate(((bench_clip, da, "标杆"), (ours, db, "这版"))):
        row = strip.with_name(f".{strip.stem}-{i}.png")
        _ffmpeg("-i", str(clip), "-vf", f"fps={frames / d:.4f},scale=480:270,tile={frames}x1,{_label(name)}", "-frames:v", "1", str(row))
        rows.append(row)
    _ffmpeg("-i", str(rows[0]), "-i", str(rows[1]), "-filter_complex", "vstack", str(strip))
    for r in rows:
        r.unlink(missing_ok=True)


def key_shots(plan: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted((s for s in plan["shots"] if check_mod.is_key(s)), key=lambda x: x["start"])


def do_compare(project: Path) -> Path:
    """精品档：每个重点镜头和它的标杆左右对比（视频 + 逐帧图），在 v2/compare/。AI 先看，不低于标杆才出样片。"""
    d, b, plan, meta = _checked(project)
    keys = key_shots(plan)
    if not keys:
        raise SystemExit("方案里没有重点镜头（key: true）")
    benches = {s["id"]: bench_mod.resolve(s["benchmark"]) for s in keys}
    out_dir = d / "compare"
    out_dir.mkdir(exist_ok=True)
    stale = [s for s in layers_to_render(project, plan["shots"], b) if check_mod.is_key(s)]
    layers_mod.render_layers(plan, b, d / "layers", status=None, only=stale, public=_public(d))
    rp = layers_mod.render_plan(plan, b, base=_base(project, meta), layer_dir=d / "layers")
    pairs = []
    for s in keys:
        bm = benches[s["id"]]
        ours, theirs = out_dir / f".ours-{s['id']}.mp4", out_dir / f".bench-{s['id']}.mp4"
        a, z = shot_window(s)
        render_mod.render(rp, ours, None, start=a, end=z)
        _ffmpeg("-ss", str(bm["start"]), "-to", str(bm["end"]), "-i", bm["video"], "-c:v", "libx264", "-crf", "18", "-c:a", "aac", str(theirs))
        pair = out_dir / f"{s['id']}.mp4"
        side_by_side(theirs, ours, pair, bench_label=bm["name"], strip=out_dir / f"{s['id']}.jpg")
        ours.unlink(missing_ok=True)
        theirs.unlink(missing_ok=True)
        pairs.append(pair)
    lst = out_dir / ".list.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in pairs), encoding="utf-8")
    _ffmpeg("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(d / "compare.mp4"))
    lst.unlink(missing_ok=True)
    return d / "compare.mp4"


def compare_missing(project: Path, plan: dict[str, Any], b: dict[str, Any]) -> list[str]:
    """精品档出样片前：哪些重点镜头还没和标杆对比过，或对比之后又改过（层要重渲 / 比对比片新）。"""
    if b.get("effort") not in ("c", "d"):
        return []
    d = _v2(project)
    stale = {s["id"] for s in layers_to_render(project, plan["shots"], b)}
    out = []
    for s in key_shots(plan):
        pair, layer = d / "compare" / f"{s['id']}.mp4", d / "layers" / f"{s['id']}.mov"
        if s["id"] in stale or not pair.is_file() or pair.stat().st_mtime < layer.stat().st_mtime:
            out.append(s["id"])
    return out


def do_sample(project: Path) -> Path:
    d, b, plan, meta = _checked(project)
    missing = compare_missing(project, plan, b)
    if missing:
        raise SystemExit(f"重点镜头 {'、'.join(missing)} 还没和标杆对比（或对比后又改过）：先跑 compare，看过不低于标杆再出样片")
    status = d / "sample-status.json"
    windows = sample_windows(plan)
    stale = layers_to_render(project, plan["shots"], b)
    need = [s for s in stale if any(s["start"] < z and a < s["end"] for a, z in windows)]
    layers_mod.render_layers(plan, b, d / "layers", status=status, only=need, weight=(0, 60), public=_public(d))
    rp = layers_mod.render_plan(plan, b, base=_base(project, meta), layer_dir=d / "layers")
    (d / "render-plan.json").write_text(json.dumps(rp, ensure_ascii=False, indent=2), encoding="utf-8")
    out = d / "sample.mp4"
    if len(windows) == 1:
        render_mod.render(rp, out, status, start=windows[0][0], end=windows[0][1], weight=(60, 100))
        return out
    parts = []
    step = 40 / len(windows)
    for i, (a, z) in enumerate(windows):
        part = d / f".sample-part-{i}.mp4"
        render_mod.render(rp, part, status, start=a, end=z, weight=(int(60 + step * i), int(60 + step * (i + 1))))
        parts.append(part)
    lst = d / ".sample-parts.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(out)], check=True)
    for p in parts + [lst]:
        p.unlink(missing_ok=True)
    render_mod.write_status(status, "done", 1, 1, stage="composite", weight=(60, 100))
    return out


def do_render(project: Path) -> Path:
    d, b, plan, meta = _checked(project)
    if "sample" not in (_json(d / "approvals.json", {}) or {}):
        raise SystemExit("Park 还没批样片，不渲染整条")
    status = d / "status.json"
    layers_mod.render_layers(plan, b, d / "layers", status=status, only=layers_to_render(project, plan["shots"], b), weight=(0, 45),
                             public=_public(d))
    rp = layers_mod.render_plan(plan, b, base=_base(project, meta), layer_dir=d / "layers")
    (d / "render-plan.json").write_text(json.dumps(rp, ensure_ascii=False, indent=2), encoding="utf-8")
    out = d / "final.mp4"
    render_mod.render(rp, out, status, weight=(45, 90))
    do_qa(project)
    return out


def do_qa(project: Path) -> dict[str, Any]:
    """终检（render 末尾自动跑；修了检查本身之后也可以单独重跑，不用重渲）。"""
    d, b, plan, _meta = _load(project)
    status = d / "status.json"
    rp = _json(d / "render-plan.json")
    if rp is None or not (d / "final.mp4").is_file():
        raise SystemExit("还没有整条成片，先 render")
    render_mod.write_status(status, "rendering", 0, 1, stage="qa", weight=(90, 100), unit="checks")
    report = qa_mod.run(d / "final.mp4", rp, b, d / "qa.json", expected_duration=plan["duration"], contact=d / "contact.jpg")
    render_mod.write_status(status, "done" if report["status"] == "pass" else "failed", 1, 1, stage="qa", weight=(90, 100), unit="checks")
    return report


def _detach(argv: list[str], project: Path) -> None:
    args = [sys.executable, os.path.abspath(__file__), *[a for a in argv[1:] if a != "--detach"]]
    log = open(_v2(project) / "run.log", "a")
    subprocess.Popen(args, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True, cwd=str(ROOT))
    print("已在后台启动；进度：python3 scripts/pv2.py status", project)


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] in ("settings", "set", "catalog", "gallery", "shotcraft"):
        return _main_settings(argv)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("init", "prep", "check", "find", "compare", "sample", "approve", "render", "qa", "status", "evidence"))
    ap.add_argument("project")
    ap.add_argument("gate", nargs="?")
    ap.add_argument("--video")
    ap.add_argument("--srt")
    ap.add_argument("-m", "--message", default="")
    ap.add_argument("--detach", action="store_true")
    a = ap.parse_args(argv[1:])
    project = Path(a.project).expanduser()
    if a.cmd == "init":
        print(init(project, video=a.video, srt=a.srt))
    elif a.cmd == "prep":
        do_prep(project)
    elif a.cmd == "check":
        d, b, plan, _ = _load(project)
        found = check_mod.run(plan, _json(d / "words.json", {}), b, proof_mod.load(d))
        print(json.dumps(found, ensure_ascii=False, indent=2))
        lo, hi = brief_mod.coverage_range(b)
        print(f"动效占 {check_mod.coverage(plan, b):.0%}（密度 {b.get('density')}：{lo:.0%}–{hi:.0%}）", file=sys.stderr)
        return 1 if found else 0
    elif a.cmd == "find":
        words = (_json(_v2(project) / "words.json", {}) or {}).get("words") or []
        print(json.dumps({"text": a.gate, "spoken_at": find(words, a.gate or "")}, ensure_ascii=False))
    elif a.cmd in ("compare", "sample", "render"):
        if a.detach:
            _detach(argv, project)
            return 0
        print({"compare": do_compare, "sample": do_sample, "render": do_render}[a.cmd](project))
    elif a.cmd == "qa":
        report = do_qa(project)
        print(json.dumps({k: report[k] for k in ("status", "placement", "hold_static")}, ensure_ascii=False, indent=2))
        return 0 if report["status"] == "pass" else 1
    elif a.cmd == "approve":
        print(json.dumps(approve(project, a.gate or "", message=a.message), ensure_ascii=False))
    elif a.cmd == "evidence":
        print(json.dumps(evidence(project, Path(a.gate or "")), ensure_ascii=False, indent=2))
    elif a.cmd == "status":
        print(json.dumps(summary(project), ensure_ascii=False, indent=2))
    return 0


def _main_settings(argv: list[str]) -> int:
    cmd, rest = argv[1], argv[2:]
    if cmd == "settings":
        print(json.dumps(settings(Path(rest[0]).expanduser() if rest else None), ensure_ascii=False, indent=2))
    elif cmd == "catalog":
        print(json.dumps(catalog(), ensure_ascii=False, indent=2))
    elif cmd == "shotcraft":
        print(json.dumps(shotcraft(), ensure_ascii=False, indent=2))
    elif cmd == "gallery":
        import gallery
        for path in gallery.render_all(rest or None):
            print(path)
    else:
        if len(rest) != 3 or rest[1] != "--json":
            raise SystemExit("用法：pv2.py set <项目>|default --json '{\"density\": \"low\"}'")
        target = rest[0] if rest[0] == "default" else str(Path(rest[0]).expanduser())
        try:
            print(json.dumps(set_values(target, json.loads(rest[2])), ensure_ascii=False))
        except ValueError as e:
            print(json.dumps({"error": str(e)}, ensure_ascii=False))
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
