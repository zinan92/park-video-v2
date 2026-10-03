// 关键数字滚动锁定：每一位从 0 往上滚，在 lockAt（他说出这个数的时刻）落定；notes 是数字下面跟随原话出现的补充行。
import React from 'react';
import { Card, Kicker, useU } from '../kit/Card';
import { E, lerp, seg } from '../kit/Motion';
import { useSec } from '../kit/time';
import { useLook } from '../kit/look';

export type NumberRollProps = { t0: number; kicker?: string; value: string; unit?: string; lockAt: number;
  notes?: { text: string; at: number }[] };

const Digit: React.FC<{ d: number; p: number; size: number }> = ({ d, p, size }) => {
  const turns = 1 + d / 10; // 先整圈再落到目标数字
  const pos = lerp(p, 0, turns * 10) % 10;
  return (
    <span style={{ display: 'inline-block', height: size * 1.1, overflow: 'hidden', verticalAlign: 'bottom' }}>
      <span style={{ display: 'block', transform: `translateY(${-pos * size * 1.1}px)` }}>
        {Array.from({ length: 11 }, (_, i) => (
          <span key={i} style={{ display: 'block', height: size * 1.1, lineHeight: `${size * 1.1}px` }}>{i % 10}</span>
        ))}
      </span>
    </span>
  );
};

export const NumberRoll: React.FC<NumberRollProps> = ({ t0, kicker, value, unit, lockAt, notes = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const p = seg(now, lockAt - 0.8, lockAt, E.outCubic);
  const size = u(130);
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      <div style={{ fontSize: size, fontWeight: 800, color: look.accent, fontVariantNumeric: 'tabular-nums', lineHeight: 1.1 }}>
        {value.split('').map((ch, i) => (/\d/.test(ch) ? <Digit key={i} d={Number(ch)} p={p} size={size} /> : <span key={i}>{ch}</span>))}
        {unit ? <span style={{ fontSize: u(44), marginLeft: u(10), color: look.muted }}>{unit}</span> : null}
      </div>
      {notes.map((n, i) => {
        const q = seg(now, n.at, n.at + 0.3, E.outCubic);
        return <div key={i} style={{ fontSize: u(36), fontWeight: 600, marginTop: u(16), opacity: q,
          transform: `translateY(${lerp(q, u(14), 0)}px)` }}>{n.text}</div>;
      })}
    </Card>
  );
};
