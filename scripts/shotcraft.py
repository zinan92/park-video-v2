"""ShotCraft 直通：把 Video-ShotCraft 原仓库的镜头卡，不改源码、批量变成能叠在人脸两侧的动效。

SOP（每次 ShotCraft 更新跑一遍，不用一张张重做）：
  1. sync：把原仓库拉到本机缓存（~/.cache/park-video-v2/video-shotcraft），记下版本，生成注册表；
  2. measure：每张卡在透明画布上渲几帧（舞台件、铺满画面的底色、品牌标志都去掉，见 motion/src/shotcraft/），
     量出内容实际占画面哪一块（合成时只裁这一块）、去底以后还剩不剩东西、能放进侧边还是只能全屏，
     列出卡上显示的字（文字槽：方案里用他的原话替换），写进 manifest.json；
  3. Park 看图鉴片段点「要 / 只全屏 / 不要」（manifest 的 verdict），没点过的按自动分类先用。

用法：
  python3 scripts/shotcraft.py sync               拉最新、生成注册表，报告新增和下架的卡
  python3 scripts/shotcraft.py measure [卡 ...]   量卡写 manifest（不写卡名就量全部；约每张 10 秒）
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MOTION = ROOT / "motion"
UPSTREAM = "https://github.com/Vincentwei1021/video-shotcraft"
REGISTRY = MOTION / "src" / "shotcraft" / "registry.generated.ts"
BRAND_FILE = MOTION / "src" / "shotcraft" / "brand.generated.ts"
MANIFEST = MOTION / "src" / "shotcraft" / "manifest.json"
LOADER = MOTION / "src" / "shotcraft" / "slot-loader.cjs"
FRAME = (1920, 1080)
SIDE = (560, 720)  # 侧边区域里卡片内容大约能用的宽高（1080p）
SIDE_MIN_SCALE = 0.35  # 内容缩进侧边后至少是原来的 0.4 倍，再小字就看不清，只能全屏用
FORMS = {"typography": "text", "data": "chart", "rhythm": "text", "opening": "text", "outro": "text"}
CSS_WORDS = re.compile(r"^(absolute|relative|fixed|hidden|visible|nowrap|center|left|right|top|bottom|flex|block|none|auto|inherit|"
                       r"transparent|pre|normal|bold|italic|uppercase|row|column|word|char|line|blur|fade|ease\w*|linear|screen|"
                       r"multiply|overlay|soft-light|cover|contain|pointer|both|forwards|text|clip|round|butt|sans|serif|mono|start|end|"
                       r"middle|baseline|wrap|space-\w+|break-\w+|preserve-3d|border-box|content-box)$")


def repo() -> Path:
    return Path(os.environ.get("PV2_SHOTCRAFT_REPO") or Path.home() / ".cache" / "park-video-v2" / "video-shotcraft")


def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(repo()), *args], capture_output=True, text=True, check=True).stdout.strip()


def kebab(name: str) -> str:
    """BraceExpand → brace-expand，Basic3DScene → basic-3d-scene（和 ShotCraft 的样式名一致）。"""
    s = re.sub(r"([a-z])([A-Z0-9])", r"\1-\2", name)
    return re.sub(r"([0-9A-Z])([A-Z][a-z])", r"\1-\2", s).lower()


def cards(home: Path | None = None) -> list[dict[str, Any]]:
    """原仓库 references/shots 里的每张卡，和它「参考实现」里的每个 demo 组件（一张卡可能有几式）。"""
    home = home or repo()
    out = []
    for md in sorted((home / "references" / "shots").glob("*/*.md")):
        text = md.read_text(encoding="utf-8")
        head = dict(re.findall(r"^(\S+?):\s*(.+)$", text.split("---")[1], re.M)) if text.startswith("---") else {}
        ref = text.split("## 参考实现", 1)[1] if "## 参考实现" in text else ""
        folder = re.search(r"(demos/[\w./-]+?)/?\s*$", ref.strip().splitlines()[0]) if ref.strip() else None
        if not folder:
            continue
        styles = []
        for tsx in sorted((home / folder.group(1)).glob("*.tsx")):
            src = tsx.read_text(encoding="utf-8")
            comp = re.findall(r"export const (\w+): React\.FC", src)
            dur = re.findall(r"export const (\w+_DURATION)\s*=\s*(\d+)", src)
            if comp and dur:
                styles.append({"key": kebab(comp[0]), "component": comp[0], "duration_name": dur[0][0], "frames": int(dur[0][1]),
                               "file": str(tsx.relative_to(home / "demos"))})
        if styles:
            out.append({"name": head.get("name", md.stem), "summary": head.get("一句话", ""), "use": head.get("适用", ""),
                        "category": md.parent.name, "styles": styles})
    return out


def write_registry(all_cards: list[dict[str, Any]]) -> Path:
    imports, rows = [], []
    for i, st in enumerate(s for c in all_cards for s in c["styles"]):
        imports.append(f"import {{ {st['component']} as C{i}, {st['duration_name']} as D{i} }} from '@sc-demos/{st['file'][:-4]}';")
        rows.append(f"  {json.dumps(st['key'])}: {{ C: C{i}, D: D{i} }},")
    REGISTRY.write_text("// @ts-nocheck 生成的文件（scripts/shotcraft.py sync），路径别名在 remotion.config.ts 里\nimport React from 'react';\n"
                        + "\n".join(imports) + "\nexport const REGISTRY: Record<string, { C: React.FC; D: number }> = {\n" + "\n".join(rows) + "\n};\n",
                        encoding="utf-8")
    return REGISTRY


def manifest() -> dict[str, Any]:
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"rev": None, "styles": {}}


def sync() -> dict[str, Any]:
    """拉原仓库最新（没有就 clone），生成注册表；报告和上次量过的相比新增、下架了哪些。"""
    if (repo() / ".git").is_dir():
        _git("pull", "-q", "--ff-only")
    else:
        repo().parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", UPSTREAM, str(repo())], check=True)
    all_cards = cards()
    write_registry(all_cards)
    BRAND_FILE.write_text("// 生成的文件（scripts/shotcraft.py sync）：原卡共用的品牌字，渲染时默认换成空\nexport const BRAND_TEXT: string[] = "
                          + json.dumps(brand_text(), ensure_ascii=False) + ";\n", encoding="utf-8")
    now = {s["key"] for c in all_cards for s in c["styles"]}
    had = set(manifest().get("styles") or {})
    return {"rev": _git("rev-parse", "--short", "HEAD"), "cards": len(all_cards), "styles": len(now),
            "added": sorted(now - had), "removed": sorted(had - now)}


def _display(t: str) -> bool:
    """像是给人看的字：有汉字，或者有字母且不是样式值、字体名、颜色、SVG 滤镜名、单个字母、驼峰标识符。"""
    if re.search(r"[\u4e00-\u9fff]", t):
        return True
    return bool(re.search(r"[A-Za-z]{2}", t)) and not (
        CSS_WORDS.match(t) or re.search(r"[#%(){};:=<>\"/\\]|-?\d*\.?\d+(em|px|deg|ms|s)\b|^\.", t)
        or re.fullmatch(r"[a-z]+(-[a-z0-9]+)*", t) or re.fullmatch(r"[A-Za-z]*[a-z][A-Z][A-Za-z]*", t)
        or re.search(r"\.(png|jpe?g|mp4|svg|com|io)\b", t))


def _strings(file: Path) -> list[str]:
    js = f"const l=require({json.dumps(str(LOADER))});const fs=require('fs');process.stdout.write(JSON.stringify(l.list(fs.readFileSync({json.dumps(str(file))},'utf8'),{json.dumps(str(file))})))"
    return json.loads(subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True, cwd=MOTION).stdout or "[]")


def brand_text(home: Path | None = None) -> list[str]:
    """原卡共用的品牌字（video-shotcraft、Shotcraft、宣传语）：渲染时默认换成空，方案可以拿它当标题槽换成他的话。"""
    file = (home or repo()) / "demos" / "_fixtures" / "Brand.tsx"
    if not file.is_file():
        return []
    return sorted({"video-shotcraft"} | {t.strip() for t in _strings(file) if t.strip() and _display(t.strip()) and "github" not in t})


def slots(file: Path) -> list[dict[str, Any]]:
    """卡上显示的字（原卡里经过 __scT 的字里，排除样式值、颜色、路径这些）：方案里按原文替换成他的话。"""
    out, seen = [], set()
    for s in _strings(file):
        t = s.strip()
        if not t or t in seen or not _display(t):
            continue
        seen.add(t)
        out.append({"text": t, "em": em(t)})
    return out


def _bbox(alpha_frames: list[Any]) -> tuple[list[int] | None, float]:
    """几帧 alpha 合起来：内容框（去掉两边各 1% 的零星像素，比如角落的小标签）和覆盖率。"""
    from PIL import ImageChops

    union = alpha_frames[0]
    for a in alpha_frames[1:]:
        union = ImageChops.lighter(union, a)
    mask = union.point(lambda v: 255 if v > 12 else 0)
    w, h = mask.size
    data = mask.load()
    cols = [sum(1 for y in range(0, h, 2) if data[x, y]) for x in range(0, w, 2)]
    rows = [sum(1 for x in range(0, w, 2) if data[x, y]) for y in range(0, h, 2)]
    total = sum(cols)
    if total == 0:
        return None, 0.0

    def span(profile: list[int]) -> tuple[int, int]:
        acc, lo, hi = 0, 0, len(profile) - 1
        for i, v in enumerate(profile):
            acc += v
            if acc > total * 0.003:
                lo = i
                break
        acc = 0
        for i in range(len(profile) - 1, -1, -1):
            acc += profile[i]
            if acc > total * 0.003:
                hi = i
                break
        return lo * 2, hi * 2 + 2

    (x0, x1), (y0, y1) = span(cols), span(rows)
    return [x0, y0, x1 - x0, y1 - y0], round(total * 4 / (w * h), 4)


def classify(box: list[int] | None, cover: float) -> str:
    """side：缩进人脸旁边还看得清；full：只能全屏用（短暂盖住人脸）；skip：去底以后什么都不剩（效果就是背景本身）。"""
    if box is None or cover < 0.002:
        return "skip"
    scale = min(SIDE[0] / box[2], SIDE[1] / box[3], 1.0)
    return "side" if scale >= SIDE_MIN_SCALE else "full"


def measure(only: list[str] | None = None) -> dict[str, Any]:
    from PIL import Image

    data = manifest()
    data["rev"] = _git("rev-parse", "--short", "HEAD")
    styles = data.setdefault("styles", {})
    todo = [(c, s) for c in cards() for s in c["styles"] if not only or s["key"] in only or c["name"] in only]
    with tempfile.TemporaryDirectory() as tmp:
        bundle = Path(tmp) / "bundle"
        subprocess.run(["npx", "remotion", "bundle", "src/index.ts", f"--out-dir={bundle}", "--log=error"], cwd=MOTION, check=True,
                       capture_output=True)
        for c, s in todo:
            frames = [int(s["frames"] * k) for k in (0.35, 0.7)] + [s["frames"] - 1]
            alphas = []
            for f in frames:
                png = Path(tmp) / f"{s['key']}-{f}.png"
                r = subprocess.run(["npx", "remotion", "still", str(bundle), "ShotcraftPass", str(png), f"--frame={f}", "--image-format=png",
                                    "--props=" + json.dumps({"card": s["key"], "lead": 0, "frames": s["frames"]}), "--log=error"],
                                   cwd=MOTION, capture_output=True, text=True)
                if r.returncode == 0 and png.is_file():
                    alphas.append(Image.open(png).convert("RGBA").split()[3])
            box, cover = _bbox(alphas) if alphas else (None, 0.0)
            src = (repo() / "demos" / s["file"]).read_text(encoding="utf-8")
            old = styles.get(s["key"]) or {}
            styles[s["key"]] = {"card": c["name"], "category": c["category"], "form": FORMS.get(c["category"], "diagram"),
                                "summary": c["summary"], "file": s["file"], "frames": s["frames"], "box": box, "cover": cover,
                                "auto": classify(box, cover) if alphas else "skip", "verdict": old.get("verdict"),
                                "slots": slots(repo() / "demos" / s["file"]), "looks": "_fixtures/Look" in src,
                                "error": None if alphas else "渲染失败"}
            print(s["key"], styles[s["key"]]["auto"], box, flush=True)
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return data


def em(text: str) -> float:
    """一段字大约占几个字宽：汉字 1，英文、数字约 0.6。"""
    return round(sum(0.6 if ord(ch) < 256 else 1 for ch in text), 1)


def brand_text_cached() -> list[str]:
    """品牌字（sync 时生成在 brand.generated.ts 里）；没同步过就是空的。"""
    try:
        return json.loads(BRAND_FILE.read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";"))
    except (OSError, ValueError, IndexError):
        return []


def usable(key: str) -> str:
    """这张卡现在能怎么用：Park 点过就听他的，没点过按自动分类。"""
    st = (manifest().get("styles") or {}).get(key) or {}
    return st.get("verdict") or st.get("auto") or "unknown"


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[1] not in ("sync", "measure"):
        print(__doc__)
        return 2
    if argv[1] == "sync":
        print(json.dumps(sync(), ensure_ascii=False, indent=2))
    else:
        data = measure(argv[2:] or None)
        n = {k: sum(1 for s in data["styles"].values() if s["auto"] == k) for k in ("side", "full", "skip")}
        print(json.dumps({"rev": data["rev"], **n}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
