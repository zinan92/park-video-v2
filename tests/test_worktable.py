"""标 Hook 的表（10/21 从 ask-park-video 搬来）：pv2.py worktable 把字幕变成 analysis/worktable.html。"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import hookcut

SRT = "1\n00:00:00,000 --> 00:00:02,400\n我每个月花四百。\n\n2\n00:00:02,400 --> 00:00:04,000\n记住了。\n"


def test_worktable_from_project_srt(tmp_path: Path) -> None:
    base = tmp_path / "p"
    (base / "subtitles").mkdir(parents=True)
    (base / "subtitles" / "source.srt").write_text(SRT, encoding="utf-8")
    pv2 = Path(hookcut.__file__).with_name("pv2.py")
    done = subprocess.run([sys.executable, str(pv2), "worktable", str(base)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    html = (base / "analysis" / "worktable.html").read_text(encoding="utf-8")
    assert "我每个月花四百" in html
    rows = json.loads((base / "subtitles" / "transcript.sentences.json").read_text(encoding="utf-8"))["transcript"]
    assert len(rows) == 2


def test_worktable_without_srt_says_so(tmp_path: Path) -> None:
    pv2 = Path(hookcut.__file__).with_name("pv2.py")
    (tmp_path / "p").mkdir()
    done = subprocess.run([sys.executable, str(pv2), "worktable", str(tmp_path / "p")], capture_output=True, text=True)
    assert done.returncode == 1 and "没有 SRT" in done.stderr


# 剪映导出的 SRT 没有标点（11/8 一条 15 分钟口播）：按 SRT 断句要么整条一句、要么一条字幕一行，都没法标 Hook。
# 正确的句子来自 AI 先写的校对稿（只加标点），10/21 搬进 pv2 时这一步丢了。
BARE_SRT = (
    "1\n00:00:00,800 --> 00:00:01,866\n首先感谢大家\n\n"
    "2\n00:00:01,866 --> 00:00:03,300\n我这个号粉丝终于破万了\n\n"
    "3\n00:00:03,300 --> 00:00:05,266\n就不管头像介绍这些都没有\n"
)
PV2 = Path(hookcut.__file__).with_name("pv2.py")


def _bare_project(tmp_path: Path) -> Path:
    base = tmp_path / "p"
    base.mkdir()
    (base / "a.srt").write_text(BARE_SRT, encoding="utf-8")
    return base


def test_worktable_srt_without_punctuation_asks_for_corrected_text(tmp_path: Path) -> None:
    base = _bare_project(tmp_path)
    done = subprocess.run([sys.executable, str(PV2), "worktable", str(base)], capture_output=True, text=True)
    assert done.returncode == 1
    assert "transcript.corrected.txt" in done.stderr and "只加标点" in done.stderr
    assert not (base / "analysis" / "worktable.html").exists()


def test_worktable_reads_corrected_text_from_project(tmp_path: Path) -> None:
    base = _bare_project(tmp_path)
    (base / "subtitles").mkdir()
    (base / "subtitles" / "transcript.corrected.txt").write_text(
        "首先感谢大家，我这个号粉丝终于破万了。\n就不管头像介绍这些都没有。\n", encoding="utf-8")
    done = subprocess.run([sys.executable, str(PV2), "worktable", str(base)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    doc = json.loads((base / "subtitles" / "transcript.sentences.json").read_text(encoding="utf-8"))
    assert [r["text"] for r in doc["transcript"]] == ["首先感谢大家，我这个号粉丝终于破万了。", "就不管头像介绍这些都没有。"]
    assert [r["start_hint"] for r in doc["transcript"]] == [0.8, 3.3]
    assert doc["text_source"].endswith("transcript.corrected.txt")


def test_map_without_punctuation_falls_back_to_one_row_per_cue(tmp_path: Path) -> None:
    base = _bare_project(tmp_path)
    out = tmp_path / "s.json"
    script = PV2.with_name("build_worktable.py")
    done = subprocess.run([sys.executable, str(script), "map", "--srt", str(base / "a.srt"), "-o", str(out)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    rows = json.loads(out.read_text(encoding="utf-8"))["transcript"]
    assert [r["text"] for r in rows] == ["首先感谢大家", "我这个号粉丝终于破万了", "就不管头像介绍这些都没有"]
