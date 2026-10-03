// 逐行出现的要点：每行在 ats[i]（他说出这行的时刻）从下方 18px、带一点模糊滑入。accent 里的行用强调色。
// 每行不折行：字号按卡片宽度自动定，第一行最大 96u、其余最大 72u（一张卡一个重点时就是大字）。
import React from 'react';
import { Card, emWidth, Kicker, useInnerWidth, useU } from '../kit/Card';
import { E, lerp, seg } from '../kit/Motion';
import { useSec } from '../kit/time';
import { useLook } from '../kit/look';

export type TextLinesProps = { t0: number; kicker?: string; lines: string[]; ats: number[]; accent?: number[] };

export const TextLines: React.FC<TextLinesProps> = ({ t0, kicker, lines, ats, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const size = (line: string, i: number) => Math.min(u(i === 0 ? 96 : 72), Math.floor(inner / Math.max(1, emWidth(line))));
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      {lines.map((line, i) => {
        const p = seg(now, ats[i], ats[i] + 0.3, E.outCubic);
        return (
          <div key={i} style={{
            fontSize: size(line, i), fontWeight: i === 0 ? 800 : 700, lineHeight: 1.25, marginTop: u(i === 0 ? 0 : 14), whiteSpace: 'nowrap',
            color: accent.includes(i) ? look.accent : look.ink, opacity: p, transform: `translateY(${lerp(p, u(18), 0)}px)`,
            filter: `blur(${lerp(p, 6, 0)}px)`,
          }}>{line}</div>
        );
      })}
    </Card>
  );
};
