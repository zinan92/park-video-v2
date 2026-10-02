#!/usr/bin/env python3
"""词级时间（有 SRT 时用这个）：拿剪映导出的 SRT 文字去对齐音频，不重新识别。

用法：python3 scripts/align_srt.py <口播视频或音频> <source.srt> <输出 words.json>
输出和 words.py 一样：{"segments": [{start,end,text}], "words": [{w,start,end}]}，秒为单位，和成片时间轴一致。

为什么不直接跑 words.py：SRT 里已经有「说了什么」和每句的时间，只缺句内每个字的时刻。
这里只做强制对齐（mlx-whisper 的 cross-attention + DTW），每 ~25 秒一次前向，不做解码，
比整条重新转写快得多；字也和字幕一字不差，动效引用的原话一定找得到。
每个字的时间会被夹回它所在那条字幕的时间范围内；某段对齐失败就在句内按字数平分。
依赖 mlx-whisper（Apple 芯片）。
"""
import json
import re
import sys
from pathlib import Path

MODEL = "mlx-community/whisper-large-v3-turbo"
WINDOW = 25.0  # 每次对齐的最长音频（秒），必须 < 30
PAD = 0.3  # 窗口前后各留一点余量


def parse_srt(path: Path) -> list[dict]:
    def sec(t: str) -> float:
        h, m, s = t.replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(s)

    cues = []
    for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8-sig").strip()):
        rows = [r.strip() for r in block.splitlines() if r.strip()]
        timing = next((r for r in rows if "-->" in r), None)
        if not timing:
            continue
        a, b = (x.strip() for x in timing.split("-->"))
        text = "".join(r for r in rows if r is not timing and not r.isdigit() and "-->" not in r)
        text = re.sub(r"\s+", "", text)
        if text:
            cues.append({"start": sec(a), "end": sec(b), "text": text})
    return cues


def windows(cues: list[dict]) -> list[list[int]]:
    groups, cur = [], []
    for i, c in enumerate(cues):
        if cur and c["end"] + PAD - (cues[cur[0]]["start"] - PAD) > WINDOW:
            groups.append(cur)
            cur = []
        cur.append(i)
    if cur:
        groups.append(cur)
    return groups


def spread(cue: dict) -> list[dict]:
    """对齐失败时的退路：句内按字数平分。"""
    chars = list(cue["text"])
    step = (cue["end"] - cue["start"]) / max(len(chars), 1)
    return [{"w": ch, "start": round(cue["start"] + i * step, 2), "end": round(cue["start"] + (i + 1) * step, 2)}
            for i, ch in enumerate(chars)]


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    import mlx.core as mx
    from mlx_whisper.audio import N_FRAMES, SAMPLE_RATE, load_audio, log_mel_spectrogram, pad_or_trim
    from mlx_whisper.load_models import load_model
    from mlx_whisper.timing import find_alignment
    from mlx_whisper.tokenizer import get_tokenizer

    src, srt, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    cues = parse_srt(srt)
    if not cues:
        print(f"{srt} 里没有字幕")
        return 1
    model = load_model(MODEL, dtype=mx.float16)
    tokenizer = get_tokenizer(model.is_multilingual, num_languages=model.num_languages, language="zh", task="transcribe")
    audio = load_audio(str(src))

    words, fallback = [], 0
    for group in windows(cues):
        first, last = cues[group[0]], cues[group[-1]]
        t0 = max(0.0, first["start"] - PAD)
        t1 = last["end"] + PAD
        clip = audio[int(t0 * SAMPLE_RATE): int(t1 * SAMPLE_RATE)]
        mel = log_mel_spectrogram(clip, n_mels=model.dims.n_mels)
        num_frames = min(mel.shape[-2], N_FRAMES)
        mel = pad_or_trim(mel, N_FRAMES, axis=-2).astype(mx.float16)
        text = "".join(cues[i]["text"] for i in group)
        try:
            timed = find_alignment(model, tokenizer, tokenizer.encode(text), mel, num_frames)
        except Exception:  # noqa: BLE001 — 一段失败不拖垮整条
            timed = []
        # 把对齐出的字按字符顺序分回各条字幕，并夹回那条字幕的时间范围
        pieces = [(t.word, t0 + float(t.start), t0 + float(t.end)) for t in timed if t.word]
        if "".join(p[0] for p in pieces) != text:
            for i in group:
                words += spread(cues[i])
            fallback += len(group)
            continue
        k = 0
        for i in group:
            cue, need = cues[i], len(cues[i]["text"])
            got = ""
            while k < len(pieces) and len(got) < need:
                w, a, b = pieces[k]
                a = min(max(a, cue["start"]), cue["end"])
                b = min(max(b, a), cue["end"])
                words.append({"w": w, "start": round(a, 2), "end": round(b, 2)})
                got += w
                k += 1

    segments = [{"start": round(c["start"], 2), "end": round(c["end"], 2), "text": c["text"]} for c in cues]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"segments": segments, "words": words, "source": "srt-aligned"}, ensure_ascii=False),
                   encoding="utf-8")
    print(f"{out}：{len(segments)} 句，{len(words)} 词（{fallback} 句对齐失败，按字数平分）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
