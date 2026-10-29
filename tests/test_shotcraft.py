import json
import shutil
import subprocess

import pytest

import check
import layers
import shotcraft

MOTION = shotcraft.MOTION


def test_style_names_match_shotcraft():
    assert [shotcraft.kebab(x) for x in ("BraceExpand", "Basic3DScene", "Carousel3D", "AxisRescaleShockV2")] == [
        "brace-expand", "basic-3d-scene", "carousel-3d", "axis-rescale-shock-v2"]


def test_only_words_people_read_become_text_slots():
    keep = ["Meet the", "Tighter", "NEW", "CRAFT THE SHOT.", "先说结论", "2.5D CAMERA MOVES"]
    drop = ["L", "-0.028em", "sRGB", "fractalNoise", "SourceGraphic", '"Helvetica Neue", Helvetica', "0.08em 0.1em", "absolute",
            "space-between", "rgba(0,0,0,0.3)", "logo.png"]
    assert all(shotcraft._display(t) for t in keep) and not any(shotcraft._display(t) for t in drop)


def test_cards_are_read_from_the_upstream_layout(tmp_path):
    (tmp_path / "references" / "shots" / "typography").mkdir(parents=True)
    (tmp_path / "references" / "shots" / "typography" / "brace-expand.md").write_text(
        "---\nname: brace-expand\n一句话: 括号拉开\n---\n\n## 参考实现\ndemos/typography/brace-expand/\n（BraceExpand.tsx）\n", encoding="utf-8")
    (tmp_path / "demos" / "typography" / "brace-expand").mkdir(parents=True)
    (tmp_path / "demos" / "typography" / "brace-expand" / "BraceExpand.tsx").write_text(
        "export const BRACE_EXPAND_DURATION = 120;\nexport const BraceExpand: React.FC = () => null;\n", encoding="utf-8")
    cards = shotcraft.cards(tmp_path)
    assert cards == [{"name": "brace-expand", "summary": "括号拉开", "use": "", "category": "typography", "styles": [
        {"key": "brace-expand", "component": "BraceExpand", "duration_name": "BRACE_EXPAND_DURATION", "frames": 120,
         "file": "typography/brace-expand/BraceExpand.tsx"}]}]


def test_content_box_and_side_or_full():
    from PIL import Image, ImageDraw
    a = Image.new("L", (1920, 1080), 0)
    ImageDraw.Draw(a).rectangle([700, 400, 1200, 600], fill=255)
    box, cover = shotcraft._bbox([a])
    assert box[0] in (700, 698) and abs(box[2] - 500) <= 4 and cover > 0.04
    assert shotcraft.classify(box, cover) == "side"
    assert shotcraft.classify([100, 100, 1700, 800], 0.3) == "full"  # 缩进侧边只剩三分之一
    assert shotcraft.classify(None, 0.0) == "skip"  # 去底以后什么都不剩


@pytest.mark.skipif(shutil.which("node") is None, reason="needs node")
def test_slot_loader_wraps_text_without_touching_the_rest(tmp_path):
    src = ("import x from './y';\nconst TITLE = 'Your title';\nconst style = { position: 'absolute' };\n"
           "export const C = () => <div className=\"big\" style={style}>Hello world<b>{TITLE}</b></div>;\n")
    f = tmp_path / "C.tsx"
    f.write_text(src, encoding="utf-8")
    js = f"const l=require({json.dumps(str(MOTION / 'src/shotcraft/slot-loader.cjs'))});process.stdout.write(l.call({{resourcePath:{json.dumps(str(f))}}},require('fs').readFileSync({json.dumps(str(f))},'utf8')))"
    out = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True, cwd=MOTION).stdout
    assert "from './y'" in out and '__scT("Your title")' in out and '{__scT("Hello world")}' in out
    assert 'className={__scT("big")}' in out and 'position: __scT("absolute")' in out  # 样式值也过一遍，表里没有就原样返回
    assert out.startswith("import { __scT } from")


# —— 方案里用直通卡 ——

