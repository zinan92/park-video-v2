// 时间换算（effort c · 数字）：小投入换大回报——「3 个小时 ≈ 一个月的工资」。
// 画面：上面一行小字是基数（如「只有6000粉丝」）；左边一个钟，指针扫过 N 小时、扫过的扇形填上强调色；
// 右边一张月历，说到「一个月」时 30 个格子一格格填满（越填越快）；中间一个「≈」把两边连起来。
// 动作弧：卡片进场时钟面和月历的空格子先铺好（不让卡空着等）→ 基数逐字出现 → 钟扫 → 月历填满 → 「≈」落下。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit, Kinetic, tint } from '../kit/parts';
import { useSec } from '../kit/time';

type Beat = { text: string; at: number };
export type TimeCompressProps = { t0: number; small?: Beat; clock: Beat & { hours: number }; month: Beat & { days?: number }; arc?: 'light' | 'hero' };

export const TimeCompress: React.FC<TimeCompressProps> = ({ t0, small, clock, month, arc = 'hero' }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const days = month.days ?? 30;
  const setup = seg(now, t0 + 0.1, t0 + 0.6, E.outCubic);
  const D = inner * 0.36;
  const calW = inner * 0.44;
  const cols = 6;
  const rows = Math.ceil(days / cols);
  const cell = calW / cols;
  const sweep = seg(now, clock.at, clock.at + 0.9, E.inOutCubic);
  const ang = sweep * (clock.hours / 12) * 360;
  const fillT = (i: number) => month.at + 0.9 * (1 - Math.pow(1 - i / days, 1.6)); // 越填越快
  const eq = seg(now, month.at + 0.75, month.at + 1.1, E.outExpo);
  const r = D / 2 - u(10);
  const arcPath = (deg: number) => {
    const a = ((deg - 90) * Math.PI) / 180;
    const x = D / 2 + r * Math.cos(a);
    const y = D / 2 + r * Math.sin(a);
    return `M ${D / 2} ${D / 2} L ${D / 2} ${D / 2 - r} A ${r} ${r} 0 ${deg > 180 ? 1 : 0} 1 ${x} ${y} Z`;
  };
  const labelSize = Math.min(fit(clock.text, u(52), D * 1.2), fit(month.text, u(52), calW * 1.25));
  return (
    <Card arc={arc}>
      {small ? <div style={{ fontSize: fit(small.text, u(46), inner), fontWeight: 800, color: look.muted, whiteSpace: 'nowrap', marginBottom: u(18) }}>
        <Kinetic text={small.text} now={now} at={small.at} rise={u(14)} />
      </div> : null}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: inner, opacity: setup }}>
        <div style={{ width: D, textAlign: 'center' }}>
          <svg width={D} height={D}>
            <circle cx={D / 2} cy={D / 2} r={r} fill="none" stroke={look.line} strokeWidth={u(6)} />
            {Array.from({ length: 12 }, (_, i) => {
              const a = (i * 30 * Math.PI) / 180;
              return <line key={i} x1={D / 2 + (r - u(14)) * Math.sin(a)} y1={D / 2 - (r - u(14)) * Math.cos(a)} x2={D / 2 + (r - u(4)) * Math.sin(a)} y2={D / 2 - (r - u(4)) * Math.cos(a)}
                stroke={look.muted} strokeWidth={u(3)} strokeLinecap="round" />;
            })}
            {sweep > 0 ? <path d={arcPath(Math.max(0.5, ang))} fill={tint(look.accent, 0.35)} /> : null}
            <line x1={D / 2} y1={D / 2} x2={D / 2 + (r - u(22)) * Math.sin((ang * Math.PI) / 180)} y2={D / 2 - (r - u(22)) * Math.cos((ang * Math.PI) / 180)}
              stroke={look.accent} strokeWidth={u(7)} strokeLinecap="round" />
            <circle cx={D / 2} cy={D / 2} r={u(9)} fill={look.accent} />
          </svg>
          <div style={{ fontSize: labelSize, fontWeight: 900, color: look.accent, whiteSpace: 'nowrap', marginTop: u(8) }}>
            <Kinetic text={clock.text} now={now} at={clock.at} rise={u(16)} />
          </div>
        </div>
        <div style={{ fontSize: u(80), fontWeight: 900, color: look.ink, opacity: eq, transform: eq >= 1 ? 'none' : `translateY(${lerp(eq, -u(30), 0)}px)` }}>≈</div>
        <div style={{ width: calW, textAlign: 'center' }}>
          <div style={{ position: 'relative', width: calW, height: cell * rows + u(16), borderRadius: u(10), border: `${u(3)}px solid ${look.line}`, paddingTop: u(16), boxSizing: 'border-box' }}>
            <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: u(16), background: look.line, borderRadius: `${u(8)}px ${u(8)}px 0 0` }} />
            {Array.from({ length: days }, (_, i) => {
              const p = seg(now, fillT(i), fillT(i) + 0.12, E.outCubic);
              return <div key={i} style={{ position: 'absolute', left: (i % cols) * cell + cell * 0.12, top: u(16) + Math.floor(i / cols) * cell + cell * 0.12,
                width: cell * 0.76, height: cell * 0.76, borderRadius: u(4), background: p > 0 ? look.accent : 'transparent',
                border: p > 0 ? 'none' : `${u(2)}px solid ${look.line}`, opacity: p > 0 ? lerp(p, 0.3, 1) : 1, transform: p > 0 && p < 1 ? `scale(${lerp(p, 0.4, 1)})` : 'none' }} />;
            })}
          </div>
          <div style={{ fontSize: labelSize, fontWeight: 900, color: look.ink, whiteSpace: 'nowrap', marginTop: u(8) }}>
            <Kinetic text={month.text} now={now} at={month.at} rise={u(16)} gap={0.03} />
          </div>
        </div>
      </div>
    </Card>
  );
};
