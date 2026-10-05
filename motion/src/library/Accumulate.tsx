// 积累成结论（effort c · 示意图）：东西越来越多、每一份都很具体，所以结论成立——「五六封、七八封问卷，填得很详细，就是强需求」。
// 做工基准：客户咨询1 旧流程 V05（Park 认可过的问卷表单）：表头一行原话、三行带勾选框的字段（行落定后描出对勾）、
// 朱红描边印章斜盖在表单右下、不压字段。这里在它上面多一层「积累」：
// 1. 说到每个数时，一张张空白问卷（灰条占位的同一张表）从上方飞落、叠成一摞，越落越快、底下几张带随机倾角露出边；上方计数跟着翻。
// 2. 最上面那张就是要读的那份：说到表头时灰条换成原话，说到每个字段时那一行的灰条换成原话，落定后勾选框描出对勾。
// 3. 说到结论时印章从上方压下来盖在表单右下，整摞被压得一沉。印章是这张卡唯一的「重击」。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, rand, seg } from '../kit/Motion';
import { DirBlur, fit, Kinetic, speed, tint } from '../kit/parts';
import { useSec } from '../kit/time';

type Beat = { text: string; at: number };
export type AccumulateProps = {
  t0: number; counts: (Beat & { sheets: number })[]; unit?: string; lead?: Beat; title?: Beat; details: Beat[]; verdict: Beat;
  arc?: 'light' | 'hero';
};

const PAPER = '#FFFFFF';
const STROKE = '#D6CFC2';
const BAR = '#DDD7CC';