MANIFEST = {"rev": "x", "styles": {
    "marker-underline-title": {"card": "marker-underline-title", "form": "text", "auto": "side", "verdict": None,
                               "slots": [{"text": "Meet the", "em": 4.8}, {"text": "new", "em": 1.8}]},
    "word-relay-geometry": {"card": "word-relay-geometry", "form": "text", "auto": "full", "verdict": None, "slots": []},
    "aurora-bloom-bg-flip": {"card": "aurora-bloom-bg-flip", "form": "diagram", "auto": "skip", "verdict": None, "slots": []}}}
BRIEF = {"canvas": [1920, 1080], "face_box": [700, 140, 520, 760], "motion_placement": "overlay-sides"}


@pytest.fixture
def manifest(monkeypatch):
    monkeypatch.setattr(shotcraft, "manifest", lambda: MANIFEST)
    monkeypatch.setattr(shotcraft, "brand_text_cached", lambda: ["video-shotcraft"])


def _shot(card="marker-underline-title", zone="left", texts=None, **kw):
    s = {"id": "S1", "start": 10.0, "end": 16.0, "hold": 12.0, "zone": zone, "component": "ShotCraft",
         "props": {"card": card, "at": 10.5, "texts": {"Meet the": "先说", "new": "结论", "video-shotcraft": "再讲原因"} if texts is None else texts}}
    s.update(kw)
    return s


def _rules(*shots, duration=600.0):
    return [x["rule"] for x in check.run({"duration": duration, "shots": list(shots)}, {"words": []}, BRIEF)]


def test_pass_card_with_every_slot_replaced_passes(manifest):
    assert _rules(_shot()) == []


def test_pass_card_rules(manifest):
    assert _rules(_shot(card="nope")) == ["shotcraft-unknown"]
    assert _rules(_shot(card="aurora-bloom-bg-flip", texts={})) == ["shotcraft-skip"]
    assert _rules(_shot(card="word-relay-geometry", texts={})) == ["shotcraft-full-only"]
    assert _rules(_shot(card="word-relay-geometry", texts={}, zone="full")) == []
    assert _rules(_shot(texts={"Meet the": "先说"})) == ["shotcraft-text-left"]  # new 没换：原卡的英文会留在画面上
    assert _rules(_shot(texts={"Meet the": "先说", "new": "结论", "Hello": "x"})) == ["shotcraft-slot"]
    assert _rules(_shot(texts={"Meet the": "这一段换上去的话实在太长了", "new": "结论"})) == ["shotcraft-text-long"]


def test_fullscreen_time_is_capped_so_the_face_stays(manifest):
    full = _shot(card="word-relay-geometry", texts={}, zone="full", start=10.0, end=20.0, hold=12.0)
    assert "too-much-fullscreen" in _rules(full, duration=60.0)  # 10 秒 > 60 秒的 10%
    assert "too-much-fullscreen" not in _rules(full, duration=200.0)


def test_pass_layer_render_command_and_placement(tmp_path):
    s = _shot()
    cmd = layers.remotion_cmd(s, {"w": 620, "h": 788}, tmp_path / "S1.mov")
    assert "ShotcraftPass" in cmd
    props = json.loads(cmd[-1].split("=", 1)[1])
    assert props == {"card": "marker-underline-title", "lead": 15, "frames": 180, "texts": s["props"]["texts"]}
    layers.box_file(tmp_path / "S1.mov").write_text(json.dumps({"box": [754, 430, 534, 230], "ink": "light"}))
    rp = layers.render_plan({"duration": 60, "shots": [s]}, {**BRIEF, "card": "paper"}, base="/v.mov", layer_dir=tmp_path)
    sh = rp["shots"][0]
    assert sh["src_rect"] == [718, 394, 606, 302] and sh["panel"] == list(layers.PANEL["dark"])  # 浅色字垫深底
    rp = layers.render_plan({"duration": 60, "shots": [{**s, "zone": "full"}]}, {**BRIEF, "card": "paper"}, base="/v.mov", layer_dir=tmp_path)
    assert "panel" not in rp["shots"][0]  # 全屏不垫底
