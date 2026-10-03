// 积累成结论（effort c · 示意图）：东西越来越多、每一份都很具体，所以结论成立——「五六封、七八封问卷，填得很详细，就是强需求」。
// 画面：左边一摞纸（问卷），说到每个数时纸一张张飞落上去叠高（越落越快、带点随机倾角），右上角的数跟着翻到新的说法；
// 右边逐条打勾（真实的问题 / 真实的诉求 / 填得详细）；最后一枚印章「强需求」从上方压下来盖在纸堆上，纸堆被压得一沉。
// 动作弧：纸堆的底座和勾选框先铺好 → 落纸 → 打勾 → 盖章。印章是这张卡唯一的「重击」。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, rand, seg } from '../kit/Motion';
import { DirBlur, fit, Ico, Kinetic, speed, tint } from '../kit/parts';
import { useSec } from '../kit/time';

type Beat = { text: string; at: number };
export type AccumulateProps = { t0: number; counts: (Beat & { sheets: number })[]; unit?: string; details: Beat[]; verdict: Beat; arc?: 'light' | 'hero' };

export const Accumulate: React.FC<AccumulateProps> = ({ t0, counts, unit = '', details, verdict, arc = 'hero' }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const stackW = inner * 0.42;
  const sheetH = stackW * 0.62;
  const total = Math.max(...counts.map((c) => c.sheets));
  const setup = seg(now, t0 + 0.05, t0 + 0.5, E.outCubic);
  const dropT = (i: number) => {
    let prev = 0;
    for (const c of counts) {
      if (i < c.sheets) return c.at + 0.55 * (1 - Math.pow(1 - (i - prev) / Math.max(1, c.sheets - prev), 1.6));
      prev = c.sheets;
    }
    return Infinity;
  };
  const stamp = seg(now, verdict.at, verdict.at + 0.32, E.inCubic);
  const thud = verdict.at + 0.32;
  const sinkX = (now - thud) / 0.35;
  const sink = sinkX > 0 && sinkX < 1 ? Math.sin(Math.PI * sinkX) * u(6) : 0;
  const cur = [...counts].reverse().find((c) => now >= c.at);
  const detailSize = Math.min(...details.map((d) => fit(d.text, u(46), inner - stackW - u(70))));
  const numSize = Math.min(...counts.map((c) => fit(c.text + unit, u(78), inner - stackW - u(30))));
  const stackBase = sheetH + total * u(7) + u(20);
  return (
    <Card arc={arc}>
      <div style={{ display: 'flex', width: inner, alignItems: 'flex-start' }}>
        <div style={{ position: 'relative', width: stackW, height: stackBase, flexShrink: 0, transform: sink ? `translateY(${sink}px)` : 'none' }}>
          <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: u(10), borderRadius: u(5), background: look.line, opacity: setup }} />
          {Array.from({ length: total }, (_, i) => {
            const t = dropT(i);
            const fall = (tt: number) => seg(tt, t, t + 0.32, E.inCubic);
            const p = fall(now);
            if (p <= 0) return null;
            const yRest = stackBase - u(12) - sheetH - i * u(7);
            const y = (tt: number) => lerp(fall(tt), yRest - u(160), yRest);
            const rot = (rand(i + 3) - 0.5) * 7;
            return (
              <DirBlur key={i} id={`s${i}`} y={speed(y, now) * 0.01} style={{ position: 'absolute', left: (rand(i + 9) - 0.5) * u(14), top: y(now), width: stackW,
                height: sheetH, opacity: seg(now, t, t + 0.08), transform: `rotate(${rot}deg)` }}>
                <div style={{ width: '100%', height: '100%', borderRadius: u(8), background: '#FBFAF7', boxShadow: `0 ${u(2)}px ${u(5)}px rgba(0,0,0,.18)`,
                  padding: `${sheetH * 0.16}px ${stackW * 0.1}px`, boxSizing: 'border-box' }}>
                  {[0.9, 0.7, 0.8, 0.5].map((w, k) => <div key={k} style={{ height: sheetH * 0.07, width: `${w * 100}%`, borderRadius: u(3),
                    background: i === total - 1 && details[k] && now >= details[k].at ? tint(look.accent, 0.55) : '#D9D5CC', marginBottom: sheetH * 0.09 }} />)}
                </div>
              </DirBlur>
            );
          })}
          {stamp > 0 ? (
            <div style={{ position: 'absolute', left: '50%', top: stackBase - u(12) - sheetH / 2 - total * u(7), opacity: seg(now, verdict.at, verdict.at + 0.1),
              transform: `translate(-50%, -50%) rotate(-10deg) scale(${lerp(stamp, 1.8, 1)})`, filter: stamp < 0.95 ? `blur(${lerp(stamp, 6, 0)}px)` : 'none',
              border: `${u(6)}px solid ${look.accent}`, borderRadius: u(10), padding: `${u(6)}px ${u(16)}px`, color: look.accent, fontSize: fit(verdict.text, u(64), stackW * 1.05),
              fontWeight: 900, whiteSpace: 'nowrap', background: tint('#FFFFFF', 0.75) }}>{verdict.text}</div>
          ) : null}
        </div>
        <div style={{ marginLeft: u(28), flex: 1 }}>
          <div style={{ height: numSize * 1.15, overflow: 'hidden', fontSize: numSize, fontWeight: 900, color: look.accent, whiteSpace: 'nowrap' }}>
            {counts.map((c, i) => {
              const into = seg(now, c.at, c.at + 0.3, E.outCubic);
              const nx = counts[i + 1];
              const out = nx ? seg(now, nx.at, nx.at + 0.3, E.inCubic) : 0;
              if (into <= 0 || out >= 1) return null;
              return <div key={i} style={{ height: 0, transform: `translateY(${lerp(into, numSize, 0) - out * numSize}px)` }}>
                <span>{c.text}</span><span style={{ fontSize: numSize * 0.5, color: look.ink, marginLeft: u(6) }}>{unit}</span>
              </div>;
            })}
          </div>
          <div style={{ marginTop: u(14) }}>
            {details.map((d, i) => {
              const tick = seg(now, d.at, d.at + 0.3, E.outExpo);
              return (
                <div key={i} style={{ display: 'flex', alignItems: 'center', marginTop: u(i ? 12 : 0), opacity: setup }}>
                  <div style={{ width: u(40), height: u(40), borderRadius: u(10), flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
                    border: `${u(3)}px solid ${tick > 0 ? look.accent : look.line}`, background: tick > 0 ? look.accent : 'transparent' }}>
                    {tick > 0 ? <div style={{ transform: `scale(${lerp(tick, 0.3, 1)})` }}><Ico name="check" size={u(28)} color="#FFFFFF" stroke={3} /></div> : null}
                  </div>
                  <div style={{ marginLeft: u(14), fontSize: detailSize, fontWeight: 800, color: look.ink, whiteSpace: 'nowrap' }}>
                    <Kinetic text={d.text} now={now} at={d.at + 0.05} gap={0.03} rise={u(12)} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </Card>
  );
};
