// 半圆仪表：指针在 at 起 0.9s 内从 0 扫到 value（缓出，不过冲、不回摆），读数同步滚动；剩余弧段在落定后点亮。
import React from 'react';
import { Card, Kicker, useU } from '../kit/Card';
import { E, lerp, seg } from '../kit/Motion';
import { useSec } from '../kit/time';
import { INK, LINE, RED } from '../kit/theme';

export type GaugeProps = { t0: number; kicker?: string; value: number; at: number; label?: string };

const arc = (cx: number, cy: number, r: number, a0: number, a1: number) => {
  const p = (a: number) => [cx + r * Math.cos(Math.PI * (1 - a)), cy - r * Math.sin(Math.PI * (1 - a))];
  const [x0, y0] = p(a0);
  const [x1, y1] = p(a1);
  return `M ${x0} ${y0} A ${r} ${r} 0 0 1 ${x1} ${y1}`;
};

export const Gauge: React.FC<GaugeProps> = ({ t0, kicker, value, at, label }) => {
  const u = useU();
  const now = useSec(t0);
  const p = seg(now, at, at + 0.9, E.outCubic);
  const v = (value / 100) * p;
  const rest = seg(now, at + 0.9, at + 1.2, E.outCubic);
  const W = u(460);
  const cx = W / 2;
  const cy = u(250);
  const r = u(200);
  const ang = Math.PI * (1 - v);
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      <svg width={W} height={u(290)} style={{ alignSelf: 'center' }}>
        <path d={arc(cx, cy, r, 0, 1)} stroke={LINE} strokeWidth={u(26)} fill="none" strokeLinecap="round" />
        <path d={arc(cx, cy, r, 0, Math.max(v, 0.001))} stroke={INK} strokeWidth={u(26)} fill="none" strokeLinecap="round" />
        <path d={arc(cx, cy, r, value / 100, 1)} stroke={RED} strokeWidth={u(26)} fill="none" strokeLinecap="round" opacity={rest} />
        <line x1={cx} y1={cy} x2={cx + (r - u(30)) * Math.cos(ang)} y2={cy - (r - u(30)) * Math.sin(ang)} stroke={INK} strokeWidth={u(8)}
          strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={u(12)} fill={RED} />
      </svg>
      <div style={{ textAlign: 'center', fontSize: u(72), fontWeight: 800, fontVariantNumeric: 'tabular-nums' }}>
        {Math.round(lerp(p, 0, value))}%
      </div>
      {label ? <div style={{ textAlign: 'center', fontSize: u(30), fontWeight: 600, marginTop: u(6) }}>{label}</div> : null}
    </Card>
  );
};