export const Accumulate: React.FC<AccumulateProps> = ({ t0, counts, unit = '', lead, title, details, verdict, arc = 'hero' }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const total = Math.max(...counts.map((c) => c.sheets));
  const top = total - 1;

  // 版面
  const W = inner - u(16);
  const padX = u(30);
  const rowH = u(70);
  const titleSize = title ? fit(title.text, u(40), W - 2 * padX) : 0;
  const fieldSize = Math.min(...details.map((d) => fit(d.text, u(40), W - 2 * padX - u(64))));
  const box = u(40);
  const stampRoom = u(108);
  const formH = u(26) + (title ? titleSize * 1.25 + u(30) : 0) + details.length * rowH + stampRoom;
  const peek = u(22); // 底下几张露出来的高度
  const numSize = Math.min(...counts.map((c) => fit(c.text + unit, u(70), inner * 0.7)));
  const leadSize = lead ? fit(lead.text, u(34), inner * 0.3) : 0;

  // 落纸：每个数说出口后 0.55s 内落完这一批，越落越快
  const dropT = (i: number) => {
    let prev = 0;
    for (const c of counts) {
      if (i < c.sheets) return c.at + 0.55 * (1 - Math.pow(1 - (i - prev) / Math.max(1, c.sheets - prev), 1.6));
      prev = c.sheets;
    }
    return Infinity;
  };
  const setup = seg(now, t0 + 0.05, t0 + 0.45, E.outCubic);
  const stamp = seg(now, verdict.at, verdict.at + 0.32, E.inCubic);
  const thud = verdict.at + 0.32;
  const sinkX = (now - thud) / 0.35;
  const sink = sinkX > 0 && sinkX < 1 ? Math.sin(Math.PI * sinkX) * u(6) : 0;

  // 一张问卷：占位灰条；最上面那张（live）随口播换成原话
  const sheet = (live: boolean) => {
    const tIn = title ? seg(now, title.at, title.at + 0.3, E.outCubic) : 0;
    return (
      <div style={{ width: W, height: formH, boxSizing: 'border-box', padding: `${u(26)}px ${padX}px 0`, background: PAPER, borderRadius: u(18),
        border: `${u(2)}px solid ${STROKE}`, boxShadow: `0 ${u(3)}px ${u(9)}px rgba(40,30,20,.16)` }}>
        {title ? (
          <div style={{ position: 'relative', height: titleSize * 1.25 }}>
            <div style={{ position: 'absolute', top: titleSize * 0.35, height: titleSize * 0.55, width: '72%', borderRadius: u(4), background: BAR,
              opacity: live ? 1 - tIn : 1 }} />
            {live ? <div style={{ position: 'absolute', inset: 0, fontSize: titleSize, fontWeight: 800, color: '#15171C', whiteSpace: 'nowrap' }}>
              <Kinetic text={title.text} now={now} at={title.at} gap={0.025} rise={u(14)} />
            </div> : null}
          </div>
        ) : null}
        {title ? <div style={{ height: u(2), background: STROKE, margin: `${u(18)}px 0 ${u(10)}px` }} /> : null}
        {details.map((d, i) => {
          const rIn = seg(now, d.at, d.at + 0.3, E.outCubic);
          const tick = seg(now, d.at + 0.33, d.at + 0.47, E.outCubic);
          const on = live && rIn > 0;
          return (
            <div key={i} style={{ height: rowH, display: 'flex', alignItems: 'center', borderBottom: `${u(2)}px dashed ${STROKE}` }}>
              <svg width={box} height={box} viewBox="0 0 46 46" style={{ flexShrink: 0 }}>
                <rect x={2} y={2} width={42} height={42} rx={9} fill={PAPER} stroke={on ? '#9C958A' : STROKE} strokeWidth={3} />
                {live && tick > 0 ? <path d="M 11 24 L 20 33 L 36 14" fill="none" stroke="#15171C" strokeWidth={5.5} strokeLinecap="round"
                  strokeLinejoin="round" pathLength={1} strokeDasharray="1 1" strokeDashoffset={1 - tick} /> : null}
              </svg>
              <div style={{ position: 'relative', flex: 1, marginLeft: u(22), height: fieldSize * 1.3 }}>
                <div style={{ position: 'absolute', top: fieldSize * 0.4, height: fieldSize * 0.5, width: `${[64, 52, 76][i % 3]}%`, borderRadius: u(4),
                  background: BAR, opacity: live ? 1 - rIn : 1 }} />
                {on ? <div style={{ position: 'absolute', inset: 0, fontSize: fieldSize, fontWeight: 700, color: '#15171C', whiteSpace: 'nowrap' }}>
                  <Kinetic text={d.text} now={now} at={d.at} gap={0.03} rise={u(12)} />
                </div> : null}
              </div>
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <Card arc={arc}>
      <div style={{ width: inner }}>
        {/* 计数：收到了 五六封 → 七八封 */}
        <div style={{ position: 'relative', zIndex: 2, display: 'flex', alignItems: 'baseline', height: numSize * 1.15, opacity: setup }}>
          {lead ? <div style={{ fontSize: leadSize, fontWeight: 700, color: look.muted, marginRight: u(12), whiteSpace: 'nowrap' }}>
            <Kinetic text={lead.text} now={now} at={lead.at} rise={u(10)} />
          </div> : null}
          <div style={{ position: 'relative', height: numSize * 1.15, overflow: 'hidden', flex: 1, fontSize: numSize, fontWeight: 900, color: look.accent,
            whiteSpace: 'nowrap' }}>
            {counts.map((c, i) => {
              const into = seg(now, c.at, c.at + 0.3, E.outCubic);
              const nx = counts[i + 1];
              const out = nx ? seg(now, nx.at, nx.at + 0.3, E.inCubic) : 0;
              if (into <= 0 || out >= 1) return null;
              const y = lerp(into, numSize, 0) - out * numSize;
              return <div key={i} style={{ position: 'absolute', left: 0, top: 0, transform: y ? `translateY(${y}px)` : 'none',
                filter: into < 1 || out > 0 ? `blur(${Math.max(1 - into, out) * 6}px)` : 'none' }}>
                <span>{c.text}</span><span style={{ fontSize: numSize * 0.5, color: look.ink, marginLeft: u(6) }}>{unit}</span>
              </div>;
            })}
          </div>
        </div>

        {/* 一摞问卷 */}
        <div style={{ position: 'relative', width: inner, height: formH + peek + u(14), marginTop: u(14), transform: sink ? `translateY(${sink}px)` : 'none' }}>
          <div style={{ position: 'absolute', left: u(8), right: u(8), bottom: 0, height: u(8), borderRadius: u(4), background: look.line, opacity: setup }} />
          {Array.from({ length: total }, (_, i) => {
            const t = dropT(i);
            const fall = (tt: number) => seg(tt, t, t + 0.3, E.inCubic);
            const p = fall(now);
            if (p <= 0) return null;
            const depth = top - i; // 0 = 最上面那张
            const yRest = peek - Math.min(depth, 3) * (peek / 3);
            const y = (tt: number) => lerp(fall(tt), yRest - u(150), yRest);
            const rot = i === top ? 0 : (rand(i + 3) - 0.5) * 6;
            const dx = i === top ? 0 : (rand(i + 9) - 0.5) * u(16);
            const landed = p >= 1;
            return (
              <DirBlur key={i} id={`q${i}`} y={landed ? 0 : speed(y, now) * 0.01} style={{ position: 'absolute', left: u(8) + dx, top: y(now),
                opacity: seg(now, t, t + 0.08), transform: rot ? `rotate(${rot}deg)` : 'none' }}>
                {sheet(i === top)}
              </DirBlur>
            );
          })}
          {stamp > 0 ? (
            <div style={{ position: 'absolute', right: u(30), top: peek + formH - stampRoom + u(14), opacity: seg(now, verdict.at, verdict.at + 0.1),
              transform: `rotate(-6deg) scale(${lerp(stamp, 1.8, 1)})`, transformOrigin: '60% 50%', filter: stamp < 0.95 ? `blur(${lerp(stamp, 6, 0)}px)` : 'none',
              border: `${u(6)}px solid ${look.accent}`, borderRadius: u(16), padding: `${u(4)}px ${u(20)}px`, color: look.accent,
              fontSize: fit(verdict.text, u(50), W * 0.72), fontWeight: 900, letterSpacing: u(2), whiteSpace: 'nowrap', background: tint('#FFFFFF', 0.9) }}>
              {verdict.text}
            </div>
          ) : null}
        </div>
      </div>
    </Card>
  );
};
