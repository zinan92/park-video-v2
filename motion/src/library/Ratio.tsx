// 环形比例（图表形式）：环在 at 起 0.5s 画到 value%，中间是百分数，下面一行说明。不滚数字、不冲过头。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { Appear, draw, fit } from '../kit/parts';
import { useSec } from '../kit/time';

export type RatioProps = { t0: number; value: number; at: number; caption?: string; captionAt?: number };

export const Ratio: React.FC<RatioProps> = ({ t0, value, at, caption, captionAt }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const D = Math.min(inner, u(380));
  const sw = D * 0.12;
  const r = (D - sw) / 2;
  const C = 2 * Math.PI * r;
  const p = draw(now, at) * (value / 100);
  return (
    <Card>
      <Appear now={now} at={at} rise={u(14)} style={{ position: 'relative', width: D, height: D, alignSelf: 'center' }}>
        <svg width={D} height={D} style={{ position: 'absolute', inset: 0, transform: 'rotate(-90deg)' }}>
          <circle cx={D / 2} cy={D / 2} r={r} stroke={look.line} strokeWidth={sw} fill="none" />
          <circle cx={D / 2} cy={D / 2} r={r} stroke={look.accent} strokeWidth={sw} fill="none" strokeLinecap="round"
            strokeDasharray={`${C * p} ${C}`} />
        </svg>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: D * 0.27, fontWeight: 900, color: look.ink, fontVariantNumeric: 'tabular-nums' }}>{value}%</div>
      </Appear>
      {caption ? (
        <Appear now={now} at={captionAt ?? at} rise={u(12)} style={{ textAlign: 'center', whiteSpace: 'nowrap', marginTop: u(20),
          fontSize: fit(caption, u(56), inner), fontWeight: 800, color: look.ink }}>{caption}</Appear>
      ) : null}
    </Card>
  );
};
