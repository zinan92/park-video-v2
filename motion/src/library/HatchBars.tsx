// 斜纹蜕变条形图（effort c · 图表）：形态取自 ShotCraft 的 hatch-depth。
// 每根条在它的 at：先以 45° 斜纹「草稿」从左擦出到对应长度（0.5s），斜纹褪去、实色原位填满（0.3s），读数弹出；
// 几何不动只换质感，读到的是「占位变成了真数据」。每根 1s 内做完。数值必须是他说出口的数。
import React from 'react';
import { Card, Kicker, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, seg } from '../kit/Motion';
import { Appear, fit, hatch } from '../kit/parts';
import { useSec } from '../kit/time';

type Bar = { label: string; value: number; display?: string; at: number };
export type HatchBarsProps = { t0: number; kicker?: string; bars: Bar[]; accent?: number[] };

export const HatchBars: React.FC<HatchBarsProps> = ({ t0, kicker, bars, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const max = Math.max(...bars.map((b) => b.value), 1);
  const labelSize = Math.min(...bars.map((b) => fit(b.label, u(60), inner)));
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      <div style={{ width: inner }}>
        {bars.map((b, i) => {
          const hot = accent.includes(i);
          const grow = seg(now, b.at, b.at + 0.5, E.outCubic);
          const solid = seg(now, b.at + 0.55, b.at + 0.85, E.outCubic);
          const pop = seg(now, b.at + 0.7, b.at + 0.95, look.pop);
          const full = Math.max(u(110), (inner * b.value) / max);
          const fill = hot ? look.accent : look.muted;
          return (
            <Appear key={i} now={now} at={b.at} rise={u(10)} style={{ marginTop: u(i ? 28 : 0) }}>
              <div style={{ fontSize: labelSize, fontWeight: 800, color: hot ? look.accent : look.ink, whiteSpace: 'nowrap' }}>{b.label}</div>
              <div style={{ position: 'relative', marginTop: u(10), height: u(78), width: full * grow, borderRadius: u(14), overflow: 'hidden',
                background: look.line }}>
                <div style={{ position: 'absolute', inset: 0, background: hatch(fill, u(22)), opacity: 0.55 * (1 - solid) }} />
                <div style={{ position: 'absolute', inset: 0, background: fill, opacity: solid }} />
                {b.display ? (
                  <div style={{ position: 'absolute', right: u(16), top: 0, bottom: 0, display: 'flex', alignItems: 'center',
                    fontSize: u(46), fontWeight: 900, color: '#FFFFFF', transform: `scale(${pop})`, transformOrigin: 'right center' }}>{b.display}</div>
                ) : null}
              </div>
            </Appear>
          );
        })}
      </div>
    </Card>
  );
};
