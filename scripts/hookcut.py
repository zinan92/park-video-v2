"""切 Hook（10/19 Park，10/21 从内容工作台搬进 park-video-v2）：照标好的 Hook，从粗剪原画面切出 h1.mp4…hN.mp4，拖进剪映自己拼。

命令行：pv2.py hook <项目> [--check] [--no-burned-captions]。

10/19 那条「请主动让AI夺舍你的身体」是在 Claude 里手做的：走完整 14 步要把正文 4K 重编码 10 分钟，
他嫌慢；只切 Hook 18 秒就好。这里把那次的做法固定下来，不做 content map、不碰正文、不加动效：

1. 读 analysis/worktable.json 里他标的 Hook（原话 + 大概在哪几秒）。
2. 原话对到词级时间 subtitles/words.json（没有就用本仓库的 align_srt.py 拿 SRT 对齐出一份）。
   只在这条 Hook 的大概位置附近找——同一句话前面可能说过。
3. 切点挪到声音的停顿上（10ms 音量包络）：句前有空白就切在开口前 50ms，连读就切在最低的那一下。
4. 切出来的片段再识别一遍，看首字、尾字对不对：多了上一句的字就往里挪一个停顿，少了字就往外挪，
   最多挪 3 次；认不出来（繁体、四万 / 4万 这种）就不动，记一条让他自己听。
5. 画面照原样（宽超过 1920 就等比缩到 1920），h264 CRF 18 / AAC 48k，首尾 15ms 淡入淡出——
   和 10/19 他认可的那批一样。全部切完才挪进 part-a-hook/individual/，最后写 edit.json：
   中途失败不会让「剪 Hook 片段」那一块看起来做完了。

剪映烧录的字幕切不掉：Hook 开头落在一条字幕中间，开头那不到一秒会显示上一句的字。这种记进 qa.json。
"""
from __future__ import annotations

import array
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Callable

FRAME = 0.01  # 包络一格 10ms
RATE = 16000
FADE = 0.015
MAX_WIDTH = 1920
QUIET_DB = -45.0  # 低于这个算停顿（剪映粗剪的底噪在 -65 上下）
LEAD = 0.05  # 停顿里切：开口前 / 收声后各留 50ms
SEARCH = 0.6  # 对齐时间前后各找这么远的切点
MAX_MOVES = 3
BISECT = 2  # 过了的切点和上一个没过的之间再对半试几次
ANCHOR_MARGIN = 6.0  # 原话只在 start_hint/end_hint 前后这么多秒里找

NO_ASR_ENVS = ("PV2_NO_HOOK_ASR", "CONTENT_STUDIO_NO_HOOK_ASR")   # 设了就不复核（测试里用）
WHISPER_MODEL_ENVS = ("PV2_WHISPER_MODEL", "CONTENT_STUDIO_WHISPER_MODEL")
DEFAULT_WHISPER_MODEL = "mlx-community/whisper-large-v3-turbo"
VIDEO_SUFFIXES = (".mp4", ".mov", ".m4v")
SKIP_DIRS = {"part-a-hook", "part-b-body", "final", "renders", "tmp", "node_modules", "subtitles", "v2"}
ALIGN = Path(__file__).resolve().parent / "align_srt.py"

Asr = Callable[[Path], str]


class HookCutError(RuntimeError):
    """说给 Park 看的一句话。"""


def find_video(base: Path) -> Path | None:
    """项目根目录下最大的那个视频文件。中间产物目录不看。"""
    found = [p for p in base.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES]
    for sub in base.iterdir():
        if sub.is_dir() and sub.name not in SKIP_DIRS and not sub.name.startswith("."):
            found += [p for p in sub.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_SUFFIXES]
    return max(found, key=lambda p: p.stat().st_size) if found else None


def find_srt(base: Path) -> Path | None:
    """先看约定位置，再看根目录（剪映导出的 SRT 通常和视频并排），再看 final/。"""
    fixed = base / "subtitles" / "source.srt"
    if fixed.is_file():
        return fixed
    loose = sorted(p for p in base.iterdir() if p.is_file() and p.suffix.lower() == ".srt")
    final = base / "final"
    if not loose and final.is_dir():
        loose = sorted(p for p in final.iterdir() if p.is_file() and p.suffix.lower() == ".srt")
    return loose[0] if loose else None


# -- 1. 读他标的 Hook -----------------------------------------------------------

