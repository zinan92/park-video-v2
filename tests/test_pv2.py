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
        assert c["name"] and c["form"] in ("text", "number", "chart", "diagram", "icon", "image") and c["example"]


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



def test_sample_uses_key_shots_otherwise_the_first_ten_seconds():
    plan = {"duration": 100.0, "shots": [{"id": "A", "start": 2.0, "end": 8.0, "hold": 5.0},
                                         {"id": "B", "start": 30.0, "end": 40.0, "hold": 34.0, "key": True},
                                         {"id": "C", "start": 60.0, "end": 70.0, "hold": 63.0, "sample": True}]}
    assert pv2.sample_windows(plan) == [(29.6, 35.0), (59.6, 64.0)]
    for s in plan["shots"]:
        s.pop("sample", None)
        s.pop("key", None)
    assert pv2.sample_windows(plan) == [(1.5, 11.5)]


def test_premium_sample_waits_for_the_benchmark_compare(proj, monkeypatch):
    """精品档：重点镜头没和标杆对比过、或对比之后层又重渲了，就不出样片。"""
    shot = {"id": "K1", "start": 1.0, "end": 5.0, "hold": 3.0, "key": True}
    plan = {"duration": 10.0, "shots": [shot]}
    monkeypatch.setattr(pv2, "layers_to_render", lambda project, shots, b, *scale: [])
    (v2(proj) / "layers").mkdir()
    layer = v2(proj) / "layers" / "K1.mov"
    layer.write_text("x")
    assert pv2.compare_missing(proj, plan, {"effort": "c"}) == ["K1"]
    assert pv2.compare_missing(proj, plan, {"effort": "b"}) == []  # 标准档不要求
    (v2(proj) / "compare").mkdir()
    pair = v2(proj) / "compare" / "K1.mp4"
    pair.write_text("x")
    import os
    os.utime(layer, (pair.stat().st_mtime - 10, pair.stat().st_mtime - 10))
    assert pv2.compare_missing(proj, plan, {"effort": "c"}) == []
    os.utime(layer, (pair.stat().st_mtime + 10, pair.stat().st_mtime + 10))  # 对比后又改过
    assert pv2.compare_missing(proj, plan, {"effort": "c"}) == ["K1"]
    monkeypatch.setattr(pv2, "layers_to_render", lambda project, shots, b, *scale: shots)  # 层要重渲
    os.utime(layer, (pair.stat().st_mtime - 10, pair.stat().st_mtime - 10))
    assert pv2.compare_missing(proj, plan, {"effort": "c"}) == ["K1"]


def test_benchmark_must_be_in_the_private_library(tmp_path, monkeypatch):
    import bench
    video = tmp_path / "old.mp4"
    (tmp_path / "b.yaml").write_text(f"抓重点: {{video: {video}, start: 59, end: 72.2, shows: 一群里挑一个}}\n", encoding="utf-8")
    monkeypatch.setenv("PV2_BENCHMARKS", str(tmp_path / "b.yaml"))
    with pytest.raises(SystemExit, match="移动硬盘"):
        bench.resolve("抓重点")
    video.write_text("x")
    assert bench.resolve("抓重点")["end"] == 72.2
    with pytest.raises(SystemExit, match="没有「别的」"):
        bench.resolve("别的")


def test_side_by_side_pads_the_shorter_clip(tmp_path):
    def clip(path, seconds, color):
        pv2._ffmpeg("-f", "lavfi", "-i", f"color=c={color}:s=1920x1080:d={seconds}:r=30", "-f", "lavfi", "-i",
                    f"sine=d={seconds}", "-shortest", "-pix_fmt", "yuv420p", str(path))
    clip(tmp_path / "a.mp4", 2, "red")
    clip(tmp_path / "b.mp4", 3, "blue")
    out, strip = tmp_path / "pair.mp4", tmp_path / "pair.jpg"
    pv2.side_by_side(tmp_path / "a.mp4", tmp_path / "b.mp4", out, bench_label="抓重点", strip=strip)
    import subprocess
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration",
                            "-of", "json", str(out)], capture_output=True, text=True, check=True)
    info = json.loads(probe.stdout)
    assert info["streams"][0]["width"] == 1920 and info["streams"][0]["height"] == 540
    assert abs(float(info["format"]["duration"]) - 3.0) < 0.2
    assert strip.is_file()


# —— 字幕：只给视频路径，SRT 自己找；找不到就问、确实没有就本机转写 ——

def test_init_finds_the_srt_next_to_the_video(tmp_path):
    (tmp_path / "粗剪.mov").write_text("x")
    (tmp_path / "粗剪.srt").write_text("1\n00:00:00,000 --> 00:00:01,000\n你好\n", encoding="utf-8")
    pv2.init(tmp_path, video="粗剪.mov")
    assert json.loads((v2(tmp_path) / "project.json").read_text())["srt"] == str(tmp_path / "粗剪.srt")


