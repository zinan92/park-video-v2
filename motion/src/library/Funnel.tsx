// 漏斗（示意图形式）：2–3 层自上而下收窄，最后一层是结论（强调色实底）。每层在 at 出现。
import React from 'react';
import { Card, Kicker, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { Appear, fit } from '../kit/parts';
import { useSec } from '../kit/time';

type Layer = { text: string; at: number };
export type FunnelProps = { t0: number; kicker?: string; layers: Layer[] };

export const Funnel: React.FC<FunnelProps> = ({ t0, kicker, layers }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const n = layers.length;
  const widths = Array.from({ length: n + 1 }, (_, i) => inner * (1 - (0.38 * i) / n));
  const H = u(132);
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      <div style={{ width: inner }}>
        {layers.map((l, i) => {
          const top = widths[i];
          const bottom = widths[i + 1];
          const inset = ((top - bottom) / 2 / top) * 100;
          const last = i === n - 1;
          return (
            <Appear key={i} now={now} at={l.at} rise={u(12)} style={{ marginTop: u(i ? 10 : 0), display: 'flex', justifyContent: 'center' }}>
              <div style={{ width: top, height: H, clipPath: `polygon(0 0, 100% 0, ${100 - inset}% 100%, ${inset}% 100%)`,
                background: last ? look.accent : look.line, display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: fit(l.text, u(64), bottom * 0.8), fontWeight: 800, whiteSpace: 'nowrap',
                color: last ? '#FFFFFF' : look.ink }}>{l.text}</div>
            </Appear>
          );
        })}
      </div>
    </Card>
  );
};