def picked(base: Path) -> list[dict[str, Any]]:
    path = base / "analysis" / "worktable.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise HookCutError("还没有标好的 Hook：先在表里标好，点「保存到项目」") from None
    hooks = [h for h in data.get("hooks") or [] if str(h.get("text") or "").strip()]
    if not hooks:
        raise HookCutError("表里没有标 Hook")
    return sorted(hooks, key=lambda h: (h.get("order") or h.get("slot") or 0))


# -- 2. 原话对到词级时间 ---------------------------------------------------------

def _norm(text: str) -> str:
    return re.sub(r"[^\w]", "", text).lower()


def locate(words: list[dict[str, Any]], quote: str, near: tuple[float, float] | None = None) -> tuple[int, int] | None:
    """原话首字、尾字是 words 里第几个词。near 给了就只认落在那个范围里的那一处。"""
    clean = _norm(quote)
    if not clean:
        return None
    flat, index = [], []
    for i, w in enumerate(words):
        for ch in _norm(str(w.get("w") or "")):
            flat.append(ch)
            index.append(i)
    stream = "".join(flat)
    best: tuple[float, tuple[int, int]] | None = None
    at = stream.find(clean)
    while at >= 0:
        span = (index[at], index[at + len(clean) - 1])
        t = float(words[span[0]]["start"])
        if near is None:
            return span
        lo, hi = near
        if lo - ANCHOR_MARGIN <= t <= hi + ANCHOR_MARGIN:
            gap = abs(t - lo)
            if best is None or gap < best[0]:
                best = (gap, span)
        at = stream.find(clean, at + 1)
    return best[1] if best else None


def load_words(base: Path, video: Path, *, align: Callable[[Path, Path, Path], None] | None = None) -> list[dict[str, Any]]:
    """subtitles/words.json；没有就拿 SRT 对齐出一份（skill 的 align_srt.py，10 分钟约 40 秒）。"""
    path = base / "subtitles" / "words.json"
    if not path.is_file():
        srt = find_srt(base)
        if srt is None:
            raise HookCutError("项目里没有字幕，也没有词级时间：先转写")
        (align or align_srt)(video, srt, path)
    try:
        words = json.loads(path.read_text(encoding="utf-8")).get("words") or []
    except (OSError, ValueError):
        raise HookCutError(f"读不了词级时间：{path}") from None
    if not words:
        raise HookCutError("词级时间是空的：重新转写一遍")
    return words


def align_srt(video: Path, srt: Path, out: Path) -> None:
    done = subprocess.run([sys.executable, str(ALIGN), str(video), str(srt), str(out)], capture_output=True, text=True, timeout=900)
    if done.returncode != 0 or not out.is_file():
        raise HookCutError(f"字幕对齐音频失败：{(done.stderr or done.stdout).strip()[-300:]}")


# -- 3. 声音的停顿 ---------------------------------------------------------------

