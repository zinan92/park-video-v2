"""切 Hook（10/19 Park，10/21 从内容工作台搬来）：照表里标的 Hook 切 h1…hN。ffmpeg 和 whisper 都是假的，不碰他的项目。"""
from __future__ import annotations

import array
import json
import math
import os
from pathlib import Path
import sys
import threading
import time

import pytest

import hookcut

FPS = hookcut.RATE

# 假粗剪的声音：(开始秒, 结束秒, 词) —— 词之间连读，句与句之间有停顿
SPEECH = [
    (0.0, 1.0, ["就是"]),
    (1.5, 4.0, ["我", "每个月", "花", "四百"]),
    (4.6, 6.0, ["记住", "了"]),
    (7.0, 9.0, ["找写", "剪发盘"]),
    (12.0, 14.0, ["找写", "剪发盘"]),
    (14.6, 15.5, ["好"]),
]
DURATION = 16.0


def words() -> list[dict]:
    out = []
    for a, b, ws in SPEECH:
        step = (b - a) / len(ws)
        out += [{"w": w, "start": round(a + i * step, 2), "end": round(a + (i + 1) * step, 2)} for i, w in enumerate(ws)]
    return out


def pcm() -> bytes:
    samples = array.array("h", [0]) * int(DURATION * FPS)
    for a, b, _ws in SPEECH:
        for i in range(int(a * FPS), int(b * FPS)):
            samples[i] = int(8000 * math.sin(i / 7))
    return samples.tobytes()


def project(root: Path, hooks: list[tuple[str, float, float]]) -> Path:
    base = root / "2026-10-19_切钩子"
    (base / "analysis").mkdir(parents=True)
    (base / "subtitles").mkdir()
    (base / "粗剪-10月19日.mov").write_bytes(b"rough cut")
    (base / "subtitles" / "words.json").write_text(json.dumps({"words": words()}, ensure_ascii=False), encoding="utf-8")
    # 剪映字幕：第一条「就是我每个月」带着上一句的「就是」，「找写剪发盘」那条从原话第一个字开始
    (base / "subtitles" / "source.srt").write_text(
        "1\n00:00:00,000 --> 00:00:02,400\n就是我每个月\n\n2\n00:00:02,400 --> 00:00:04,000\n花四百\n\n"
        "3\n00:00:12,000 --> 00:00:14,000\n找写剪发盘\n", encoding="utf-8")
    table = {"schema": "park-video-worktable/v1", "hooks": [
        {"slot": n, "order": n, "text": text, "anchor": {"start_hint": a, "end_hint": b}} for n, (text, a, b) in enumerate(hooks, 1)]}
    (base / "analysis" / "worktable.json").write_text(json.dumps(table, ensure_ascii=False), encoding="utf-8")
    return base


@pytest.fixture()
def fake_ffmpeg(tmp_path: Path, monkeypatch) -> Path:
    """PATH 上放一个假 ffmpeg：读声音时吐假 PCM；切东西时把 -ss / -t 写进输出文件，给假 whisper 看切在哪。"""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (tmp_path / "audio.pcm").write_bytes(pcm())
    log = tmp_path / "ffmpeg.log"
    script = bin_dir / "ffmpeg"
    script.write_text(f"""#!{sys.executable}
import json, os, sys
args = sys.argv[1:]
open({str(log)!r}, "a").write(json.dumps(args) + "\\n")
if "s16le" in args:
    sys.stdout.buffer.write(open({str(tmp_path / "audio.pcm")!r}, "rb").read())
    sys.exit(0)
out = args[-1]
if out.endswith("h2.mp4") and os.path.exists({str(tmp_path / "FAIL_H2")!r}):
    sys.stderr.write("boom")
    sys.exit(1)
open(out, "w").write(json.dumps({{"ss": float(args[args.index("-ss") + 1]), "t": float(args[args.index("-t") + 1])}}))
""", encoding="utf-8")
    script.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    return log


def fake_asr(say):
    """假 whisper：看切出来的声音从第几秒到第几秒，说出那一段的字。"""
    heard: list[tuple[float, float]] = []

    def asr(path: Path) -> str:
        cut = json.loads(path.read_text())
        a, b = cut["ss"], cut["ss"] + cut["t"]
        heard.append((round(a, 3), round(b, 3)))
        return say(a, b)

    asr.heard = heard  # type: ignore[attr-defined]
    return asr


def spoken(a: float, b: float) -> str:
    """那段时间里说出声的词（词的中点落在里面才算）。"""
    return "".join(w["w"] for w in words() if a <= (w["start"] + w["end"]) / 2 <= b)


