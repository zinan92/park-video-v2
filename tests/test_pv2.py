import json
from pathlib import Path

import pytest

import pv2

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def proj(tmp_path):
    (tmp_path / "rough.mov").write_text("x")
    (tmp_path / "source.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\n你好\n", encoding="utf-8")
    pv2.init(tmp_path, video="rough.mov", srt="source.srt")
    return tmp_path


def v2(p):
    return p / "v2"


def test_init_writes_project_and_a_brief_to_fill(proj):
    assert json.loads((v2(proj) / "project.json").read_text()) == {"rough_cut": "rough.mov", "srt": "source.srt"}
    assert (v2(proj) / "brief.yaml").is_file()


def test_summary_walks_through_the_four_steps(proj):
    s = pv2.summary(proj)
    assert s["step"] == "准备" and s["waiting_for"] == "Park 确认 brief"
    (v2(proj) / "brief.yaml").write_text((ROOT / "brief.example.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    assert pv2.summary(proj)["waiting_for"] == "跑 prep"
    (v2(proj) / "words.json").write_text('{"words": []}')
    assert pv2.summary(proj) | {} == pv2.summary(proj) and pv2.summary(proj)["step"] == "方案"
    assert pv2.summary(proj)["waiting_for"] == "AI 写 plan.json"
    (v2(proj) / "plan.json").write_text('{"duration": 10, "shots": []}')
    (v2(proj) / "sample.mp4").write_text("x")
    s = pv2.summary(proj)
    assert s["step"] == "方案" and s["waiting_for"] == "Park 看样片" and s["sample"] == "v2/sample.mp4"
    pv2.approve(proj, "sample", message="可以，全部渲染")
    assert pv2.summary(proj)["step"] == "渲染" and pv2.summary(proj)["waiting_for"] == "跑 render"
    (v2(proj) / "status.json").write_text(json.dumps({"state": "rendering", "stage": "composite", "percent": 63}))
    s = pv2.summary(proj)
    assert s["step"] == "渲染" and s["percent"] == 63 and s["waiting_for"] is None
    (v2(proj) / "final.mp4").write_text("x")
    (v2(proj) / "qa.json").write_text('{"status": "pass"}')
    (v2(proj) / "status.json").write_text(json.dumps({"state": "done", "stage": "qa", "percent": 100}))
    s = pv2.summary(proj)
    assert s["step"] == "终审" and s["waiting_for"] == "Park 看成片" and s["final"] == "v2/final.mp4"
    pv2.approve(proj, "final", message="就这样了")
    assert pv2.summary(proj)["step"] == "已交付"


def test_failed_render_is_shown_not_hidden(proj):
    (v2(proj) / "brief.yaml").write_text((ROOT / "brief.example.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (v2(proj) / "words.json").write_text('{"words": []}')
    (v2(proj) / "plan.json").write_text('{"duration": 10, "shots": []}')
    (v2(proj) / "status.json").write_text(json.dumps({"state": "failed", "stage": "layers", "percent": 20}))
    s = pv2.summary(proj)
    assert s["failed"] is True and "layers" in s["detail"]


def test_approval_needs_a_message(proj):
    with pytest.raises(ValueError):
        pv2.approve(proj, "sample", message="")
    with pytest.raises(ValueError):
        pv2.approve(proj, "hook", message="x")


BRIEF = {"canvas": [1920, 1080], "face_box": [840, 180, 440, 500], "caption_band": [868, 1000],
         "motion_placement": "overlay-sides", "card": "glass", "accent": "#E2461F", "overshoot": False}
SHOTS = [{"id": "A", "start": 0, "end": 1, "zone": "left", "component": "TextLines", "props": {"lines": ["a"]}},
         {"id": "B", "start": 2, "end": 3, "zone": "right", "component": "TextLines", "props": {"lines": ["b"]}}]


def _rendered(proj, shot, brief):
    """假装这个镜头已经按 brief 渲染过：层文件 + 旁边的 props。"""
    import check, layers
    d = v2(proj) / "layers"
    d.mkdir(exist_ok=True)
    (d / f"{shot['id']}.mov").write_text("x")
    props = layers.layer_props(shot, check._zone(shot, brief), layers.style(brief))
    layers.props_file(d / f"{shot['id']}.mov").write_text(json.dumps(props, sort_keys=True))


def test_layers_already_rendered_with_the_same_props_are_reused(proj):
    _rendered(proj, SHOTS[0], BRIEF)
    assert [s["id"] for s in pv2.layers_to_render(proj, SHOTS, BRIEF)] == ["B"]


def test_changing_a_shot_makes_only_that_layer_stale(proj):
    _rendered(proj, SHOTS[0], BRIEF)
    _rendered(proj, SHOTS[1], BRIEF)
    changed = [SHOTS[0], {**SHOTS[1], "props": {"lines": ["改了"]}}]
    assert [s["id"] for s in pv2.layers_to_render(proj, changed, BRIEF)] == ["B"]


def test_changing_the_card_style_makes_layers_stale(proj):
    _rendered(proj, SHOTS[0], BRIEF)
    assert [s["id"] for s in pv2.layers_to_render(proj, SHOTS[:1], {**BRIEF, "card": "paper"})] == ["A"]


def test_changing_component_code_makes_layers_stale(proj, monkeypatch):
    _rendered(proj, SHOTS[0], BRIEF)
    import time
    monkeypatch.setattr(pv2, "_motion_mtime", lambda: time.time() + 100)
    assert [s["id"] for s in pv2.layers_to_render(proj, SHOTS[:1], BRIEF)] == ["A"]


def test_find_returns_every_time_a_phrase_is_spoken():
    words = [{"w": "流量", "start": 1.0}, {"w": "很", "start": 1.5}, {"w": "重要", "start": 1.7},
             {"w": "流量", "start": 9.0}, {"w": "只是", "start": 9.4}]
    assert pv2.find(words, "流量") == [1.0, 9.0]
    assert pv2.find(words, "流量只是") == [9.0]
    assert pv2.find(words, "没说过") == []


def test_qa_rerun_updates_status(proj, monkeypatch):
    (v2(proj) / "brief.yaml").write_text((ROOT / "brief.example.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    (v2(proj) / "plan.json").write_text('{"duration": 10, "shots": []}')
    (v2(proj) / "render-plan.json").write_text('{"base": "x", "canvas": [1920, 1080], "shots": []}')
    (v2(proj) / "final.mp4").write_text("x")
    (v2(proj) / "status.json").write_text(json.dumps({"state": "failed", "stage": "qa", "percent": 100}))
    monkeypatch.setattr(pv2.qa_mod, "run", lambda *a, **k: {"status": "pass", "placement": [], "hold_static": []})
    assert pv2.do_qa(proj)["status"] == "pass"
    assert json.loads((v2(proj) / "status.json").read_text())["state"] == "done"
