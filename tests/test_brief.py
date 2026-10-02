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
