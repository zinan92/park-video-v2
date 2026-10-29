import shutil
import subprocess

import pytest

import brief
import captions
import render

SRT = """1
00:00:01,000 --> 00:00:02,500
先说结论

2
00:00:02,500 --> 00:00:04,000
这个 high level 的想法

3
00:00:09,000 --> 00:00:10,000
很后面的一句
"""


def test_srt_keeps_spaces_between_english_words_only(tmp_path):
    p = tmp_path / "a.srt"
    p.write_text(SRT, encoding="utf-8")
    assert [c["text"] for c in captions.read_srt(p)] == ["先说结论", "这个high level的想法", "很后面的一句"]


def test_long_line_breaks_at_punctuation_nearest_the_middle():
    assert captions.lines("短句", 10) == ["短句"]
    assert captions.lines("前面这一段话很长，后面这一段也很长", 10) == ["前面这一段话很长，", "后面这一段也很长"]
    assert all(len(x) <= 12 for x in captions.lines("没有标点的一句很长很长的话放不下", 10))
    assert captions.lines("abc defghij klm", 4) != ["abc defghij klm"]


def test_ass_uses_parks_style_and_scales_with_the_video(tmp_path):
    p = tmp_path / "a.srt"
    p.write_text(SRT, encoding="utf-8")
    hd = captions.to_ass(captions.read_srt(p), [1920, 1080])
    k4 = captions.to_ass(captions.read_srt(p), [3840, 2160])
    assert "PlayResY: 1080" in hd and ",PingFang SC,56,&H00F6FDFF," in hd and ",3,12,0,2," in hd  # 底板（BorderStyle 3），不是描边
    assert ",PingFang SC,112," in k4 and ",3,24,0,2," in k4
    assert captions.band([1920, 1080]) == [904, 1040] and captions.band([3840, 2160]) == [1808, 2080]


def test_sample_window_only_gets_its_own_lines_shifted_to_zero(tmp_path):
    p = tmp_path / "a.srt"
    p.write_text(SRT, encoding="utf-8")
    ass = captions.to_ass(captions.read_srt(p), [1920, 1080], start=2.0, end=5.0)
    events = [ln for ln in ass.splitlines() if ln.startswith("Dialogue")]
    assert len(events) == 2
    assert events[0].startswith("Dialogue: 0,0:00:00.00,0:00:00.50,") and events[1].startswith("Dialogue: 0,0:00:00.50,0:00:02.00,")


def test_brief_that_burns_captions_keeps_motion_out_of_them(tmp_path):
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    text = (root / "brief.example.yaml").read_text(encoding="utf-8")
    text = text.replace("captions_burned_in: true", "captions_burned_in: false").replace("caption_band: [868, 1000]", "")
    p = tmp_path / "brief.yaml"
    p.write_text(text + "burn_captions: true\n", encoding="utf-8")
    assert brief.load(p)["caption_band"] == [904, 1040]
    p.write_text((root / "brief.example.yaml").read_text(encoding="utf-8") + "burn_captions: true\n", encoding="utf-8")
    with pytest.raises(ValueError, match="烧一遍"):
        brief.load(p)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
def test_captions_are_burned_into_the_video(tmp_path):
    base = tmp_path / "base mp4 有空格.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=gray:size=640x360:rate=30:duration=5",
                    "-f", "lavfi", "-i", "sine=duration=5", "-shortest", "-pix_fmt", "yuv420p", str(base)], check=True)
    srt = tmp_path / "a.srt"
    srt.write_text(SRT, encoding="utf-8")
    plain, burned = tmp_path / "plain.mp4", tmp_path / "burned.mp4"
    render.render({"base": str(base), "canvas": [640, 360], "shots": []}, plain, None, start=0.0, end=5.0)
    render.render({"base": str(base), "canvas": [640, 360], "shots": [], "captions": str(srt)}, burned, None, start=0.0, end=5.0)

    def bottom(path, t):  # 字幕带那一块的平均亮度
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(path), "-frames:v", "1", "-vf", "crop=40:16:300:326,scale=1:1",
                            "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True, check=True)
        return r.stdout[0]
    assert abs(bottom(burned, 1.8) - bottom(plain, 1.8)) > 5  # 有字幕的时刻底下变了（深色底板）
    assert abs(bottom(burned, 4.6) - bottom(plain, 4.6)) <= 2  # 这时没人说话，没有字幕
