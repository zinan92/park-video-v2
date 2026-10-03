// 上下两块对照 + 中间关系符（≠ / → / vs）。区域窄，所以上下排而不是左右排。各块在他说出时出现。
import React from 'react';
import { Card, Kicker, useInnerWidth, useU } from '../kit/Card';
import { fit } from '../kit/parts';
import { E, lerp, seg } from '../kit/Motion';
import { useSec } from '../kit/time';
import { useLook } from '../kit/look';

type Side = { title: string; sub?: string; at: number };
export type CompareProps = { t0: number; kicker?: string; top: Side; bottom: Side; symbol: string; symbolAt: number };

const Block: React.FC<{ side: Side; now: number; size: number }> = ({ side, now, size }) => {
  const u = useU();
  const look = useLook();
  const p = seg(now, side.at, side.at + 0.3, E.outCubic);
  return (
    <div style={{ border: `${u(3)}px solid ${look.line}`, borderRadius: u(20), padding: `${u(22)}px ${u(26)}px`, opacity: p,
      transform: `translateY(${lerp(p, u(16), 0)}px)` }}>
      <div style={{ fontSize: size, fontWeight: 800, textAlign: 'center', whiteSpace: 'nowrap' }}>{side.title}</div>
      {side.sub ? <div style={{ fontSize: size * 0.62, color: look.muted, marginTop: u(8), textAlign: 'center' }}>{side.sub}</div> : null}
    </div>
  );
};

export const Compare: React.FC<CompareProps> = ({ t0, kicker, top, bottom, symbol, symbolAt }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const s = seg(now, symbolAt, symbolAt + 0.25, look.pop);
  const avail = useInnerWidth() - u(58);
  const size = Math.min(fit(top.title, u(68), avail), fit(bottom.title, u(68), avail));
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      <Block side={top} now={now} size={size} />
      <div style={{ textAlign: 'center', fontSize: u(84), fontWeight: 800, color: look.accent, margin: `${u(6)}px 0`,
        transform: `scale(${s})` }}>{symbol}</div>
      <Block side={bottom} now={now} size={size} />
    </Card>
  );
};
