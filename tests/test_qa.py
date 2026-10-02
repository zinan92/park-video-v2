import json
import shutil
import subprocess

import pytest

import qa

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


@pytest.fixture
def clean(tmp_path):
    p = tmp_path / "clean.mp4"
    ff("-f", "lavfi", "-i", "testsrc=size=320x180:rate=30:duration=4", "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
       "-shortest", "-pix_fmt", "yuv420p", str(p))
    return p


@needs_ffmpeg
def test_clean_video_passes(clean):
    r = qa.video_checks(clean, expected_duration=4.0)
    assert r["status"] == "pass", r
    assert r["decode"]["errors"] == "" and r["black"] == [] and r["silence"] == []
    assert -40 < r["loudness"]["integrated_lufs"] < 0


@needs_ffmpeg
def test_black_and_silent_stretch_is_reported(tmp_path):
    p = tmp_path / "bad.mp4"
    ff("-f", "lavfi", "-i", "color=c=black:size=320x180:rate=30:duration=3", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
       "-t", "3", "-pix_fmt", "yuv420p", str(p))
    r = qa.video_checks(p, expected_duration=3.0)
    assert r["status"] == "fail"
    assert r["black"] and r["silence"]


@needs_ffmpeg
def test_duration_mismatch_fails(clean):
    r = qa.video_checks(clean, expected_duration=10.0)
    assert r["status"] == "fail" and r["duration"]["pass"] is False


@needs_ffmpeg
def test_hold_is_static_for_a_still_layer_and_not_for_a_moving_one(tmp_path):
    still, moving = tmp_path / "still.mov", tmp_path / "moving.mov"
    ff("-f", "lavfi", "-i", "color=c=red@0.9:size=160x90:rate=30:duration=2,format=rgba", "-c:v", "qtrle", str(still))
    ff("-f", "lavfi", "-i", "testsrc=size=160x90:rate=30:duration=2,format=rgba", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo",
       "-t", "2", "-c:v", "qtrle", str(moving))
    with_audio = tmp_path / "still_audio.mov"
    ff("-f", "lavfi", "-i", "color=c=red@0.9:size=160x90:rate=30:duration=2,format=rgba", "-f", "lavfi", "-i", "sine=duration=2",
       "-t", "2", "-c:v", "qtrle", str(with_audio))
    assert qa.hold_is_static(with_audio, hold_offset=0.5, end_offset=1.8) is True
    assert qa.hold_is_static(still, hold_offset=0.5, end_offset=1.8) is True
    assert qa.hold_is_static(moving, hold_offset=0.5, end_offset=1.8) is False


def test_placement_must_clear_caption_band_and_face():
    plan = {"canvas": [1920, 1080], "shots": [
        {"id": "OK", "src_rect": [0, 0, 1056, 918], "zone": {"x": 40, "y": 40, "w": 760, "h": 788}},
        {"id": "BAD", "src_rect": [0, 0, 1056, 918], "zone": {"x": 40, "y": 400, "w": 760, "h": 600}},
    ]}
    brief = {"caption_band": [868, 1000], "face_box": [840, 180, 440, 500], "motion_placement": "overlay-sides"}
    f = qa.placement_checks(plan, brief)
    assert [x["shot"] for x in f] == ["BAD"] and f[0]["rule"] == "caption-band"


@needs_ffmpeg
def test_contact_sheet_has_one_tile_per_shot(tmp_path, clean):
    out = tmp_path / "sheet.jpg"
    qa.contact_sheet(clean, [0.5, 1.5, 2.5], out)
    assert out.is_file() and out.stat().st_size > 1000


@needs_ffmpeg
def test_run_writes_qa_json(tmp_path, clean):
    plan = {"base": str(clean), "canvas": [320, 180], "shots": []}
    brief = {"caption_band": [150, 170], "motion_placement": "overlay-sides", "face_box": [120, 20, 80, 100]}
    out = tmp_path / "qa.json"
    report = qa.run(clean, plan, brief, out, expected_duration=4.0)
    assert json.loads(out.read_text())["status"] == report["status"] == "pass"


@needs_ffmpeg
def test_hold_ignores_12_bit_prores_noise(tmp_path):
    # 同一张静止画面编成 ProRes 4444：12 位里每帧有编码噪声，按显示像素比应当判为静止
    still = tmp_path / "still4444.mov"
    ff("-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=0.04,format=rgba,loop=loop=60:size=1:start=0",
       "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-t", "2", str(still))
    assert qa.hold_is_static(still, hold_offset=0.5, end_offset=1.5) is True
