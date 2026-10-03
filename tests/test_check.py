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
    s = {"id": "V02", "start": 21.0, "end": 33.0, "zone": "right", "component": "TextLines",
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


# —— defaults.yaml 里 Park 定的风格和规则 ——
SPEECH = {"words": [
    {"w": "这是", "start": 10.0, "end": 10.3}, {"w": "两件", "start": 10.3, "end": 10.6},
    {"w": "非常", "start": 10.6, "end": 10.9}, {"w": "重要", "start": 10.9, "end": 11.2},
    {"w": "的", "start": 11.2, "end": 11.3}, {"w": "问题", "start": 11.3, "end": 11.7},
    {"w": "客户甲", "start": 12.0, "end": 12.5}, {"w": "一年", "start": 12.5, "end": 12.8},
    {"w": "200万", "start": 12.8, "end": 13.4},
]}
RULES = {**BRIEF, "banned_words": ["客户甲"], "max_items": 3, "text_amount": "one-point",
         "rewrite": "trim-only", "exit": "after-sentence", "min_gap": 5}


def card(**kw):
    s = {"id": "V08", "start": 10.0, "end": 12.5, "zone": "right", "component": "TextLines",
         "props": {"lines": ["两件重要的问题"], "ats": [10.3]}, "reveals": [{"at": 10.3, "text": "两件非常重要的问题"}], "hold": 11.0}
    s.update(kw)
    return s


def rules(*shots, **over):
    return [x["rule"] for x in check.run({"duration": 600.0, "shots": list(shots)}, SPEECH, {**RULES, **over})]


def test_card_that_follows_every_rule_passes():
    assert rules(card()) == []


def test_trimming_the_words_is_fine():
    assert rules(card(props={"lines": ["两件重要问题"], "ats": [10.3]})) == []


def test_swapping_a_word_is_caught():
    # 昨天的 V08：他说「非常重要」，卡上写成「最重要」
    assert rules(card(props={"lines": ["两件最重要的问题"], "ats": [10.3]})) == ["rewritten"]


def test_kicker_and_titles_count_too():
    assert rules(card(props={"kicker": "核心洞察", "lines": ["两件重要问题"], "ats": [10.3]})) == ["rewritten"]


def test_summarize_mode_allows_rewording():
    assert rules(card(props={"lines": ["两件最重要的问题"], "ats": [10.3]}), rewrite="summarize") == []


def test_banned_word_on_the_card_is_caught():
    f = rules(card(end=13.5, props={"lines": ["客户甲一年200万"], "ats": [12.0]}, reveals=[{"at": 12.0, "text": "客户甲一年200万"}]))
    assert f == ["banned-word"]


def test_too_many_items_on_one_card():
    f = rules(card(props={"lines": ["两件", "重要", "问题", "一年"], "ats": [10.3, 10.9, 11.3, 12.5]}), text_amount="points", intensity="medium")
    assert f == ["too-many-items"]


def test_one_point_card_cannot_carry_a_paragraph():
    long = "这是两件非常重要的问题客户一年200万"
    f = rules(card(props={"lines": [long, long]}, reveals=[]), rewrite="summarize")
    assert "not-one-point" in f


def test_component_above_the_chosen_effort():
    s = card(component="Cycle", props={"nodes": [{"text": "两件", "at": 10.3}, {"text": "问题", "at": 11.3}]}, reveals=[])
    assert rules(s, effort="a") == ["effort-too-high"]
    assert rules(s, effort="b") == []


def test_most_cards_cannot_be_plain_text_at_effort_b():
    t1 = card()
    t2 = card(id="V09", start=18.0, end=19.0, hold=18.5, zone="left", component="IconPoint", reveals=[],
              props={"icon": "users", "iconAt": 18.0, "lines": ["一年200万"], "ats": [18.0]})
    t5 = card(id="V12", start=40.0, end=41.0, hold=40.5, reveals=[], component="Cycle",
              props={"nodes": [{"text": "一年", "at": 40.0}, {"text": "200万", "at": 40.0}]})
    assert "effort-too-low" not in rules(t1, t2, t5, effort="b", rewrite="summarize")  # 1/3 是文字卡
    t3 = card(id="V10", start=25.0, end=26.0, hold=25.5, reveals=[], component="Quote", props={"lines": ["一年"], "ats": [25.0]})
    t4 = card(id="V11", start=30.0, end=31.0, hold=30.5, reveals=[], component="BigNumber", props={"value": "200万", "at": 30.0})
    assert "effort-too-low" in rules(t1, t2, t3, t4, t5, effort="b", rewrite="summarize")  # 3/5


def test_density_range_is_enforced():
    plan = {"duration": 100.0, "shots": [card(start=10.0, end=12.5)]}
    f = check.run(plan, SPEECH, {**RULES, "density": "medium"})
    assert [x["rule"] for x in f] == ["density"] and "30%" in f[0]["detail"]
    assert check.run(plan, SPEECH, {**RULES, "coverage": [0.0, 0.05]}) == []


def test_until_next_still_has_a_ceiling():
    assert rules(card(end=20.0), exit="until-next") == []
    assert rules(card(end=23.0), exit="until-next") == ["stays-too-long"]


def test_card_stays_long_after_the_sentence_ends():
    assert rules(card(end=16.0)) == ["stays-too-long"]
    assert rules(card(end=16.0), exit="until-next") == []  # 停到下一张：最后一句说完后 10 秒内都可以


def test_cards_too_close_together():
    later = card(id="V09", start=15.0, end=18.0, hold=15.5, zone="left", reveals=[], props={"lines": ["一年200万"], "ats": [15.0]})
    assert rules(card(), later) == ["gap"]
    assert rules(card(), {**later, "start": 17.6, "end": 20.6, "hold": 17.8}, rewrite="summarize") == []


def test_coverage_is_reported_not_enforced():
    plan = {"duration": 100.0, "shots": [card(start=10.0, end=20.0)]}
    assert check.coverage(plan, {"no_motion": [[50.0, 100.0]]}) == 0.2


def test_line_too_long_for_the_zone_gets_tiny_text():
    # 昨天样片里右侧窄区的「现在能够赚一年200万」只剩 30 多 px
    narrow = {"x": 1320, "y": 40, "w": 560, "h": 788}
    assert check.line_px("现在能够赚一年200万", 560, 1) < check.MIN_TEXT_PX
    assert check.line_px("赚一年200万", 560, 1) >= check.MIN_TEXT_PX
    s = card(zone=narrow, props={"lines": ["这是两件非常重要的问题一年200万"], "ats": [10.3]}, reveals=[])
    assert "text-too-small" in rules(s, rewrite="summarize")


# —— 表达形式和图标 ——
def test_two_cards_in_a_row_with_the_same_form():
    later = card(id="V09", start=18.0, end=21.0, hold=18.5, zone="left", reveals=[], component="Flow",
                 props={"steps": [{"text": "一年", "at": 18.0}, {"text": "200万", "at": 18.0}]})
    first = card(component="Cycle", props={"nodes": [{"text": "两件", "at": 10.3}, {"text": "问题", "at": 11.3}]}, reveals=[])
    assert rules(first, later, effort="b", rewrite="summarize") == ["same-form"]
    other = {**later, "component": "IconPoint", "props": {"icon": "users", "iconAt": 18.0, "lines": ["一年200万"], "ats": [18.0]}}
    assert rules(first, other, effort="b", rewrite="summarize") == []


def test_icon_must_exist_and_its_name_is_not_checked_as_speech():
    ok = card(component="IconPoint", props={"icon": "users", "iconAt": 10.3, "lines": ["两件重要的问题"], "ats": [10.3]})
    assert rules(ok) == []
    if check.ICON_DIR.is_dir():
        bad = {**ok, "props": {**ok["props"], "icon": "no-such-icon-xyz"}}
        assert rules(bad) == ["unknown-icon"]


def test_component_that_does_not_exist():
    assert rules(card(component="PillSlot")) == ["unknown-component"]


def test_card_too_short_to_read():
    assert rules(card(end=11.5, hold=11.0)) == ["too-short"]


def test_avoided_component_is_caught():
    assert rules(card(), avoid=["TextLines"]) == ["avoided-component"]



# —— effort c 组件：动作做完才能停住、区域够宽、字不超长 ——
def test_hold_cannot_come_before_the_component_finishes_moving():
    s = card(component="GlassCycle", effort="c", reveals=[], end=14.0, hold=11.0,
             props={"nodes": [{"text": "两件", "at": 10.3}, {"text": "问题", "at": 11.3}]})
    f = rules(s, effort="c", rewrite="summarize")
    assert "hold-before-settle" in f
    assert "hold-before-settle" not in rules({**s, "hold": 12.3}, effort="c", rewrite="summarize")


def test_c_component_needs_a_wide_enough_zone():
    narrow = {"x": 1320, "y": 40, "w": 480, "h": 788}
    s = card(component="GlassCycle", zone=narrow, reveals=[], end=14.0, hold=12.3,
             props={"nodes": [{"text": "两件", "at": 10.3}, {"text": "问题", "at": 11.3}]})
    assert "zone-too-narrow" in rules(s, effort="c", rewrite="summarize")


def test_c_component_label_limit():
    s = card(component="GlassCycle", reveals=[], end=14.0, hold=12.3,
             props={"nodes": [{"text": "两件非常重要", "at": 10.3}, {"text": "问题", "at": 11.3}]})
    assert "label-too-long" in rules(s, effort="c", rewrite="summarize")



# —— 精品档（C / D）的流程规则 ——
def _premium(**kw):
    base = card(intent={"means": "两件事里有一件最重要", "picture": "两颗点里一颗变红"}, sample=True)
    base.update(kw)
    return base


def test_premium_cards_need_meaning_and_picture():
    assert "no-intent" in rules(card(sample=True), effort="c", rewrite="summarize")
    assert "no-intent" not in rules(_premium(), effort="c", rewrite="summarize")
    assert "no-intent" not in rules(card(), effort="b")  # 快出 / 标准不要求


def test_premium_never_repeats_a_component():
    a = _premium()
    b2 = _premium(id="V09", start=18.0, end=21.0, hold=18.5, zone="left", reveals=[], sample=False,
                  props={"lines": ["一年200万"], "ats": [18.0]})
    assert "repeated-component" in rules(a, b2, effort="c", rewrite="summarize")


def test_premium_marks_two_or_three_sample_shots():
    assert "no-sample-shots" in rules(_premium(sample=False), effort="c", rewrite="summarize")
