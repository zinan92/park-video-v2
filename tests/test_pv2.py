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


def test_bad_style_choice_waits_for_park_instead_of_crashing(proj):
    (v2(proj) / "brief.yaml").write_text((ROOT / "brief.example.yaml").read_text(encoding="utf-8") + "card: 毛玻璃\n", encoding="utf-8")
    s = pv2.summary(proj)
    assert s["waiting_for"] == "Park 确认 brief" and "card" in s["detail"]


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


# —— 设置清单（工作台读它画滑杆）——
def test_settings_lists_every_slider_with_values_and_where_they_come_from(proj):
    s = pv2.settings(proj)
    keys = [x["key"] for x in s["schema"]["sliders"]]
    assert keys == ["density", "effort", "evidence", "edit", "sound", "review"]
    assert s["values"]["density"] == "medium" and s["source"]["density"] == "repo"
    effort = next(x for x in s["schema"]["sliders"] if x["key"] == "effort")
    assert [lv.get("available", True) for lv in effort["levels"]] == [True, True, True, False]
    presets = {p["name"]: p["available"] for p in s["schema"]["presets"]}
    assert presets == {"快出": True, "标准": True, "精品": True}
    assert {c["key"] for c in s["components"]} >= {"TextLines", "Cycle", "IconList"}


def test_setting_a_project_value_keeps_the_rest_of_the_brief(proj):
    brief = v2(proj) / "brief.yaml"
    brief.write_text((ROOT / "brief.example.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    pv2.set_values(str(proj), {"density": "low", "card": "dark"})
    text = brief.read_text(encoding="utf-8")
    assert "face_box: [700, 140, 520, 760]   # 人脸" in text  # 注释和其他字段原样留着
    s = pv2.settings(proj)
    assert s["values"]["density"] == "low" and s["source"]["density"] == "project" and s["values"]["card"] == "dark"
    pv2.set_values(str(proj), {"no_motion": [[1.0, 2.0]]})  # 多行的字段整块换掉
    import brief as brief_mod
    b = brief_mod.load(brief)
    assert b["no_motion"] == [[1.0, 2.0]] and b["density"] == "low"


def test_setting_a_default_goes_to_parks_own_file_not_the_repo(proj, tmp_path):
    before = (ROOT / "defaults.yaml").read_text(encoding="utf-8")
    pv2.set_values("default", {"effort": "a"})
    assert (ROOT / "defaults.yaml").read_text(encoding="utf-8") == before
    assert pv2.settings()["values"]["effort"] == "a" and pv2.settings()["source"]["effort"] == "user"


def test_unbuilt_level_or_bad_value_is_refused_before_writing(proj):
    with pytest.raises(ValueError, match="还没做"):
        pv2.set_values(str(proj), {"effort": "d"})
    with pytest.raises(ValueError, match="density"):
        pv2.set_values(str(proj), {"density": "huge"})
    with pytest.raises(ValueError, match="数字"):
        pv2.set_values(str(proj), {"max_items": "three"})


def test_catalog_has_a_chinese_name_and_example_for_every_component():
    items = pv2.catalog()
    assert len(items) >= 14
    for c in items:
        assert c["name"] and c["form"] in ("text", "number", "chart", "diagram", "icon") and c["example"]


def test_shotcraft_cards_are_listed_with_what_we_already_adapted(tmp_path, monkeypatch):
    home = tmp_path / "sc"
    (home / "gallery" / "api").mkdir(parents=True)
    (home / "gallery" / "media" / "poster").mkdir(parents=True)
    (home / "gallery" / "media" / "poster" / "cycle-glass-node-morph.jpg").write_bytes(b"x")
    (home / "gallery" / "media" / "cycle-glass-node-morph.mp4").write_bytes(b"x")
    (home / "gallery" / "api" / "library.json").write_text(json.dumps({
        "categories": {"data": {"zh": "数据与图表"}},
        "cards": [{"name": "cycle-glass-node-morph", "summary": "循环图", "use": "机制解释", "category": "data",
                   "styles": [{"key": "cycle-glass-node-morph"}]},
                  {"name": "aurora-bloom-bg-flip", "summary": "极光", "use": "开场", "category": "opening"}]}), encoding="utf-8")
    monkeypatch.setenv(pv2.SHOTCRAFT_ENV, str(home))
    cards = {c["name"]: c for c in pv2.shotcraft()}
    assert cards["cycle-glass-node-morph"]["adapted_as"] == ["Cycle", "GlassCycle"] and cards["cycle-glass-node-morph"]["poster"]
    assert cards["cycle-glass-node-morph"]["category_zh"] == "数据与图表"
    assert cards["cycle-glass-node-morph"]["video"]
    assert cards["aurora-bloom-bg-flip"]["adapted_as"] == [] and cards["aurora-bloom-bg-flip"]["poster"] is None
    assert cards["aurora-bloom-bg-flip"]["video"] is None



def test_sample_uses_marked_shots_otherwise_the_first_ten_seconds():
    plan = {"duration": 100.0, "shots": [{"id": "A", "start": 2.0, "end": 8.0, "hold": 5.0},
                                         {"id": "B", "start": 30.0, "end": 40.0, "hold": 34.0, "sample": True},
                                         {"id": "C", "start": 60.0, "end": 70.0, "hold": 63.0, "sample": True}]}
    assert pv2.sample_windows(plan) == [(29.6, 35.0), (59.6, 64.0)]
    for s in plan["shots"]:
        s.pop("sample", None)
    assert pv2.sample_windows(plan) == [(1.5, 11.5)]
