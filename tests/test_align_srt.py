import align_srt

SRT = """1
00:00:00,770 --> 00:00:02,800
我这个号只有6,000粉丝

2
00:00:02,870 --> 00:00:05,530
上个星期 我用3个小时

3
00:00:30,000 --> 00:00:31,000
后面
"""


def test_parse_srt_strips_spaces_and_keeps_times(tmp_path):
    p = tmp_path / "s.srt"
    p.write_text("﻿" + SRT, encoding="utf-8")
    cues = align_srt.parse_srt(p)
    assert [c["text"] for c in cues] == ["我这个号只有6,000粉丝", "上个星期我用3个小时", "后面"]
    assert cues[0]["start"] == 0.77 and cues[1]["end"] == 5.53


def test_windows_stay_under_the_limit(tmp_path):
    p = tmp_path / "s.srt"
    p.write_text(SRT, encoding="utf-8")
    groups = align_srt.windows(align_srt.parse_srt(p))
    assert groups == [[0, 1], [2]]


def test_spread_splits_a_cue_evenly_by_character():
    words = align_srt.spread({"start": 1.0, "end": 2.0, "text": "四个字吧"})
    assert [w["w"] for w in words] == list("四个字吧")
    assert words[0]["start"] == 1.0 and words[-1]["end"] == 2.0
