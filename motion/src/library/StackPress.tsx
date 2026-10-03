// 层叠压入（effort c · 文字）：形态取自 ShotCraft 的 list-stack-press。
// 动作弧：
//   卡片进场时左侧一条细轨道先从上往下描出，标出几步的位置（不让卡空着等）；
//   每一条在它的 at：小卡以上沿为轴从下方翻起（透视下转 70°→0，带竖向速度拖影，落定后 transform 为 none——3D 下字会糊），
//   脚下投影跟着变实；同时轨道上从上一步到这一步亮起一段强调色、头上一颗光点走过去，编号圆点亮起；
//   已经在的小卡被「压」一下（下沉再回位，0.8s 内停）；右上角「几 / 共几」的数字滚到新值；字逐字升起。
// 最后一条后约 0.9s 做完，之后一帧不动。
import React from 'react';
import { Card, Kicker, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { DirBlur, fit, Kinetic, speed, tint } from '../kit/parts';
import { useSec } from '../kit/time';

export type StackPressProps = { t0: number; kicker?: string; items: string[]; ats: number[] };

const press = (now: number, t: number) => {
  const x = (now - t - 0.2) / 0.6;
  return x <= 0 || x >= 1 ? 0 : Math.sin(Math.PI * x);
};

export const StackPress: React.FC<StackPressProps> = ({ t0, kicker, items, ats }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const rail = u(64);
  const row = u(118);
  const size = Math.min(...items.map((it) => fit(it, u(60), inner - rail - u(70))));
  const count = ats.filter((a) => now >= a).length;
  const dark = look.card === 'dark' || look.card === 'none';
  const sub = dark ? 'rgba(40,43,52,.96)' : 'rgba(255,255,255,.94)';
  const track = seg(now, t0 + 0.05, t0 + 0.55, E.inOutCubic);
  const lit = (i: number) => seg(now, ats[i] + 0.05, ats[i] + 0.45, E.inOutCubic); // 轨道从第 i-1 步亮到第 i 步
  const dotY = (i: number) => row * i + row / 2;
  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', width: inner, marginBottom: u(10) }}>
        {kicker ? <Kicker>{kicker}</Kicker> : <span />}
        <span style={{ fontSize: u(40), fontWeight: 900, color: look.muted, fontVariantNumeric: 'tabular-nums', opacity: count ? 1 : 0 }}>
          <span style={{ display: 'inline-block', height: u(46), overflow: 'hidden', verticalAlign: 'bottom', color: look.accent }}>
            <span style={{ display: 'block', transform: `translateY(${-lerp(count ? seg(now, ats[count - 1], ats[count - 1] + 0.3, E.outCubic) : 0, Math.max(0, count - 1), count) * u(46)}px)` }}>
              {Array.from({ length: items.length + 1 }, (_, j) => <span key={j} style={{ display: 'block', height: u(46), lineHeight: `${u(46)}px` }}>{j}</span>)}
            </span>
          </span> / {items.length}
        </span>
      </div>
      <div style={{ position: 'relative', width: inner, height: row * items.length }}>
        <svg width={rail} height={row * items.length} style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible' }}>
          <line x1={rail / 2} y1={dotY(0)} x2={rail / 2} y2={lerp(track, dotY(0), dotY(items.length - 1))} stroke={look.line} strokeWidth={u(5)} strokeLinecap="round" />
          {items.map((_, i) => {
            if (i === 0) return null;
            const p = lit(i);
            if (p <= 0) return null;
            const y = lerp(p, dotY(i - 1), dotY(i));
            return (
              <g key={i}>
                <line x1={rail / 2} y1={dotY(i - 1)} x2={rail / 2} y2={y} stroke={look.accent} strokeWidth={u(5)} strokeLinecap="round" />
                {p < 1 ? <circle cx={rail / 2} cy={y} r={u(16)} fill={`url(#rail-head)`} /> : null}
              </g>
            );
          })}
          {items.map((_, i) => {
            const on = seg(now, ats[i], ats[i] + 0.25, E.outCubic);
            const ready = seg(now, t0 + 0.1 + i * 0.1, t0 + 0.45 + i * 0.1, E.outCubic);
            return (
              <g key={`d${i}`} opacity={ready}>
                <circle cx={rail / 2} cy={dotY(i)} r={u(22)} fill={on > 0 ? look.accent : 'none'} fillOpacity={on} stroke={on > 0 ? look.accent : look.muted} strokeWidth={u(3)} />
                <text x={rail / 2} y={dotY(i) + u(9)} textAnchor="middle" fontSize={u(26)} fontWeight={900} fill={on > 0.5 ? '#FFFFFF' : look.muted}>{i + 1}</text>
              </g>
            );
          })}
          <defs>
            <radialGradient id="rail-head">
              <stop offset="0" stopColor="#FFFFFF" />
              <stop offset="0.35" stopColor={look.accent} stopOpacity="0.9" />
              <stop offset="1" stopColor={look.accent} stopOpacity="0" />
            </radialGradient>
          </defs>
        </svg>
        {items.map((it, i) => {
          const at = ats[i];
          const flip = (t: number) => seg(t, at, at + 0.5, E.outExpo);
          const f = flip(now);
          const sink = ats.slice(i + 1).reduce((s, later) => s + press(now, later), 0) * u(7);
          const lift = (t: number) => lerp(flip(t), u(60), 0);
          const settled = f >= 1 && sink === 0;
          return (
            <div key={i} style={{ position: 'absolute', left: rail + u(16), right: 0, top: row * i + u(8), height: row - u(16), opacity: seg(now, at, at + 0.12),
              transform: settled ? 'none' : `perspective(${u(900)}px) translateY(${lift(now) + sink}px) rotateX(${lerp(f, 70, 0)}deg)`, transformOrigin: 'top center' }}>
              <DirBlur id={`c${i}`} y={speed(lift, now) * 0.012} style={{ height: '100%' }}>
                <div style={{ height: '100%', display: 'flex', alignItems: 'center', padding: `0 ${u(24)}px`, borderRadius: u(18), background: sub,
                  boxShadow: `0 ${lerp(f, u(2), u(8))}px ${lerp(f, u(4), u(18))}px rgba(0,0,0,${lerp(f, 0.05, 0.2)})`,
                  borderLeft: `${u(6)}px solid ${tint(look.accent, lerp(seg(now, at + 0.2, at + 0.5), 0, 1))}` }}>
                  <span style={{ fontSize: size, fontWeight: 800, color: dark ? '#F4F1EA' : '#15171C', whiteSpace: 'nowrap' }}>
                    <Kinetic text={it} now={now} at={at + 0.12} gap={0.03} rise={u(16)} />
                  </span>
                </div>
              </DirBlur>
            </div>
          );
        })}
      </div>
    </Card>
  );
};
