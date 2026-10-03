// 光晕数字（effort c · 数字）：形态取自 ShotCraft 的 halation-bloom + odometer-digit-roll。
// 他说出这个数时：各位数字滚动锁定（0.8s），背后一团强调色光晕铺开，下划线从中间描出，一道高光扫过整张卡；
// 1.4s 内做完，之后完全静止。光晕和高光都在卡片里面（卡外的半透明会被毛玻璃糊成一圈）。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { Appear, fit, Sheen, tint } from '../kit/parts';
import { useSec } from '../kit/time';

export type HaloNumberProps = { t0: number; value: string; unit?: string; at: number; caption?: string; captionAt?: number };

const Roll: React.FC<{ d: number; p: number; size: number }> = ({ d, p, size }) => {
  const pos = lerp(p, 0, 10 + d) % 10; // 先转一整圈再落到目标数字
  return (
    <span style={{ display: 'inline-block', height: size * 1.05, overflow: 'hidden', verticalAlign: 'bottom' }}>
      <span style={{ display: 'block', transform: `translateY(${-pos * size * 1.05}px)` }}>
        {Array.from({ length: 11 }, (_, i) => <span key={i} style={{ display: 'block', height: size * 1.05, lineHeight: `${size * 1.05}px` }}>{i % 10}</span>)}
      </span>
    </span>
  );
};

export const HaloNumber: React.FC<HaloNumberProps> = ({ t0, value, unit, at, caption, captionAt }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const size = fit(value + (unit ? '一'.repeat(Math.ceil(unit.length * 0.42)) : ''), u(200), inner);
  const roll = seg(now, at, at + 0.8, E.outQuart);
  const show = seg(now, at, at + 0.15);
  const halo = seg(now, at + 0.1, at + 0.9, E.outCubic);
  const line = seg(now, at + 0.6, at + 1.0, E.outCubic);
  return (
    <Card>
      <div style={{ position: 'relative', width: inner, textAlign: 'center', padding: `${u(18)}px 0 ${u(6)}px` }}>
        <div style={{ position: 'absolute', left: '50%', top: '42%', width: inner * 0.95, height: size * 1.5,
          transform: `translate(-50%, -50%) scale(${lerp(halo, 0.35, 1)})`, opacity: halo,
          background: `radial-gradient(ellipse at center, ${tint(look.accent, 0.42)} 0%, ${tint(look.accent, 0.12)} 45%, ${tint(look.accent, 0)} 72%)` }} />
        <div style={{ position: 'relative', whiteSpace: 'nowrap', lineHeight: 1.05, opacity: show }}>
          <span style={{ fontSize: size, fontWeight: 900, color: look.accent, fontVariantNumeric: 'tabular-nums', letterSpacing: -size * 0.02,
            textShadow: `0 0 ${size * 0.12}px ${tint(look.accent, 0.35)}` }}>
            {value.split('').map((ch, i) => (/\d/.test(ch) ? <Roll key={i} d={Number(ch)} p={roll} size={size} /> : <span key={i}>{ch}</span>))}
          </span>
          {unit ? <span style={{ fontSize: size * 0.42, fontWeight: 800, color: look.ink, marginLeft: u(8) }}>{unit}</span> : null}
        </div>
        <div style={{ position: 'relative', height: u(8), width: inner * 0.5 * line, margin: `${u(10)}px auto 0`, borderRadius: u(4), background: look.accent }} />
        {caption ? (
          <Appear now={now} at={captionAt ?? at + 0.5} rise={u(12)} style={{ position: 'relative', whiteSpace: 'nowrap', marginTop: u(16),
            fontSize: fit(caption, u(54), inner), fontWeight: 800, color: look.ink }}>{caption}</Appear>
        ) : null}
      </div>
      <Sheen now={now} start={at + 0.75} />
    </Card>
  );
};