def test_init_without_any_srt_leaves_it_empty_and_prep_says_to_ask(tmp_path):
    (tmp_path / "粗剪.mov").write_text("x")
    pv2.init(tmp_path, video="粗剪.mov")
    assert json.loads((v2(tmp_path) / "project.json").read_text())["srt"] is None
    (v2(tmp_path) / "brief.yaml").write_text((ROOT / "brief.example.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(SystemExit) as e:
        pv2.do_prep(tmp_path)
    assert "transcribe" in str(e.value)


def test_transcribe_writes_an_srt_the_rest_of_the_flow_uses(tmp_path, monkeypatch):
    import sys
    import types
    (tmp_path / "粗剪.mov").write_text("x")
    pv2.init(tmp_path, video="粗剪.mov")
    fake = types.SimpleNamespace(transcribe=lambda *a, **k: {"segments": [{"start": 0.0, "end": 1.5, "text": "先说结论"},
                                                                         {"start": 1.5, "end": 3.25, "text": " 再讲原因 "}]})
    monkeypatch.setitem(sys.modules, "mlx_whisper", fake)
    out = pv2.transcribe(tmp_path)
    assert out.read_text(encoding="utf-8") == ("1\n00:00:00,000 --> 00:00:01,500\n先说结论\n\n"
                                               "2\n00:00:01,500 --> 00:00:03,250\n再讲原因\n\n")
    assert json.loads((v2(tmp_path) / "project.json").read_text())["srt"] == "v2/source.srt"


# —— 渲染包：是方案不是参考 ——

def _pack(tmp_path):
    pack = tmp_path / "渲染包"
    pack.mkdir()
    (pack / "plan.json").write_text(json.dumps({"title": "t", "beats": [
        {"n": 1, "line": "十分好用", "motion": "before-after-slider-scrub"},
        {"n": 2, "line": "开头要抓人", "motion": "brace-expand"}]}, ensure_ascii=False), encoding="utf-8")
    (pack / "settings.json").write_text(json.dumps({"density": "mid", "effort": "b", "skill": "park-video-v2"}), encoding="utf-8")
    (pack / "script.md").write_text("稿子", encoding="utf-8")
    return pack


def test_render_pack_goes_into_the_project_and_its_settings_read_back(proj, tmp_path):
    pv2.take_pack(proj, _pack(tmp_path))
    assert [b["motion"] for b in pv2.plan_beats(proj)] == ["before-after-slider-scrub", "brace-expand"]
    s = pv2.settings(proj)
    assert s["values"]["density"] == "medium" and s["source"]["density"] == "project" and s["values"]["effort"] == "b"


def test_sample_waits_for_the_deviation_list_park_has_seen(proj, tmp_path):
    pv2.take_pack(proj, _pack(tmp_path))
    plan = {"shots": [{"id": "V01", "beat": 1, "component": "Compare"},  # Compare 是照 before-after-slider-scrub 改的：算照做
                      {"id": "V02", "beat": 2, "component": "IconList"}]}  # 花括号拉开换成了图标列表：偏离
    st = pv2.deviations_state(proj, plan)
    assert st["undone"] == [2] and "deviations.json" in st["problem"]
    (v2(proj) / "deviations.json").write_text(json.dumps([]), encoding="utf-8")
    assert "第 2 镜" in pv2.deviations_state(proj, plan)["problem"]  # 偷偷换了、清单里没写
    dev = [{"beat": 2, "motion": "brace-expand", "instead": "IconList", "why": "库里没有花括号拉开，改编要半天"}]
    (v2(proj) / "deviations.json").write_text(json.dumps(dev, ensure_ascii=False), encoding="utf-8")
    assert "Park 还没看" in pv2.deviations_state(proj, plan)["problem"]
    pv2.approve(proj, "deviations", message="第 2 镜先这样")
    assert pv2.deviations_state(proj, plan)["problem"] is None
    dev.append({"beat": 1, "why": "又改了"})
    (v2(proj) / "deviations.json").write_text(json.dumps(dev, ensure_ascii=False), encoding="utf-8")
    assert "Park 还没看" in pv2.deviations_state(proj, plan)["problem"]  # 批过之后清单又变了，要重新批


def test_everything_done_as_planned_needs_only_an_empty_list(proj, tmp_path):
    pv2.take_pack(proj, _pack(tmp_path))
    plan = {"shots": [{"id": "V01", "beat": 1, "component": "Compare"}, {"id": "V02", "beat": 2, "component": "Compare"}]}
    assert pv2.deviations_state(proj, plan)["undone"] == [2]  # Compare 不是从 brace-expand 改的
    assert pv2.deviations_state(proj, {"shots": []})["undone"] == [1, 2]
    assert pv2.deviations_state(tmp_path / "没有渲染包", {"shots": []})["problem"] is None


def test_find_falls_back_to_the_closest_thing_he_actually_said():
    words = [{"w": "这个", "start": 1.0, "end": 1.3}, {"w": "非常", "start": 1.3, "end": 1.6}, {"w": "好用", "start": 1.6, "end": 2.0},
             {"w": "你", "start": 5.0, "end": 5.2}, {"w": "听到", "start": 5.2, "end": 5.5}, {"w": "什么", "start": 5.5, "end": 5.9}]
    assert pv2.find(words, "十分好用") == []
    assert pv2.near(words, "十分好用")[0] == {"at": 1.3, "said": "非常好用", "score": 0.5}
    assert pv2.near(words, "你学到什么")[0]["said"] == "你听到什么"


# —— 4K 原片：坐标照 canvas，合成按倍数放大 ——

def test_4k_rough_cut_scales_up_and_wrong_aspect_stops():
    b = {"canvas": [1920, 1080]}
    assert pv2.base_scale(Path("."), b, {"rough_cut": "x", "size": [3840, 2160]}) == 2
    assert pv2.base_scale(Path("."), b, {"rough_cut": "x", "size": [1920, 1080]}) == 1
    with pytest.raises(SystemExit) as e:
        pv2.base_scale(Path("."), b, {"rough_cut": "x", "size": [2160, 3840]})
    assert "宽高比" in str(e.value)
