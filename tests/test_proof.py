"""证据截图卡（10/5 Park）：只放内容工作台里他点过「要」的真截图，来源照抄，停够时间。"""
import json

import pytest

import check
import proof
import pv2

WORDS = {"words": [{"w": "收入", "start": 20.0, "end": 20.5}]}
BRIEF = {"canvas": [1920, 1080], "caption_band": [868, 1000], "face_box": [700, 140, 520, 760],
         "motion_placement": "overlay-sides", "evidence": "search"}


def _items(tmp_path):
    img = tmp_path / "C-627f1fbc.png"
    img.write_bytes(b"\x89PNG fake")
    mine = tmp_path / "mine-B.png"
    mine.write_bytes(b"\x89PNG mine")
    return [{"path": str(img), "kind": "data", "source": "Fortune（Yahoo Finance 转载）", "date": "2025-08-18T00:00:00Z",
             "caption": "MIT 报告：AI 试点只有约 5% 带来营收快速增长", "point": "C", "point_title": "收入", "url": "https://finance.yahoo.com/x"},
            {"path": str(mine), "kind": "mine", "source": "我自己的截图", "date": "2026-10-05", "caption": "我的后台", "point": "B"}]


def test_putting_evidence_copies_by_content_and_sets_the_level(tmp_path):
    proj = tmp_path / "proj"
    pv2.init(proj, video="粗剪.mov", srt=None)
    manifest = tmp_path / "list.json"
    manifest.write_text(json.dumps(_items(tmp_path), ensure_ascii=False), encoding="utf-8")
    res = pv2.evidence(proj, manifest)
    assert res["evidence"] == "search"
    files = [i["file"] for i in res["items"]]
    assert all((proj / "v2" / "evidence" / f).is_file() for f in files) and files[0].endswith(".png") and len(files[0]) == 16
    assert res["items"][0]["line"] == "来源：Fortune（Yahoo Finance 转载） · 2025-08-18"
    assert "evidence: \"search\"" in (proj / "v2" / "brief.yaml").read_text()
    assert [i["file"] for i in proof.load(proj / "v2")] == files
    # 再给一次（他取消了外面那张）：整份换掉，旧图删掉，只剩他自己的截图就是 own
    manifest.write_text(json.dumps(_items(tmp_path)[1:], ensure_ascii=False), encoding="utf-8")
    res = pv2.evidence(proj, manifest)
    assert res["evidence"] == "own" and not (proj / "v2" / "evidence" / files[0]).exists()
    manifest.write_text("[]", encoding="utf-8")
    assert pv2.evidence(proj, manifest)["evidence"] == "none"


def test_putting_evidence_needs_a_project_and_real_images(tmp_path):
    with pytest.raises(ValueError, match="init"):
        proof.put(tmp_path / "nope" / "v2", [])
    (tmp_path / "v2").mkdir()
    with pytest.raises(ValueError, match="找不到"):
        proof.put(tmp_path / "v2", [{"path": str(tmp_path / "missing.png")}])


def _shot(**kw):
    s = {"id": "P1", "start": 19.5, "end": 25.0, "zone": "left", "component": "Proof",
         "props": {"src": "abc.png", "at": 20.0, "source": "来源：Fortune · 2025-08-18"}, "reveals": [], "hold": 21.0}
    s.update(kw)
    return s


EVIDENCE = [{"file": "abc.png", "line": "来源：Fortune · 2025-08-18"}]


def rules(shot, brief=BRIEF, evidence=EVIDENCE):
    return [f["rule"] for f in check.run({"duration": 60, "shots": [shot]}, WORDS, {**brief, "rewrite": "trim-only", "text_amount": "one-point"}, evidence)]


def test_a_clean_evidence_card_passes_without_tripping_the_text_rules():
    assert rules(_shot()) == []  # 来源一行不是他说的话：不查原话删减、不套一张卡的字数


def test_only_picked_evidence_with_its_real_source_and_enough_time():
    assert rules(_shot(props={"src": "made-up.png", "at": 20.0, "source": "来源：Fortune · 2025-08-18"})) == ["proof-unknown"]
    assert rules(_shot(props={"src": "abc.png", "at": 20.0, "source": "来源：路透社"})) == ["proof-source"]
    assert rules(_shot(end=22.0)) == ["proof-too-short"]
    assert rules(_shot(), brief={**BRIEF, "evidence": "none"}) == ["proof-off"]
    assert "proof-unknown" in rules(_shot(), evidence=[])


def test_banned_words_still_apply_to_the_source_line():
    assert "banned-word" in rules(_shot(), brief={**BRIEF, "banned_words": ["Fortune"]})


def test_evidence_cards_do_not_count_as_low_effort():
    b = {**BRIEF, "effort": "b"}
    shots = [_shot(id=f"P{i}", start=10.0 * i, end=10.0 * i + 5, hold=10.0 * i + 1, props={**_shot()["props"], "at": 10.0 * i + 0.5}) for i in range(1, 4)]
    found = check.run({"duration": 60, "shots": shots}, {"words": []}, b, EVIDENCE)
    assert "effort-too-low" not in [f["rule"] for f in found]


def test_the_two_evidence_levels_can_be_chosen_now(tmp_path):
    proj = tmp_path / "proj"
    pv2.init(proj, video="粗剪.mov", srt=None)
    pv2.set_values(str(proj), {"evidence": "search"})
    pv2.set_values(str(proj), {"evidence": "own"})