# -- 对时间 ------------------------------------------------------------------------------------------

def test_a_phrase_said_twice_is_found_near_where_he_marked_it() -> None:
    w = words()
    first = hookcut.locate(w, "找写剪发盘")
    near = hookcut.locate(w, "找写剪发盘", (12.0, 14.0))
    assert w[first[0]]["start"] == 7.0 and w[near[0]]["start"] == 12.0
    assert hookcut.locate(w, "没说过的话", (1.0, 2.0)) is None


def test_cuts_land_in_the_pause_just_before_he_opens_his_mouth_and_just_after_he_stops() -> None:
    env = hookcut.envelope(pcm())
    assert hookcut.cut_points(env, 1.0, 2.0, "start") == [1.45]
    assert hookcut.cut_points(env, 3.5, 4.5, "end") == [4.05]
    start, end, notes = hookcut.refine(env, 1.5, 4.0, "我每个月花四百", cut=lambda s, e: Path("x"), asr=None)
    assert (start, end, notes) == (1.45, 4.05, [])


def test_heard_words_are_compared_loosely_and_unreadable_ones_are_left_alone() -> None:
    assert hookcut.check("就是我每个月花四百。", "我每个月花四百") == (2, 0)
    assert hookcut.check("个月花四百", "我每个月花四百") == (-2, 0)
    assert hookcut.check("我每个月花四百记住", "我每个月花四百") == (0, 2)
    assert hookcut.check("I'm not using AI enough.", "i'm not using AI enough。") == (0, 0)
    assert hookcut.check("", "我每个月花四百") == (99, 99)


def test_when_the_clip_still_has_the_previous_words_the_start_moves_to_the_next_pause() -> None:
    """对齐把首字标早了（像 10/19 Hook 4 的「top」）：重新听到上一句的字，就往里挪一个停顿。"""
    env = hookcut.envelope(pcm())
    asr = fake_asr(spoken)
    # 对齐说这句从 0.4 秒开始（其实 0.0–1.0 是「就是」），离停顿 1.45 太远，先试对齐时间
    start, end, notes = _refine_with_paths(env, 0.4, 4.0, "我每个月花四百", asr)
    assert start == 1.45 and end == 4.05 and notes == []
    assert len(asr.heard) >= 2


def _refine_with_paths(env, start, end, quote, asr, tmp=Path(os.environ.get("TMPDIR", "/tmp"))):
    clip = tmp / f"hookcut-test-{os.getpid()}.json"

    def cut(s: float, e: float) -> Path:
        clip.write_text(json.dumps({"ss": s, "t": e - s}))
        return clip

    try:
        return hookcut.refine(env, start, end, quote, cut=cut, asr=asr)
    finally:
        clip.unlink(missing_ok=True)


def test_a_recogniser_that_cannot_read_the_edges_leaves_the_cut_and_says_listen() -> None:
    env = hookcut.envelope(pcm())
    asr = fake_asr(lambda a, b: "我每個月花肆佰")  # 繁体 / 大写数字：认不准就不挪
    start, end, notes = _refine_with_paths(env, 1.5, 4.0, "我每个月花四百", asr)
    assert (start, end) == (1.45, 4.05) and len(asr.heard) == 1
    assert notes == ["结尾没认出来，听一下"]


# -- 剪映烧录字幕 --------------------------------------------------------------------------------------

def test_a_start_inside_a_caption_that_carries_earlier_words_is_flagged(tmp_path: Path) -> None:
    base = project(tmp_path, [])
    captions = hookcut.cues(base / "subtitles" / "source.srt")
    over = hookcut.caption_overlap(captions, 1.45, "我每个月花四百")
    assert over == {"text": "就是我每个月", "extra": "就是", "seconds": 0.95}
    assert hookcut.caption_overlap(captions, 12.2, "找写剪发盘") is None  # 字幕就从原话第一个字开始
    assert hookcut.caption_overlap(captions, 2.4, "花四百") is None  # 正好切在字幕换条的地方


# -- 整条：假 ffmpeg -----------------------------------------------------------------------------------

