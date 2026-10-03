// 最多 3 根横条对比（图表形式）：每根在 at 出现并在 0.4s 内长到 value 对应的长度；display 是条上显示的读数（原话里的数）。
import React from 'react';
import { Card, Kicker, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { Appear, draw, fit } from '../kit/parts';
import { useSec } from '../kit/time';

type Bar = { label: string; value: number; display?: string; at: number };
export type BarsProps = { t0: number; kicker?: string; bars: Bar[]; accent?: number[] };

export const Bars: React.FC<BarsProps> = ({ t0, kicker, bars, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const max = Math.max(...bars.map((b) => b.value), 1);
  const labelSize = Math.min(...bars.map((b) => fit(b.label, u(64), inner)));
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      <div style={{ width: inner }}>
        {bars.map((b, i) => {
          const hot = accent.includes(i);
          const w = Math.max(u(70), (inner * b.value) / max) * draw(now, b.at, 0.4);
          return (
            <Appear key={i} now={now} at={b.at} rise={u(12)} style={{ marginTop: u(i ? 26 : 0) }}>
              <div style={{ fontSize: labelSize, fontWeight: 700, color: hot ? look.accent : look.ink, whiteSpace: 'nowrap' }}>{b.label}</div>
              <div style={{ marginTop: u(10), height: u(76), width: w, borderRadius: u(14), background: hot ? look.accent : look.line,
                display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: u(16), boxSizing: 'border-box',
                fontSize: u(46), fontWeight: 800, color: hot ? '#FFFFFF' : look.ink, whiteSpace: 'nowrap' }}>{b.display ?? ''}</div>
            </Appear>
          );
        })}
      </div>
    </Card>
  );
};
