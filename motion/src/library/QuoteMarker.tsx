// 马克笔引用（effort c · 文字）：形态取自 ShotCraft 的 marker-underline-title + blur-slide。
// 大引号先弹出；每行在它的 at 从下方带模糊滑入；accent 里的行，滑入后一支强调色马克笔从左到右涂过字的下半截（0.45s）。
// 最后一行后 0.8s 内做完。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit, tint } from '../kit/parts';
import { useSec } from '../kit/time';

export type QuoteMarkerProps = { t0: number; lines: string[]; ats: number[]; accent?: number[] };

export const QuoteMarker: React.FC<QuoteMarkerProps> = ({ t0, lines, ats, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const avail = useInnerWidth() - u(10);
  const q = seg(now, ats[0], ats[0] + 0.35, look.pop);
  return (
    <Card>
      <div style={{ fontSize: u(150), lineHeight: 0.6, height: u(70), fontWeight: 900, color: look.accent, fontFamily: 'Georgia, serif',
        opacity: seg(now, ats[0], ats[0] + 0.15), transform: `scale(${lerp(q, 0.4, 1)})`, transformOrigin: 'left top' }}>“</div>
      {lines.map((line, i) => {
        const p = seg(now, ats[i], ats[i] + 0.35, E.outCubic);
        const m = seg(now, ats[i] + 0.3, ats[i] + 0.75, E.inOutCubic);
        const hot = accent.includes(i);
        return (
          <div key={i} style={{ marginTop: u(i ? 12 : 8), opacity: p, transform: `translateY(${lerp(p, u(22), 0)}px)`, filter: `blur(${lerp(p, 7, 0)}px)` }}>
            <span style={{ position: 'relative', display: 'inline-block', whiteSpace: 'nowrap', fontSize: fit(line, u(i === 0 ? 82 : 70), avail),
              fontWeight: 900, lineHeight: 1.2, color: look.ink }}>
              {hot ? <span style={{ position: 'absolute', left: '-2%', bottom: '6%', height: '40%', width: `${104 * m}%`, borderRadius: u(6),
                background: tint(look.accent, 0.38) }} /> : null}
              <span style={{ position: 'relative' }}>{line}</span>
            </span>
          </div>
        );
      })}
    </Card>
  );
};
