import json
import shutil
import subprocess
import sys

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


def test_glass_shot_is_baked_from_just_its_own_seconds():
    shot = {"id": "A", "start": 1.0, "end": 2.0, "layer": "/l/A.mov", "src_rect": [0, 0, 100, 60],
            "zone": {"x": 20, "y": 20, "w": 100, "h": 60}, "glass": 0.45}
    cmd = render.glass_cmd("/v/base.mov", shot, render.Path("/l/A.glass.mov"))
    assert cmd[cmd.index("-ss") + 1] == "1.000" and cmd[cmd.index("-t") + 1] == "1.000"
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "crop=100:60:20:20,gblur" in graph and "lut=c0='min(255,val*2.2222)'" in graph and "alphamerge" in graph


def _sharpness(path, t, crop):
    """相邻像素平均差多少：细节越多越大，模糊后接近 0。"""
    w = int(crop.split(":")[0])
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(path), "-frames:v", "1",
                          "-vf", f"crop={crop},format=gray", "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    diffs = [abs(raw[i] - raw[i + 1]) for i in range(len(raw) - 1) if (i + 1) % w]
    return sum(diffs) / len(diffs)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_glass_card_on_a_real_render(tmp_path):
    base, layer = tmp_path / "base.mp4", tmp_path / "card.mov"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=3",
                    "-vf", "noise=alls=60:allf=u", "-pix_fmt", "yuv420p", "-crf", "10", str(base)], check=True)
    # 一张铺满层的半透明白卡（不透明度 0.45），和 Remotion 渲出来的毛玻璃层一样
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=white@0.45:size=120x80:rate=30:duration=1,format=rgba",
                    "-c:v", "qtrle", str(layer)], check=True)
    shot = {"id": "A", "start": 1.0, "end": 2.0, "layer": str(layer), "src_rect": [0, 0, 120, 80],
            "zone": {"x": 100, "y": 50, "w": 120, "h": 80}}
    glass, plain = tmp_path / "glass.mp4", tmp_path / "plain.mp4"
    render.render({"base": str(base), "canvas": [320, 180], "shots": [{**shot, "glass": 0.45}]}, glass, None)
    assert (tmp_path / "card.glass.mov").is_file()
    render.render({"base": str(base), "canvas": [320, 180], "shots": [shot]}, plain, None)
    inside, outside = "80:50:120:65", "60:40:10:120"
    # 卡片底下：毛玻璃把细节糊掉，比只盖一层半透明白平滑得多
    assert _sharpness(glass, 1.5, inside) < 0.3 * _sharpness(plain, 1.5, inside)
    # 卡片外面、镜头前后：和原画面一样
    assert _sharpness(glass, 1.5, outside) > 0.8 * _sharpness(base, 1.5, outside)
    assert _sharpness(glass, 0.5, inside) > 0.8 * _sharpness(base, 0.5, inside)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_glass_shots_spread_across_a_video_render_in_one_pass(tmp_path):
    # 毛玻璃先逐个镜头烤好，整条合成里只剩普通叠加（这个小例子复现不了真片 20 个镜头时的卡死，只保证烤层这条路走得通）
    base, layer = tmp_path / "base.mp4", tmp_path / "card.mov"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=30:duration=40",
                    "-pix_fmt", "yuv420p", str(base)], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=white@0.45:size=120x80:rate=30:duration=2,format=rgba",
                    "-c:v", "qtrle", str(layer)], check=True)
    shots = [{"id": f"S{i}", "start": t, "end": t + 2.0, "layer": str(layer), "src_rect": [0, 0, 120, 80],
              "zone": {"x": 100, "y": 50, "w": 120, "h": 80}, "glass": 0.45} for i, t in enumerate((2.0, 35.0))]
    out = tmp_path / "out.mp4"
    proc = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(render.Path(render.__file__).parent)!r}); import render, json;"
                           f"render.render(json.loads({json.dumps(json.dumps({'base': str(base), 'canvas': [320, 180], 'shots': shots}))}), render.Path({str(out)!r}), None)"],
                          timeout=60)
    assert proc.returncode == 0 and out.stat().st_size > 10000
