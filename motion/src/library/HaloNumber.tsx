// 光晕数字（effort c · 数字 · hero 卡）：形态取自 ShotCraft 的 light-play-moves（halation-bloom）+ odometer-digit-roll。
// 动作弧（他说出这个数时，at 起）：
//   卡片从人脸那侧强减速滑入、边缘光描一圈（Card arc=hero）；
//   各位数字一起开转、带竖向速度拖影，从高位到低位依次锁定，间隔越来越短（越锁越快）；
//   最后一位锁定那一下：整个数字从 1.035 压到 1（不冲过头），背后光晕亮到最满再回落到常亮；
//   单位逐字从右侧滑入，下划线从左描出、头上一颗光点走到头熄灭；说明一行逐字升起。
// 约 1.4s 内做完，之后一帧不动。光晕、光点都在卡片里面。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { DirBlur, fit, Kinetic, speed, tint } from '../kit/parts';
import { useSec } from '../kit/time';

export type HaloNumberProps = { t0: number; value: string; unit?: string; at: number; caption?: string; captionAt?: number };

const LOCK = [0.5, 0.64, 0.74, 0.81, 0.86, 0.9, 0.93]; // 第 i 位在 at+LOCK[i] 锁定：越锁越快

export const HaloNumber: React.FC<HaloNumberProps> = ({ t0, value, unit, at, caption, captionAt }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const size = fit(value + (unit ? '一'.repeat(Math.ceil(unit.length * 0.42)) : ''), u(200), inner);
  const cell = size * 1.05;
  const digits = [...value].filter((ch) => /\d/.test(ch)).length;
  const lockEnd = at + LOCK[Math.min(LOCK.length - 1, Math.max(0, digits - 1))];
  const impact = seg(now, lockEnd, lockEnd + 0.25, E.outCubic);
  const halo = Math.min(seg(now, at, lockEnd, E.inCubic), 1) * lerp(seg(now, lockEnd, lockEnd + 0.4, E.outCubic), 1, 0.72);
  const line = (t: number) => seg(t, lockEnd - 0.02, lockEnd + 0.42, E.inOutCubic);
  const lp = line(now);
  let di = -1;
  return (
    <Card arc="hero">
      <div style={{ position: 'relative', width: inner, textAlign: 'center', padding: `${u(20)}px 0 ${u(8)}px` }}>
        <div style={{ position: 'absolute', left: '50%', top: '42%', width: inner * 1.0, height: size * 1.6,
          transform: `translate(-50%, -50%) scale(${lerp(halo, 0.5, 1)})`, opacity: halo,
          background: `radial-gradient(ellipse at center, ${tint(look.accent, 0.5)} 0%, ${tint(look.accent, 0.16)} 42%, ${tint(look.accent, 0)} 70%)` }} />
        <div style={{ position: 'relative', whiteSpace: 'nowrap', lineHeight: 1.05, opacity: seg(now, at, at + 0.12),
          transform: impact > 0 && impact < 1 ? `scale(${lerp(impact, 1.035, 1)})` : 'none' }}>
          <span style={{ fontSize: size, fontWeight: 900, color: look.accent, fontVariantNumeric: 'tabular-nums', letterSpacing: -size * 0.02 }}>
            {[...value].map((ch, i) => {
              if (!/\d/.test(ch)) return <span key={i}>{ch}</span>;
              di += 1;
              const d = Number(ch);
              const lock = at + LOCK[Math.min(LOCK.length - 1, di)];
              const pos = (t: number) => lerp(seg(t, at, lock, E.outQuart), 0, 20 + d) * cell; // 转两圈再落到目标
              const y = (pos(now) / cell) % 10;
              return (
                <span key={i} style={{ display: 'inline-block', height: cell, overflow: 'hidden', verticalAlign: 'bottom' }}>
                  <DirBlur id={`d${i}`} y={speed(pos, now) * 0.012}>
                    <span style={{ display: 'block', transform: `translateY(${-y * cell}px)` }}>
                      {Array.from({ length: 11 }, (_, j) => <span key={j} style={{ display: 'block', height: cell, lineHeight: `${cell}px` }}>{j % 10}</span>)}
                    </span>
                  </DirBlur>
                </span>
              );
            })}
          </span>
          {unit ? <span style={{ fontSize: size * 0.42, fontWeight: 800, color: look.ink, marginLeft: u(8) }}>
            <Kinetic text={unit} now={now} at={lockEnd - 0.12} gap={0.05} rise={size * 0.2} />
          </span> : null}
        </div>
        <div style={{ position: 'relative', height: u(8), width: inner * 0.56, margin: `${u(12)}px auto 0` }}>
          <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: `${lp * 100}%`, borderRadius: u(4),
            background: `linear-gradient(90deg, ${tint(look.accent, 0.35)}, ${look.accent})` }} />
          {lp > 0 && lp < 1 ? <div style={{ position: 'absolute', left: `${lp * 100}%`, top: '50%', width: u(26), height: u(26), borderRadius: '50%',
            transform: 'translate(-50%, -50%)', background: `radial-gradient(circle, #FFFFFF 0%, ${tint(look.accent, 0.7)} 40%, ${tint(look.accent, 0)} 72%)` }} /> : null}
        </div>
        {caption ? (
          <div style={{ position: 'relative', whiteSpace: 'nowrap', marginTop: u(18), fontSize: fit(caption, u(58), inner), fontWeight: 800, color: look.ink }}>
            <Kinetic text={caption} now={now} at={captionAt ?? lockEnd + 0.1} rise={u(18)} />
          </div>
        ) : null}
      </div>
    </Card>
  );
};
