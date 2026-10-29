"""把字幕烧进成片：SRT（剪映导出的，或 pv2 transcribe 本机转写的）→ 按 Park 的字幕样式写成 ASS → 合成时用 ffmpeg 的 subtitles 滤镜烧进去。

烧录照 videocut:字幕 的做法（一条 ffmpeg subtitles 滤镜），样式照 ask-park-video 定过的 park-caption-4x3-v1：
苹方、浅色字、深色半透明底板跟着字宽走、底部居中、一行为主最多两行、4 帧淡入。
不要只有描边的字幕（Park 的规格里明确不要）。ffmpeg 的底板是直角，规格里的圆角和投影做不出来。
所有尺寸按 1080 高定，原片多高就按比例放大（4K 翻倍）。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any


REF_H = 1080
FONT = "PingFang SC"
FONT_PX = 40  # 规格里是 CSS 字号（一个字宽）
ASS_EM = 1.4  # ASS 的 Fontsize 是整行高（含上下留白），苹方要乘约 1.4 才和 CSS 的 40px 一样大
LINE_H = 1.24
PAD = 12  # 底板内边距（ASS 的底板四边一样宽，取规格上下左右 11–24 的中间值）
BOTTOM = 40  # 底板离画面下沿
MAX_W = 1160  # 一行最宽（px），超过就在意思断开的地方换成两行
INK = "&H00F6FDFF"  # #FFFDF6，ASS 颜色是 &HAABBGGRR
BOX = "&H290A0C09"  # rgba(9, 12, 10, 0.84)
FADE_MS = 130  # 4 帧淡入，跟着字幕切走
BREAKS = "，。！？；、：,.!?;:"


def _em(text: str) -> float:
    return sum(0.6 if ord(ch) < 256 else 1 for ch in text)


def lines(text: str, max_em: float) -> list[str]:
    """一行放得下就一行；放不下在离中间最近的标点处断，没有标点就从中间断（数字和英文单词不拆开）。最多两行。"""
    if _em(text) <= max_em:
        return [text]
    mid = len(text) / 2
    cuts = [i + 1 for i, ch in enumerate(text[:-1]) if ch in BREAKS]
    if not cuts:
        cuts = [i for i in range(1, len(text)) if not (text[i - 1].isascii() and text[i - 1].isalnum() and text[i].isascii() and text[i].isalnum())]
    at = min(cuts, key=lambda i: abs(i - mid)) if cuts else int(mid)
    return [text[:at].rstrip(), text[at:].lstrip()]


def band(canvas: list[int]) -> list[int]:
    """两行字幕连底板占的那条带（y 范围，canvas 像素）：动效要避开它。"""
    k = canvas[1] / REF_H
    bottom = canvas[1] - BOTTOM * k
    top = bottom - (2 * FONT_PX * ASS_EM + 2 * PAD) * k  # ASS 一行高 = Fontsize
    return [int(top), int(round(bottom))]


def _ts(t: float) -> str:
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def to_ass(cues: list[dict[str, Any]], size: list[int], *, start: float = 0.0, end: float | None = None) -> str:
    """cues：[{start, end, text}]（原片秒）。start / end：只要这一段（样片），时间换成从 start 起算。"""
    w, h = size
    k = h / REF_H
    max_em = min(MAX_W * k, w - 2 * (PAD + 24) * k) / (FONT_PX * k)
    side = max(0, round((w - MAX_W * k) / 2))
    head = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {w}\nPlayResY: {h}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
            "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Park,{FONT},{round(FONT_PX * ASS_EM * k)},{INK},{INK},{BOX},{BOX},1,0,0,0,100,100,0,0,3,{round(PAD * k)},0,2,"
            f"{side},{side},{round((BOTTOM + PAD) * k)},1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    rows = []
    for c in cues:
        a, z = c["start"] - start, c["end"] - start
        if end is not None:
            z = min(z, end - start)
        if z <= 0 or a >= z:
            continue
        text = r"\N".join(lines(c["text"], max_em))
        rows.append(f"Dialogue: 0,{_ts(max(a, 0.0))},{_ts(z)},Park,,0,0,0,,{{\\fad({FADE_MS},0)}}{text}")
    return head + "\n".join(rows) + "\n"


def read_srt(path: Path) -> list[dict[str, Any]]:
    """SRT → [{start, end, text}]。和 align_srt.parse_srt 不同：英文单词之间的空格留着（「high level」不粘成一个词）。"""
    def sec(t: str) -> float:
        h, m, x = t.strip().replace(",", ".").split(":")
        return int(h) * 3600 + int(m) * 60 + float(x)

    out = []
    for block in re.split(r"\n\s*\n", Path(path).read_text(encoding="utf-8-sig").strip()):
        rows = [r.strip() for r in block.splitlines() if r.strip()]
        timing = next((r for r in rows if "-->" in r), None)
        if not timing:
            continue
        text = re.sub(r"\s+", " ", " ".join(r for r in rows if r is not timing and not r.isdigit()))
        text = re.sub(r"(?<=[^\x00-\x7f]) | (?=[^\x00-\x7f])", "", text).strip()  # 汉字旁边的空格去掉，英文词之间的留着
        text = re.sub(r"[{}\\]", "", text)  # ASS 的控制字符
        if text:
            a, z = timing.split("-->")
            out.append({"start": sec(a), "end": sec(z), "text": text})
    return out


def write(srt: Path, size: list[int], out: Path, *, start: float = 0.0, end: float | None = None) -> Path:
    cues = read_srt(Path(srt))
    out.write_text(to_ass(cues, size, start=start, end=end), encoding="utf-8")
    return out
