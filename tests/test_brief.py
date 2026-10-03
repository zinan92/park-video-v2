from pathlib import Path

import pytest

import brief

ROOT = Path(__file__).resolve().parents[1]


def test_example_brief_is_complete():
    b = brief.load(ROOT / "brief.example.yaml")
    assert b["motion_placement"] == "overlay-sides"
    assert b["no_motion"] == [[312.9, 565.4]]


def test_missing_fields_stop_and_name_what_to_ask(tmp_path):
    p = tmp_path / "brief.yaml"
    p.write_text("video_type: 横屏口播\ncanvas: [1920, 1080]\n", encoding="utf-8")
    with pytest.raises(brief.NeedsPark) as e:
        brief.load(p)
    assert "motion_placement" in e.value.missing and "captions_burned_in" in e.value.missing
    assert "问 Park" in str(e.value)


def test_overlay_sides_needs_a_face_box(tmp_path):
    p = tmp_path / "brief.yaml"
    text = (ROOT / "brief.example.yaml").read_text(encoding="utf-8").replace("face_box:", "#face_box:")
    p.write_text(text, encoding="utf-8")
    with pytest.raises(brief.NeedsPark) as e:
        brief.load(p)
    assert e.value.missing == ["face_box"]


def test_unknown_placement_is_rejected(tmp_path):
    p = tmp_path / "brief.yaml"
    text = (ROOT / "brief.example.yaml").read_text(encoding="utf-8").replace("overlay-sides  #", "diagonal  #")
    p.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError):
        brief.load(p)


def test_side_zones_come_from_the_face_box():
    b = {"canvas": [1920, 1080], "face_box": [700, 140, 520, 760], "caption_band": [868, 1000]}
    left, right = brief.side_zones(b, margin=40)
    assert left == {"x": 40, "y": 40, "w": 620, "h": 788}
    assert right == {"x": 1260, "y": 40, "w": 620, "h": 788}


def test_defaults_fill_in_style_and_rules():
    b = brief.load(ROOT / "brief.example.yaml")
    assert b["card"] == "glass" and b["intensity"] == "restrained" and b["rewrite"] == "trim-only"
    assert b["max_items"] == 3 and b["min_gap"] == 5 and b["exit"] == "after-sentence"


def test_a_video_can_override_a_default(tmp_path):
    p = tmp_path / "brief.yaml"
    p.write_text((ROOT / "brief.example.yaml").read_text(encoding="utf-8") + "card: dark\nmax_items: 5\n", encoding="utf-8")
    b = brief.load(p)
    assert b["card"] == "dark" and b["max_items"] == 5 and b["intensity"] == "restrained"


def test_unknown_style_choice_is_rejected(tmp_path):
    p = tmp_path / "brief.yaml"
    p.write_text((ROOT / "brief.example.yaml").read_text(encoding="utf-8") + "card: neon\n", encoding="utf-8")
    with pytest.raises(ValueError, match="card"):
        brief.load(p)


def test_sfx_and_bgm_are_no_longer_asked_but_old_briefs_still_load(tmp_path):
    p = tmp_path / "brief.yaml"
    p.write_text((ROOT / "brief.example.yaml").read_text(encoding="utf-8") + "sfx: low\nbgm: none\n", encoding="utf-8")
    assert brief.load(p)["sfx"] == "low"
    assert "sfx" not in brief.REQUIRED and "bgm" not in brief.REQUIRED


def test_banned_words_never_ship_in_the_public_defaults():
    assert "banned_words" not in brief.defaults()


def test_forms_default_to_all_five_and_unknown_forms_are_rejected(tmp_path):
    assert brief.load(ROOT / "brief.example.yaml")["forms"] == ["text", "number", "chart", "diagram", "icon"]
    p = tmp_path / "brief.yaml"
    p.write_text((ROOT / "brief.example.yaml").read_text(encoding="utf-8") + "forms: [text, photo]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="forms"):
        brief.load(p)
