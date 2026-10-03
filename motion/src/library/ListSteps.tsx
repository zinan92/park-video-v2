// 编号步骤：第 i 项在 ats[i] 出现，编号圆点先弹出、文字随后滑入。只表示先后，不画时间刻度。
import React from 'react';
import { Card, Kicker, useInnerWidth, useU } from '../kit/Card';
import { fit } from '../kit/parts';
import { E, lerp, seg } from '../kit/Motion';
import { useSec } from '../kit/time';
import { useLook } from '../kit/look';

export type ListStepsProps = { t0: number; kicker?: string; items: string[]; ats: number[] };

export const ListSteps: React.FC<ListStepsProps> = ({ t0, kicker, items, ats }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const dotW = u(64);
  const inner = useInnerWidth();
  const size = Math.min(...items.map((it) => fit(it, u(60), inner - dotW - u(24))));
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      {items.map((item, i) => {
        const dot = seg(now, ats[i], ats[i] + 0.25, look.pop);
        const txt = seg(now, ats[i] + 0.08, ats[i] + 0.38, E.outCubic);
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', marginTop: u(i ? 26 : 4) }}>
            <div style={{ width: dotW, height: dotW, borderRadius: '50%', background: look.accent, color: 'white', fontSize: u(34),
              fontWeight: 800, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              transform: `scale(${dot})` }}>{i + 1}</div>
            <div style={{ fontSize: size, fontWeight: 700, whiteSpace: 'nowrap', marginLeft: u(24), opacity: txt,
              transform: `translateX(${lerp(txt, u(16), 0)}px)` }}>{item}</div>
          </div>
        );
      })}
    </Card>
  );
};
