// 编号步骤：第 i 项在 ats[i] 出现，编号圆点先弹出、文字随后滑入。只表示先后，不画时间刻度。
import React from 'react';
import { Card, Kicker, useU } from '../kit/Card';
import { E, lerp, seg } from '../kit/Motion';
import { useSec } from '../kit/time';
import { RED } from '../kit/theme';

export type ListStepsProps = { t0: number; kicker?: string; items: string[]; ats: number[] };

export const ListSteps: React.FC<ListStepsProps> = ({ t0, kicker, items, ats }) => {
  const u = useU();
  const now = useSec(t0);
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      {items.map((item, i) => {
        const dot = seg(now, ats[i], ats[i] + 0.25, E.outBack);
        const txt = seg(now, ats[i] + 0.08, ats[i] + 0.38, E.outCubic);
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', marginTop: u(i ? 22 : 4) }}>
            <div style={{ width: u(52), height: u(52), borderRadius: '50%', background: RED, color: 'white', fontSize: u(28),
              fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              transform: `scale(${dot})` }}>{i + 1}</div>
            <div style={{ fontSize: u(38), fontWeight: 600, marginLeft: u(20), opacity: txt,
              transform: `translateX(${lerp(txt, u(16), 0)}px)` }}>{item}</div>
          </div>
        );
      })}
    </Card>
  );
};
