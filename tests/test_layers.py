import os
import shutil
from pathlib import Path

import pytest

import layers

BRIEF = {"canvas": [1920, 1080], "face_box": [840, 180, 440, 500], "caption_band": [868, 1000],
         "motion_placement": "overlay-sides"}
PLAN = {"duration": 60.0, "shots": [
    {"id": "V01", "start": 1.0, "end": 5.0, "zone": "left", "component": "NumberRoll",
     "props": {"value": "6000", "lockAt": 2.2}, "reveals": [], "hold": 3.0},
    {"id": "V02", "start": 20.0, "end": 30.0, "zone": "right", "component": "TextLines",
     "props": {"lines": ["a"], "ats": [21.0]}, "reveals": [], "hold": 22.0},
]}


def test_render_plan_points_each_shot_at_its_layer_and_zone(tmp_path):
    rp = layers.render_plan(PLAN, BRIEF, base="/v/rough.mov", layer_dir=tmp_path)
    assert rp["base"] == "/v/rough.mov" and rp["canvas"] == [1920, 1080]
    v1, v2 = rp["shots"]
    assert v1["layer"] == str(tmp_path / "V01.mov") and v1["zone"] == {"x": 40, "y": 40, "w": 760, "h": 788}
    assert v1["src_rect"] == [0, 0, 760, 788] and v1["hold"] == 3.0
    assert v2["zone"]["x"] == 1320 and v2["src_rect"] == [0, 0, 560, 788]


def test_remotion_command_passes_zone_and_times():
    cmd = layers.remotion_cmd(PLAN["shots"][0], {"x": 40, "y": 40, "w": 760, "h": 788}, Path("/tmp/V01.mov"))
    assert cmd[:4] == ["npx", "remotion", "render", "src/index.ts"] and "Shot" in cmd
    props = [a for a in cmd if a.startswith("--props=")][0]
    assert '"component": "NumberRoll"' in props and '"w": 760' in props and '"start": 1.0' in props
    assert "--codec=prores" in cmd and "--prores-profile=4444" in cmd


def test_card_style_from_the_brief_goes_to_remotion():
    look = layers.style({**BRIEF, "card": "glass", "accent": "#123456"})
    assert look == {"card": "glass", "accent": "#123456", "overshoot": False, "glassAlpha": layers.GLASS_ALPHA}
    cmd = layers.remotion_cmd(PLAN["shots"][0], {"x": 40, "y": 40, "w": 760, "h": 788}, Path("/tmp/V01.mov"), look)
    props = [a for a in cmd if a.startswith("--props=")][0]
    assert '"card": "glass"' in props and '"accent": "#123456"' in props


def test_glass_cards_ask_the_composite_for_a_blur():
    assert all(s["glass"] == layers.GLASS_ALPHA for s in layers.render_plan(PLAN, {**BRIEF, "card": "glass"}, base="b", layer_dir=Path("/x"))["shots"])
    assert all(s["glass"] is None for s in layers.render_plan(PLAN, {**BRIEF, "card": "paper"}, base="b", layer_dir=Path("/x"))["shots"])


def test_shots_in_window_for_the_sample():
    assert [s["id"] for s in layers.shots_between(PLAN, 0.0, 10.0)] == ["V01"]
    assert [s["id"] for s in layers.shots_between(PLAN, 4.0, 22.0)] == ["V01", "V02"]


def test_pick_sample_window_starts_just_before_the_first_shot():
    assert layers.sample_window(PLAN, length=10.0) == (0.5, 10.5)


@pytest.mark.skipif(not os.environ.get("PV2_REMOTION") or shutil.which("npx") is None, reason="set PV2_REMOTION=1 to run a real render")
def test_real_layer_render(tmp_path):
    for card in ("glass", "paper", "dark", "none"):
        out = layers.render_layers({"duration": 60, "shots": [PLAN["shots"][1]]}, {**BRIEF, "card": card}, tmp_path / card, status=None)
        assert out[0].is_file() and layers.props_file(out[0]).is_file()
