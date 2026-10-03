// 马克笔引用（effort c · 文字）：形态取自 ShotCraft 的 marker-underline-title + blur-slide。
// 动作弧：
//   大引号从放大、模糊、略倾斜的状态压下来落定（0.4s，强减速）；
//   每行在它的 at 逐字从下方带模糊升起（间隔越来越短）；
//   accent 里的行：字出齐后，一支强调色马克笔从左往右涂过字的下半截——笔触是两道略有起伏、深浅不同的笔画叠在一起，
//   像真的手涂（0.5s，先快后慢）。最后一行后约 0.9s 做完，之后一帧不动。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { emWidth } from '../kit/Card';
import { fit, Kinetic, tint } from '../kit/parts';
import { useSec } from '../kit/time';

export type QuoteMarkerProps = { t0: number; lines: string[]; ats: number[]; accent?: number[] };

// 一道手涂笔画：宽 w、高 h 的波浪带，起伏 amp（像马克笔压力不均）
const stroke = (w: number, h: number, amp: number, phase: number) => {
  const n = 6;
  const top = Array.from({ length: n + 1 }, (_, i) => `${(w * i) / n},${h * 0.18 + Math.sin(i * 1.7 + phase) * amp}`);
  const bot = Array.from({ length: n + 1 }, (_, i) => `${(w * (n - i)) / n},${h * 0.86 + Math.sin((n - i) * 1.3 + phase + 1) * amp}`);
  return `M ${top.join(' L ')} L ${bot.join(' L ')} Z`;
};

export const QuoteMarker: React.FC<QuoteMarkerProps> = ({ t0, lines, ats, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const avail = useInnerWidth() - u(10);
  const q = seg(now, ats[0], ats[0] + 0.4, E.outExpo);
  return (
    <Card>
      <div style={{ fontSize: u(160), lineHeight: 0.6, height: u(74), fontWeight: 900, color: look.accent, fontFamily: 'Georgia, serif',
        opacity: seg(now, ats[0], ats[0] + 0.12), transformOrigin: 'left top',
        transform: q >= 1 ? 'none' : `scale(${lerp(q, 1.7, 1)}) rotate(${lerp(q, -12, 0)}deg)`, filter: q < 0.9 ? `blur(${lerp(q, 8, 0)}px)` : 'none' }}>“</div>
      {lines.map((line, i) => {
        const size = fit(line, u(i === 0 ? 84 : 72), avail);
        const hot = accent.includes(i);
        const chars = [...line].length;
        const done = ats[i] + 0.04 * chars + 0.3;
        const m = seg(now, done, done + 0.5, E.outQuart);
        const w = emWidth(line) * size;
        return (
          <div key={i} style={{ marginTop: u(i ? 12 : 8), minHeight: size * 1.2 }}>
            <span style={{ position: 'relative', display: 'inline-block', whiteSpace: 'nowrap', fontSize: size, fontWeight: 900, lineHeight: 1.2, color: look.ink }}>
              {hot && m > 0 ? (
                <svg width={w * 1.06} height={size * 0.62} style={{ position: 'absolute', left: -w * 0.03, bottom: size * 0.02, overflow: 'visible' }}>
                  <defs><clipPath id={`mk${i}`}><rect x={0} y={-size} width={w * 1.06 * m} height={size * 3} /></clipPath></defs>
                  <g clipPath={`url(#mk${i})`}>
                    <path d={stroke(w * 1.06, size * 0.62, size * 0.035, 0.4)} fill={tint(look.accent, 0.32)} />
                    <path d={stroke(w * 1.06, size * 0.5, size * 0.03, 2.1)} transform={`translate(0 ${size * 0.08})`} fill={tint(look.accent, 0.22)} />
                  </g>
                </svg>
              ) : null}
              <span style={{ position: 'relative' }}><Kinetic text={line} now={now} at={ats[i]} gap={0.04} rise={size * 0.3} dur={0.36} /></span>
            </span>
          </div>
        );
      })}
    </Card>
  );
};
