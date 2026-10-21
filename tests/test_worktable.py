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
