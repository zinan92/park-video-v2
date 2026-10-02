import check

WORDS = {"words": [
    {"w": "流量", "start": 21.40, "end": 21.80},
    {"w": "只是", "start": 21.80, "end": 22.10},
    {"w": "渠道", "start": 22.10, "end": 22.60},
    {"w": "你", "start": 30.40, "end": 30.55},
    {"w": "发的", "start": 30.55, "end": 30.90},
    {"w": "视频", "start": 30.90, "end": 31.30},
]}
BRIEF = {"canvas": [1920, 1080], "caption_band": [868, 1000], "no_motion": [[312.9, 565.4]],
         "face_box": [700, 140, 520, 760], "motion_placement": "overlay-sides"}


def shot(**kw):
    s = {"id": "V02", "start": 21.0, "end": 33.0, "zone": "right", "component": "PillSlot",
         "reveals": [{"at": 21.4, "text": "流量只是渠道"}], "hold": 31.5}
    s.update(kw)
    return s


def findings(*shots, duration=578.0):
    return check.run({"duration": duration, "shots": list(shots)}, WORDS, BRIEF)


def test_clean_plan_passes():
    assert findings(shot()) == []


def test_text_before_the_word_is_spoken():
    # 今天的 V02：「你发的每一篇视频」在 30.0s 出现，「你」30.4s 才说
    f = findings(shot(reveals=[{"at": 30.0, "text": "你发的视频"}]))
    assert [x["rule"] for x in f] == ["text-before-speech"]
    assert f[0]["shot"] == "V02" and "30.4" in f[0]["detail"]


def test_text_a_frame_early_is_fine():
    assert findings(shot(reveals=[{"at": 30.37, "text": "你发的视频"}])) == []


def test_text_not_found_in_speech():
    f = findings(shot(reveals=[{"at": 22.0, "text": "他没说过的话"}]))
    assert [x["rule"] for x in f] == ["text-not-spoken"]


def test_shot_inside_no_motion_range():
    f = findings(shot(id="V10", start=333.8, end=347.6, reveals=[], hold=346.0))
    assert [x["rule"] for x in f] == ["no-motion-range"]


def test_shot_overlapping_the_edge_of_no_motion_range():
    f = findings(shot(id="V09", start=300.0, end=315.0, reveals=[], hold=310.0))
    assert [x["rule"] for x in f] == ["no-motion-range"]


def test_hold_must_be_inside_the_shot():
    f = findings(shot(hold=34.0))
    assert [x["rule"] for x in f] == ["hold-outside-shot"]


def test_zone_must_stay_out_of_caption_band():
    f = findings(shot(zone={"x": 1260, "y": 500, "w": 600, "h": 450}))
    assert [x["rule"] for x in f] == ["caption-band"]


def test_zone_must_not_cover_the_face_when_overlaying_beside_it():
    f = findings(shot(zone={"x": 900, "y": 40, "w": 400, "h": 400}))
    assert [x["rule"] for x in f] == ["covers-face"]


def test_overlapping_shots_in_the_same_zone():
    f = findings(shot(id="V02"), shot(id="V03", start=32.0, end=40.0, reveals=[], hold=39.0))
    assert [x["rule"] for x in f] == ["zone-overlap"]


def test_adjacent_shots_in_different_zones_are_fine():
    assert findings(shot(id="V02"), shot(id="V03", start=32.0, end=40.0, zone="left", reveals=[], hold=39.0)) == []


def test_shot_past_the_end_of_the_video():
    f = findings(shot(start=570.0, end=600.0, hold=590.0, reveals=[]))
    assert [x["rule"] for x in f] == ["outside-video"]
