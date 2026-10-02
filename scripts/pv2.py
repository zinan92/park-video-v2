#!/usr/bin/env python3
"""口播动效 v2：一条命令走完四步。所有文件在 <项目目录>/v2/ 下。

  pv2.py init    <项目> --video 粗剪.mov --srt source.srt   建 v2/，写 brief 模板（Park 填）
  pv2.py prep    <项目>                 SRT 对齐音频 → words.json
  pv2.py check   <项目>                 程序检查 plan.json（AI 写好方案后）
  pv2.py sample  <项目> [--detach]      渲染一段 10 秒样片 → sample.mp4（和整条同一个渲染函数）
  pv2.py approve <项目> sample|final -m "Park 原话"
  pv2.py render  <项目> [--detach]      全部镜头 + 整条合成 + 终检 → final.mp4、qa.json、contact.jpg
  pv2.py status  <项目>                 现在在哪一步、进度多少、在等谁

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

import brief as brief_mod
import check as check_mod
import layers as layers_mod
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
    except (brief_mod.NeedsPark, OSError) as e:
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
        return {**out, "waiting_for": "Park 看样片" if out["sample"] else "跑 sample"}
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


def layers_to_render(project: Path, shots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """层文件不存在、或比 plan.json / 组件代码旧，就要重渲；其余直接复用（样片渲过的镜头整条时不重渲）。"""
    d = _v2(project)
    plan_m = max((d / "plan.json").stat().st_mtime, _motion_mtime())
    out = []
    for s in shots:
        f = d / "layers" / f"{s['id']}.mov"
        if not f.is_file() or f.stat().st_mtime < plan_m:
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
    found = check_mod.run(plan, _json(d / "words.json", {}), b)
    if found:
        print(json.dumps(found, ensure_ascii=False, indent=2))
        raise SystemExit("程序检查没过，先改 plan.json")
    return d, b, plan, meta


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


def do_sample(project: Path) -> Path:
    d, b, plan, meta = _checked(project)
    status = d / "sample-status.json"
    a, z = layers_mod.sample_window(plan)
    need = [s for s in layers_mod.shots_between(plan, a, z) if s in layers_to_render(project, plan["shots"])]
    layers_mod.render_layers(plan, b, d / "layers", status=status, only=need, weight=(0, 60))
    rp = layers_mod.render_plan(plan, b, base=_base(project, meta), layer_dir=d / "layers")
    (d / "render-plan.json").write_text(json.dumps(rp, ensure_ascii=False, indent=2), encoding="utf-8")
    out = d / "sample.mp4"
    render_mod.render(rp, out, status, start=a, end=z, weight=(60, 100))
    return out


def do_render(project: Path) -> Path:
    d, b, plan, meta = _checked(project)
    if "sample" not in (_json(d / "approvals.json", {}) or {}):
        raise SystemExit("Park 还没批样片，不渲染整条")
    status = d / "status.json"
    layers_mod.render_layers(plan, b, d / "layers", status=status, only=layers_to_render(project, plan["shots"]), weight=(0, 45))
    rp = layers_mod.render_plan(plan, b, base=_base(project, meta), layer_dir=d / "layers")
    (d / "render-plan.json").write_text(json.dumps(rp, ensure_ascii=False, indent=2), encoding="utf-8")
    out = d / "final.mp4"
    render_mod.render(rp, out, status, weight=(45, 90))
    render_mod.write_status(status, "rendering", 0, 1, stage="qa", weight=(90, 100), unit="checks")
    report = qa_mod.run(out, rp, b, d / "qa.json", expected_duration=plan["duration"], contact=d / "contact.jpg")
    render_mod.write_status(status, "done" if report["status"] == "pass" else "failed", 1, 1, stage="qa", weight=(90, 100), unit="checks")
    return out


def _detach(argv: list[str], project: Path) -> None:
    args = [sys.executable, os.path.abspath(__file__), *[a for a in argv[1:] if a != "--detach"]]
    log = open(_v2(project) / "run.log", "a")
    subprocess.Popen(args, stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True, cwd=str(ROOT))
    print("已在后台启动；进度：python3 scripts/pv2.py status", project)


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=("init", "prep", "check", "find", "sample", "approve", "render", "status"))
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
        found = check_mod.run(plan, _json(d / "words.json", {}), b)
        print(json.dumps(found, ensure_ascii=False, indent=2))
        return 1 if found else 0
    elif a.cmd == "find":
        words = (_json(_v2(project) / "words.json", {}) or {}).get("words") or []
        print(json.dumps({"text": a.gate, "spoken_at": find(words, a.gate or "")}, ensure_ascii=False))
    elif a.cmd in ("sample", "render"):
        if a.detach:
            _detach(argv, project)
            return 0
        print((do_sample if a.cmd == "sample" else do_render)(project))
    elif a.cmd == "approve":
        print(json.dumps(approve(project, a.gate or "", message=a.message), ensure_ascii=False))
    elif a.cmd == "status":
        print(json.dumps(summary(project), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
