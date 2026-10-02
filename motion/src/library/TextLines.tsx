// 逐行出现的要点：每行在 ats[i]（他说出这行的时刻）从下方 18px、带一点模糊滑入。accent 里的行用朱红。
import React from 'react';
import { Card, Kicker, useU } from '../kit/Card';
import { E, lerp, seg } from '../kit/Motion';
import { useSec } from '../kit/time';
import { INK, RED } from '../kit/theme';

export type TextLinesProps = { t0: number; kicker?: string; lines: string[]; ats: number[]; accent?: number[] };

export const TextLines: React.FC<TextLinesProps> = ({ t0, kicker, lines, ats, accent = [] }) => {
  const u = useU();
  const now = useSec(t0);
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      {lines.map((line, i) => {
        const p = seg(now, ats[i], ats[i] + 0.3, E.outCubic);
        return (
          <div key={i} style={{
            fontSize: u(i === 0 ? 46 : 40), fontWeight: i === 0 ? 700 : 600, lineHeight: 1.3, marginTop: u(i === 0 ? 0 : 14),
            color: accent.includes(i) ? RED : INK, opacity: p, transform: `translateY(${lerp(p, u(18), 0)}px)`,
            filter: `blur(${lerp(p, 6, 0)}px)`,
          }}>{line}</div>
        );
      })}
    </Card>
  );
};
