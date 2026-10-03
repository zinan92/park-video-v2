// 斜纹蜕变条形图（effort c · 图表）：形态取自 ShotCraft 的 hatch-depth。
// 动作弧：
//   卡片进场时每根条的「槽」先淡淡铺好（灰底轨道，长度等于最长那根），标签位置也在（不让卡空着等）；
//   每根条在它的 at：斜纹「草稿」带横向速度拖影从左冲出、强减速停在对应长度（0.55s），冲的过程中斜纹一直在往前滚；
//   停下后一道实色从左往右擦过去把斜纹盖掉（0.35s，擦的前沿有一条亮边）；读数从 0 数到原话里的数（和长度同步），
//   标签逐字升起。几何不动只换质感：读到的是「占位变成了真数据」。每根约 1.1s 做完。数值必须是他说出口的数。
import React from 'react';
import { Card, Kicker, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { DirBlur, fit, hatch, Kinetic, speed } from '../kit/parts';
import { useSec } from '../kit/time';

type Bar = { label: string; value: number; display?: string; at: number };
export type HatchBarsProps = { t0: number; kicker?: string; bars: Bar[]; accent?: number[] };

// 读数从 0 数上去：把 display 里的第一个数按进度换掉，其余字不变（如「200万」→「137万」）
const counting = (display: string, p: number) =>
  p >= 1 ? display : display.replace(/\d+(\.\d+)?/, (m) => String(Math.round(Number(m) * p)));

export const HatchBars: React.FC<HatchBarsProps> = ({ t0, kicker, bars, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const max = Math.max(...bars.map((b) => b.value), 1);
  const labelSize = Math.min(...bars.map((b) => fit(b.label, u(60), inner)));
  const H = u(80);
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      <div style={{ width: inner }}>
        {bars.map((b, i) => {
          const hot = accent.includes(i);
          const slot = seg(now, t0 + 0.1 + i * 0.08, t0 + 0.5 + i * 0.08, E.outCubic);
          const growT = (t: number) => seg(t, b.at, b.at + 0.55, E.outExpo);
          const full = Math.max(u(130), (inner * b.value) / max);
          const w = (t: number) => full * growT(t);
          const g = growT(now);
          const wipe = seg(now, b.at + 0.55, b.at + 0.9, E.inOutCubic);
          const fill = hot ? look.accent : look.muted;
          const roll = (now - b.at) * u(90); // 斜纹往前滚：只在长的过程中滚，停下后固定
          const offset = g < 1 ? roll : (0.55 * u(90));
          return (
            <div key={i} style={{ marginTop: u(i ? 30 : 0), opacity: slot }}>
              <div style={{ fontSize: labelSize, fontWeight: 800, color: hot ? look.accent : look.ink, whiteSpace: 'nowrap', minHeight: labelSize * 1.2 }}>
                <Kinetic text={b.label} now={now} at={b.at} gap={0.03} rise={u(14)} />
              </div>
              <div style={{ position: 'relative', marginTop: u(10), height: H, width: full, borderRadius: u(14), background: look.line, overflow: 'hidden' }}>
                {g > 0 ? (
                  <DirBlur id={`b${i}`} x={speed(w, now) * 0.01} style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: w(now) }}>
                    <div style={{ position: 'absolute', inset: 0, borderRadius: u(14), overflow: 'hidden' }}>
                      <div style={{ position: 'absolute', inset: 0, background: hatch(fill, u(24)), backgroundPosition: `${offset}px 0`, opacity: 0.6 }} />
                      <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${wipe * 100}%`, background: fill }} />
                      {wipe > 0 && wipe < 1 ? <div style={{ position: 'absolute', top: 0, bottom: 0, left: `calc(${wipe * 100}% - ${u(4)}px)`, width: u(8),
                        background: 'rgba(255,255,255,.85)', filter: `blur(${u(2)}px)` }} /> : null}
                      {b.display ? (
                        <div style={{ position: 'absolute', right: u(16), top: 0, bottom: 0, display: 'flex', alignItems: 'center',
                          fontSize: u(46), fontWeight: 900, color: wipe > 0.6 ? '#FFFFFF' : look.ink, fontVariantNumeric: 'tabular-nums' }}>
                          {counting(b.display, g)}
                        </div>
                      ) : null}
                    </div>
                  </DirBlur>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>
    </Card>
  );
};