def test_export_writes_h1_to_hn_edit_json_and_flags_without_touching_the_body(tmp_path: Path, fake_ffmpeg: Path) -> None:
    base = project(tmp_path, [("我每个月花四百。", 1.4, 4.0), ("找写剪发盘", 11.8, 14.0)])
    asr = fake_asr(spoken)
    qa = hookcut.run(base, asr=asr)
    individual = base / "part-a-hook" / "individual"
    assert sorted(p.name for p in individual.iterdir()) == ["h1.mp4", "h2.mp4"]
    assert json.loads((individual / "h1.mp4").read_text()) == {"ss": 1.45, "t": 2.6}
    edit = json.loads((base / "part-a-hook" / "edit.json").read_text(encoding="utf-8"))
    assert list(edit) == ["source", "source_sha256", "timeline", "order", "fade_s", "clips"]
    assert edit["source"] == "粗剪-10月19日.mov" and edit["order"] == ["h1", "h2"] and edit["fade_s"] == 0.015
    assert edit["clips"] == [{"id": "h1", "quote": "我每个月花四百。", "start": 1.45, "end": 4.05},
                             {"id": "h2", "quote": "找写剪发盘", "start": 11.95, "end": 14.05}]
    assert qa["flags"] == [{"id": "h1", "notes": ["开头 0.95 秒的烧录字幕是「就是我每个月」，带着「就是」，切不掉"]}]
    saved = json.loads((base / "part-a-hook" / "qa.json").read_text(encoding="utf-8"))
    assert saved["flags"] == qa["flags"] and "重新识别" in saved["method"]
    calls = [json.loads(line) for line in fake_ffmpeg.read_text().splitlines()]
    videos = [c for c in calls if c[-1].endswith(".mp4")]
    assert len(videos) == 2, "只切 Hook，正文不重编码"
    for c in videos:
        assert c[c.index("-vf") + 1].startswith("scale='min(1920,iw)':-2") and c[c.index("-crf") + 1] == "18"
        assert "afade=t=in:d=0.015" in c[c.index("-af") + 1] and c[c.index("-ar") + 1] == "48000"
    assert not (base / "part-a-hook" / ".work").exists()


def test_a_failure_midway_leaves_the_old_clips_and_no_half_done_folder(tmp_path: Path, fake_ffmpeg: Path) -> None:
    base = project(tmp_path, [("我每个月花四百", 1.4, 4.0), ("找写剪发盘", 11.8, 14.0)])
    old = base / "part-a-hook" / "individual"
    old.mkdir(parents=True)
    (old / "h1.mp4").write_text("accepted")
    (tmp_path / "FAIL_H2").write_text("")
    with pytest.raises(hookcut.HookCutError, match="切 h2 失败"):
        hookcut.run(base, asr=None)
    assert [p.name for p in old.iterdir()] == ["h1.mp4"] and (old / "h1.mp4").read_text() == "accepted"
    assert not (base / "part-a-hook" / "edit.json").exists() and not (base / "part-a-hook" / ".work").exists()


def test_without_word_times_it_aligns_the_srt_first(tmp_path: Path) -> None:
    base = project(tmp_path, [])
    (base / "subtitles" / "words.json").unlink()
    seen = []

    def align(video: Path, srt: Path, out: Path) -> None:
        seen.append((video.name, srt.name))
        out.write_text(json.dumps({"words": words()}), encoding="utf-8")

    assert len(hookcut.load_words(base, base / "粗剪-10月19日.mov", align=align)) == len(words())
    assert seen == [("粗剪-10月19日.mov", "source.srt")]


# -- 页面上的按钮 --------------------------------------------------------------------------------------


def test_cli_check_and_cut(tmp_path: Path, fake_ffmpeg: Path, monkeypatch) -> None:
    """pv2.py hook：--check 只数表里的 Hook；不带就切，进度一行一行打到 stderr，结果是 qa 的 JSON。"""
    import subprocess

    monkeypatch.setenv("PV2_NO_HOOK_ASR", "1")
    base = project(tmp_path, [("我每个月花四百", 1.4, 4.0)])
    pv2 = Path(hookcut.__file__).with_name("pv2.py")
    done = subprocess.run([sys.executable, str(pv2), "hook", str(base), "--check"], capture_output=True, text=True)
    assert done.returncode == 0 and json.loads(done.stdout) == {"hooks": 1}
    done = subprocess.run([sys.executable, str(pv2), "hook", str(base)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert "STAGE 切 h1" in done.stderr and json.loads(done.stdout)["clips"][0]["id"] == "h1"
    assert (base / "part-a-hook" / "individual" / "h1.mp4").is_file()
    (base / "analysis" / "worktable.json").unlink()
    done = subprocess.run([sys.executable, str(pv2), "hook", str(base), "--check"], capture_output=True, text=True)
    assert done.returncode == 2 and "ERROR 还没有标好的 Hook" in done.stderr
