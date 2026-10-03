// 层叠压入（effort c · 文字）：形态取自 ShotCraft 的 list-stack-press。
// 每一条是一张小卡，在它的 at 从下方带着倾角升起落位（0.45s），已经在的卡被它「压」一下（下沉再回位，0.8s 内停）；
// 右上角计数跟着换成「几 / 共几」。最后一条后 0.9s 内做完，之后完全静止（小卡保留一点点倾角）。
import React from 'react';
import { Card, Kicker, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit } from '../kit/parts';
import { useSec } from '../kit/time';

export type StackPressProps = { t0: number; kicker?: string; items: string[]; ats: number[] };

// 被压一下：0→下沉→回位，只在 [t, t+0.8] 内动
const press = (now: number, t: number) => {
  const x = (now - t - 0.2) / 0.6;
  return x <= 0 || x >= 1 ? 0 : Math.sin(Math.PI * x);
};

export const StackPress: React.FC<StackPressProps> = ({ t0, kicker, items, ats }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const tag = u(58);
  const size = Math.min(...items.map((it) => fit(it, u(58), inner - tag - u(70))));
  const count = ats.filter((a) => now >= a).length;
  const sub = look.card === 'dark' || look.card === 'none' ? 'rgba(40,43,52,.95)' : 'rgba(255,255,255,.92)';
  return (
    <Card>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', width: inner }}>
        {kicker ? <Kicker>{kicker}</Kicker> : <span />}
        <span style={{ fontSize: u(30), fontWeight: 800, color: look.muted, fontVariantNumeric: 'tabular-nums', opacity: count ? 1 : 0 }}>
          <span style={{ color: look.accent }}>{count}</span> / {items.length}
        </span>
      </div>
      {items.map((it, i) => {
        const at = ats[i];
        const enter = seg(now, at, at + 0.45, E.outCubic);
        const tilt = i % 2 ? 1 : -1;
        const sink = ats.slice(i + 1).reduce((s, later) => s + press(now, later), 0) * u(7);
        return (
          <div key={i} style={{ marginTop: u(i ? 16 : 14), opacity: seg(now, at, at + 0.15),
            transform: `translateY(${lerp(enter, u(80), 0) + sink}px) rotate(${lerp(enter, tilt * 4, tilt * 0.7)}deg)` }}>
            <div style={{ display: 'flex', alignItems: 'center', padding: `${u(18)}px ${u(22)}px`, borderRadius: u(18), background: sub,
              boxShadow: `0 ${u(6)}px ${u(14)}px rgba(0,0,0,.18)` }}>
              <div style={{ width: tag, height: tag, borderRadius: u(14), background: look.accent, color: '#FFFFFF', fontSize: u(32), fontWeight: 900,
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>{i + 1}</div>
              <div style={{ marginLeft: u(20), fontSize: size, fontWeight: 800, color: look.card === 'dark' || look.card === 'none' ? '#F4F1EA' : '#15171C',
                whiteSpace: 'nowrap' }}>{it}</div>
            </div>
          </div>
        );
      })}
    </Card>
  );
};