def envelope(pcm: bytes) -> list[float]:
    """16k 单声道 s16le → 每 10ms 一个 dB 值。"""
    samples = array.array("h")
    samples.frombytes(pcm[: len(pcm) // 2 * 2])
    step = int(RATE * FRAME)
    out = []
    for i in range(0, len(samples) - step + 1, step):
        chunk = samples[i:i + step]
        rms = math.sqrt(sum(x * x for x in chunk) / step)
        out.append(20 * math.log10(max(rms, 1.0) / 32768))
    return out


def cut_points(env: list[float], t0: float, t1: float, side: str) -> list[float]:
    """[t0, t1] 里能下刀的地方，按时间排。停顿：start 切在开口前 50ms、end 切在收声后 50ms；连读：最低的那一下。"""
    lo, hi = max(0, int(round(t0 / FRAME))), min(len(env) - 1, int(round(t1 / FRAME)))
    points: list[float] = []
    i = lo
    while i <= hi:
        if env[i] < QUIET_DB:
            j = i
            while j + 1 < len(env) and env[j + 1] < QUIET_DB:
                j += 1
            k = i
            while k - 1 >= 0 and env[k - 1] < QUIET_DB:
                k -= 1
            if j - k >= 4:  # 至少 50ms 的停顿
                at = (j + 1) * FRAME - LEAD if side == "start" else k * FRAME + LEAD
                at = min(max(at, k * FRAME), (j + 1) * FRAME)
                points.append(round(at, 3))  # 停顿只要碰到窗口就算：开口点可能在窗口外一点
                i = j + 1
                continue
        # 连读里的一下低谷：比两边 150ms 内的峰都低 10dB 以上，且是前后 50ms 里最低
        a, b = max(0, i - 15), min(len(env), i + 16)
        if (env[i] == min(env[max(0, i - 5):i + 6]) and max(env[a:i] or [env[i]]) - env[i] >= 10
                and max(env[i + 1:b] or [env[i]]) - env[i] >= 10):
            points.append(round(i * FRAME + FRAME / 2, 3))
            i += 5
            continue
        i += 1
    return sorted(set(points))


def snap(env: list[float], t: float, reach: float = 0.05) -> float:
    """对齐时间附近 ±50ms 里最安静的那一格：连读时就切在这里。"""
    lo, hi = max(0, int(round((t - reach) / FRAME))), min(len(env) - 1, int(round((t + reach) / FRAME)))
    if lo > hi:
        return round(t, 3)
    return round(min(range(lo, hi + 1), key=lambda i: env[i]) * FRAME + FRAME / 2, 3)


def _level(env: list[float], t: float) -> float:
    return env[min(max(0, int(t / FRAME)), len(env) - 1)] if env else 0.0


def candidates(env: list[float], aligned: float, t0: float, t1: float, side: str) -> tuple[list[float], int]:
    """能下刀的地方（停顿 + 对齐时间本身），和先试哪一个：离对齐时间 120ms 内有停顿就用停顿，没有就用对齐时间。"""
    pauses = cut_points(env, t0, t1, side)
    here = snap(env, aligned)
    close = [p for p in pauses if abs(p - aligned) <= 0.12]
    first = min(close, key=lambda p: abs(p - aligned)) if close else here
    points = sorted({*pauses, first} if close else {*pauses, here})
    return points, points.index(first)


# -- 4. 切出来再听一遍 -----------------------------------------------------------

def check(heard: str, quote: str, n: int = 2) -> tuple[int, int]:
    """(首, 尾)：0 = 对；>0 = 多了上一句 / 下一句的字；<0 = 少了原话的字；99 = 认不出来（繁体、四万 / 4万）。"""
    h, q = _norm(heard), _norm(quote)
    if not h or len(q) < n:
        return 99, 99

    def side(hs: str, qs: str) -> int:
        head = qs[:n]
        at = hs.find(head)
        if 0 <= at <= 4:
            return at
        miss = qs.find(hs[:n])
        if 0 < miss <= 6:
            return -miss
        return 99

    return side(h, q), side(h[::-1], q[::-1])


def refine(env: list[float], start: float, end: float, quote: str, *, cut: Callable[[float, float], Path], asr: Asr | None,
           floor: float = 0.0, ceil: float | None = None) -> tuple[float, float, list[str]]:
    """把对齐时间挪到停顿上，再切出来听首尾字。返回 (start, end, 要他注意的话)。

    每次只往该挪的方向挪一个切点，试过的不再试：认不准的时候来回跳，就停在最后一次、记一条让他听。"""
    ceil = ceil if ceil is not None else len(env) * FRAME
    starts, si = candidates(env, start, max(floor, start - SEARCH), min(start + SEARCH, end - 0.5), "start")
    ends, ei = candidates(env, end, max(end - SEARCH, start + 0.5), min(end + SEARCH, ceil), "end")
    notes: list[str] = []
    if asr is None:
        return starts[si], ends[ei], notes
    tried_s, tried_e = {si}, {ei}
    s, e = starts[si], ends[ei]
    bad_s = bad_e = None  # 上一个没过的切点：过了以后在两者中间再试，切得更贴
    head = tail = 99
    for _ in range(MAX_MOVES + 1):
        head, tail = check(asr(cut(s, e)), quote)
        moved = False
        if head not in (0, 99):
            nxt = si + (1 if head > 0 else -1)
            if 0 <= nxt < len(starts) and nxt not in tried_s and starts[nxt] < e - 0.5:
                bad_s, si, s, moved = s, nxt, starts[nxt], True
                tried_s.add(nxt)
        if tail not in (0, 99):
            nxt = ei + (-1 if tail > 0 else 1)
            if 0 <= nxt < len(ends) and nxt not in tried_e and ends[nxt] > s + 0.5:
                bad_e, ei, e, moved = e, nxt, ends[nxt], True
                tried_e.add(nxt)
        if not moved:
            break
    else:
        head, tail = check(asr(cut(s, e)), quote)
    for _ in range(BISECT):  # 切点已经在停顿里就不用再试；只往不比现在更响的地方挪，不切进一个字的中间
        if head == 0 and bad_s is not None and _level(env, s) >= QUIET_DB and abs(s - bad_s) > 0.06:
            mid = snap(env, (s + bad_s) / 2, 0.03)
            if _level(env, mid) <= _level(env, s) + 6 and check(asr(cut(mid, e)), quote)[0] == 0:
                s = mid
            else:
                bad_s = mid
        if tail == 0 and bad_e is not None and _level(env, e) >= QUIET_DB and abs(e - bad_e) > 0.06:
            mid = snap(env, (e + bad_e) / 2, 0.03)
            if _level(env, mid) <= _level(env, e) + 6 and check(asr(cut(s, mid)), quote)[1] == 0:
                e = mid
            else:
                bad_e = mid
    say = {99: "没认出来，听一下", 1: "可能带了{}的半个字，听一下", -1: "可能吃掉了一个字，听一下"}
    for where, other, got in (("开头", "上一句", head), ("结尾", "下一句", tail)):
        if got:
            notes.append(where + say[99 if got == 99 else (1 if got > 0 else -1)].format(other))
    return s, e, notes


# -- 剪映烧录字幕 ----------------------------------------------------------------

def cues(srt: Path | None) -> list[dict[str, Any]]:
    if srt is None or not srt.is_file():
        return []

    def sec(t: str) -> float:
        h, m, s = t.strip().replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    out = []
    for block in re.split(r"\n\s*\n", srt.read_text(encoding="utf-8-sig").strip()):
        rows = [r.strip() for r in block.splitlines() if r.strip()]
        timing = next((r for r in rows if "-->" in r), None)
        if not timing:
            continue
        a, b = timing.split("-->")
        try:
            out.append({"start": sec(a), "end": sec(b), "text": "".join(r for r in rows if "-->" not in r and not r.isdigit())})
        except ValueError:
            continue
    return out


def caption_overlap(captions: list[dict[str, Any]], start: float, quote: str) -> dict[str, Any] | None:
    """开头落在一条字幕中间、那条字幕前面还有上一句的字：烧录的字切不掉，开头会闪一下。

    字幕正好从原话第一个字开始（只是对齐差了一点）不算。"""
    head = _norm(quote)[:2]
    for c in captions:
        if c["start"] + 0.1 < start < c["end"] - 0.05:
            text = _norm(c["text"])
            at = text.find(head) if head else -1
            if at == 0:
                return None
            extra = c["text"] if at < 0 else _leading(c["text"], at)
            return {"text": c["text"], "extra": extra, "seconds": round(c["end"] - start, 2)}
    return None


def _leading(text: str, chars: int) -> str:
    """text 里前 chars 个（去标点后的）字，原样带标点。"""
    seen = 0
    for i, ch in enumerate(text):
        if _norm(ch):
            if seen == chars:
                return text[:i]
            seen += 1
    return text


# -- 5. ffmpeg -------------------------------------------------------------------

def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise HookCutError("这台机器上没有 ffmpeg：brew install ffmpeg")
    return exe


def read_pcm(video: Path) -> bytes:
    done = subprocess.run([_ffmpeg(), "-v", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", str(RATE), "-f", "s16le", "-"],
                          capture_output=True, timeout=600)
    if done.returncode != 0 or not done.stdout:
        raise HookCutError(f"读不出粗剪的声音：{done.stderr.decode('utf-8', 'replace').strip()[-200:]}")
    return done.stdout


def export(video: Path, start: float, end: float, out: Path) -> None:
    """原画面（宽超过 1920 等比缩到 1920），h264 CRF 18 / AAC 48k，首尾 15ms 淡入淡出。"""
    dur = end - start
    args = [_ffmpeg(), "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", str(video), "-t", f"{dur:.3f}",
            "-vf", f"scale='min({MAX_WIDTH},iw)':-2:flags=lanczos,format=yuv420p,setsar=1",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-g", "60",
            "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
            "-af", f"afade=t=in:d={FADE},afade=t=out:st={max(dur - FADE, 0):.3f}:d={FADE}",
            "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k", "-movflags", "+faststart", str(out)]
    done = subprocess.run(args, capture_output=True, text=True, timeout=600)
    if done.returncode != 0 or not out.is_file():
        raise HookCutError(f"切 {out.stem} 失败：{(done.stderr or '').strip()[-200:]}")


def listen(video: Path, start: float, end: float, out: Path) -> Path:
    """只要声音，给重新识别用（比切视频快得多）。"""
    done = subprocess.run([_ffmpeg(), "-v", "error", "-y", "-ss", f"{start:.3f}", "-i", str(video), "-t", f"{end - start:.3f}",
                           "-vn", "-ac", "1", "-ar", str(RATE), str(out)], capture_output=True, text=True, timeout=120)
    if done.returncode != 0:
        raise HookCutError(f"切声音失败：{(done.stderr or '').strip()[-200:]}")
    return out


def whisper_asr() -> Asr | None:
    """本机 mlx-whisper；没有就不复核，只靠包络（qa.json 里会写明）。测试里一律关掉（conftest 设 NO_ASR_ENV）。"""
    if any(os.environ.get(k) for k in NO_ASR_ENVS):
        return None
    try:
        import mlx_whisper
    except ImportError:
        return None
    model = next((os.environ[k] for k in WHISPER_MODEL_ENVS if os.environ.get(k)), DEFAULT_WHISPER_MODEL)

    def asr(path: Path) -> str:
        result = mlx_whisper.transcribe(str(path), path_or_hf_repo=model, language="zh", verbose=None,
                                        initial_prompt="以下是普通话的句子。", condition_on_previous_text=False)
        return str(result.get("text") or "")

    return asr


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# -- 整条 -------------------------------------------------------------------------

def run(base: Path, *, asr: Asr | None | str = "auto", captions_burned_in: bool = True,
        progress: Callable[[str], None] = lambda _s: None) -> dict[str, Any]:
    """切 h1…hN，写 edit.json / qa.json。返回 qa（给页面看要注意的地方）。视频在 iCloud 上没下到本机的，调用方先下好。"""
    hooks = picked(base)
    video = find_video(base)
    if video is None:
        raise HookCutError("项目里没有粗剪")
    progress("对词级时间")
    words = load_words(base, video)
    progress("读声音")
    env = envelope(read_pcm(video))
    listen_fn: Asr | None = whisper_asr() if asr == "auto" else asr  # type: ignore[assignment]
    captions = cues(find_srt(base)) if captions_burned_in else []

    out_dir = base / "part-a-hook"
    work = out_dir / ".work"
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    clips, flags = [], []
    try:
        for n, hook in enumerate(hooks, 1):
            cid, quote = f"h{n}", str(hook["text"]).strip()
            progress(f"切 {cid}")
            anchor = hook.get("anchor") or {}
            near = (float(anchor["start_hint"]), float(anchor.get("end_hint") or anchor["start_hint"])) if anchor.get("start_hint") is not None else None
            span = locate(words, quote, near)
            notes: list[str] = []
            if span is None:
                if near is None:
                    raise HookCutError(f"{cid}「{quote[:12]}…」在逐字稿里找不到：回表里重新标一下")
                start, end = near
                notes.append("原话和词级时间对不上，用的是字幕的大概时间，听一下首尾")
                floor, ceil = 0.0, None
            else:
                start, end = float(words[span[0]]["start"]), float(words[span[1]]["end"])
                floor = float(words[span[0] - 1]["start"]) if span[0] > 0 else 0.0
                ceil = float(words[span[1] + 1]["end"]) if span[1] + 1 < len(words) else None
            sound = work / f"{cid}.wav"
            start, end, more = refine(env, start, end, quote, cut=lambda s, e: listen(video, s, e, sound), asr=listen_fn,
                                      floor=floor, ceil=ceil)
            sound.unlink(missing_ok=True)
            notes += more
            over = caption_overlap(captions, start, quote)
            if over:
                notes.append(f"开头 {over['seconds']} 秒的烧录字幕是「{over['text']}」，带着「{over['extra']}」，切不掉")
            export(video, start, end, work / f"{cid}.mp4")
            clips.append({"id": cid, "quote": quote, "start": round(start, 2), "end": round(end, 2)})
            if notes:
                flags.append({"id": cid, "notes": notes})
        progress("放进 part-a-hook")
        target = out_dir / "individual"
        if target.is_dir():
            for old in target.glob("h*.mp4"):
                if re.fullmatch(r"h\d+", old.stem):
                    old.unlink()
        target.mkdir(parents=True, exist_ok=True)
        for clip in clips:
            (work / f"{clip['id']}.mp4").replace(target / f"{clip['id']}.mp4")
    finally:
        shutil.rmtree(work, ignore_errors=True)
    qa = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
          "method": "词级对齐 + 10ms 音量包络" + (" + 对切出的声音重新识别首尾字" if listen_fn else "（这台机器没有 mlx-whisper，没有重新识别）"),
          "spec": f"原画面（宽 ≤ {MAX_WIDTH} 等比缩）h264 CRF 18 / AAC 48k，首尾 {int(FADE * 1000)}ms 淡入淡出",
          "flags": flags}
    (out_dir / "qa.json").write_text(json.dumps(qa, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    edit = {"source": video.name, "source_sha256": _sha(video), "timeline": f"rough-cut seconds ({video.name})",
            "order": [c["id"] for c in clips], "fade_s": FADE, "clips": clips}
    (out_dir / "edit.json").write_text(json.dumps(edit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**qa, "clips": clips}
