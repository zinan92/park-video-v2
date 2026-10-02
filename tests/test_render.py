import json
import shutil
import subprocess

import pytest

import render

ZONE = {"x": 40, "y": 40, "w": 760, "h": 788}


def test_fit_keeps_aspect_and_centres_vertically():
    r = render.fit((1056, 918), ZONE)
    assert r["w"] == 760 and r["h"] == round(918 * 760 / 1056)
    assert r["x"] == 40 and r["y"] == 40 + (788 - r["h"]) // 2


def test_fit_limited_by_height():
    r = render.fit((400, 1000), {"x": 0, "y": 0, "w": 760, "h": 500})
    assert r["h"] == 500 and r["w"] == 200 and r["x"] == 280


def test_shots_outside_the_range_are_left_out():
    shots = [{"id": "A", "start": 0, "end": 5}, {"id": "B", "start": 20, "end": 25}, {"id": "C", "start": 9, "end": 12}]
    assert [s["id"] for s in render.in_range(shots, 8.0, 18.0)] == ["C"]


def test_filter_places_each_layer_in_its_time_window():
    shots = [{"id": "A", "start": 2.0, "end": 4.0, "src_rect": [10, 0, 100, 80], "place": {"x": 5, "y": 6, "w": 50, "h": 40}}]
    f = render.filtergraph(shots)
    assert "crop=100:80:10:0" in f and "scale=50:40" in f
    assert "setpts=PTS-STARTPTS+2.0/TB" in f
    assert "overlay=5:6:enable='between(t,2.0,4.0)':eof_action=pass" in f
    assert f.rstrip().endswith("[v1]")


def test_status_file_reports_real_progress(tmp_path):
    p = tmp_path / "status.json"
    render.write_status(p, "rendering", 3.25, 10.0)
    s = json.loads(p.read_text())
    assert s == {"state": "rendering", "stage": "composite", "done": 3.25, "total": 10.0, "percent": 32, "unit": "seconds"}
    render.write_status(p, "rendering", 2, 4, stage="layers", weight=(0, 40), unit="shots")
    assert json.loads(p.read_text())["percent"] == 20


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_end_to_end_on_a_tiny_synthetic_video(tmp_path):
    base = tmp_path / "base.mp4"
    layer = tmp_path / "layer.mov"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:size=320x180:rate=30:duration=3",
                    "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-shortest", "-pix_fmt", "yuv420p", str(base)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=red@0.9:size=320x180:rate=30:duration=1,format=rgba",
                    "-c:v", "qtrle", str(layer)], check=True)
    plan = {"base": str(base), "canvas": [320, 180],
            "shots": [{"id": "A", "start": 1.0, "end": 2.0, "layer": str(layer), "src_rect": [0, 0, 320, 180],
                       "zone": {"x": 10, "y": 10, "w": 100, "h": 60}}]}
    out = tmp_path / "out.mp4"
    status = tmp_path / "status.json"
    render.render(plan, out, status, start=0.0, end=3.0)
    s = json.loads(status.read_text())
    assert s["state"] == "done" and s["percent"] == 100
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                           capture_output=True, text=True, check=True)
    assert abs(float(probe.stdout) - 3.0) < 0.1
    # 1.5s 时左上角区域是红的（叠上去了），0.5s 时不是
    def pixel(t):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(out), "-frames:v", "1",
                              "-vf", "crop=2:2:40:30,format=rgb24", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        return tuple(raw[:3])
    assert pixel(1.5)[0] > 180 and pixel(1.5)[1] < 80
    assert not (pixel(0.5)[0] > 180 and pixel(0.5)[1] < 80)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_sample_starting_mid_shot_seeks_into_the_layer(tmp_path):
    base, layer = tmp_path / "base.mp4", tmp_path / "layer.mov"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:size=320x180:rate=30:duration=4",
                    "-pix_fmt", "yuv420p", str(base)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=red@0.9:size=320x180:rate=30:duration=2,format=rgba",
                    "-c:v", "qtrle", str(layer)], check=True)
    plan = {"base": str(base), "canvas": [320, 180],
            "shots": [{"id": "A", "start": 1.0, "end": 3.0, "layer": str(layer), "src_rect": [0, 0, 320, 180],
                       "zone": {"x": 10, "y": 10, "w": 100, "h": 60}}]}
    out = tmp_path / "out.mp4"
    render.render(plan, out, None, start=2.0, end=4.0)
    def pixel(t):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(out), "-frames:v", "1",
                              "-vf", "crop=2:2:40:30,format=rgb24", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True, check=True).stdout
        return tuple(raw[:3])
    assert pixel(0.3)[0] > 180 and pixel(0.3)[1] < 80      # 样片开头还在镜头里
    assert not (pixel(1.5)[0] > 180 and pixel(1.5)[1] < 80)  # 3.0s 之后镜头结束
