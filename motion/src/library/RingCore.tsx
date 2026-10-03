// 核心环形图（effort c · 示意图 · hero 卡）：形态取自 ShotCraft 的 ring-diagram-annotation-reveal。
// 动作弧：
//   卡片从人脸那侧强减速滑入、边缘光描一圈（Card arc=hero）；同时分段外环一边转一边描出来（逆时针 60° 转到位），
//   细环和中间的空位淡淡标好，下面注释的位置也留出来（不让卡空着等）；
//   他说出核心词时（coreAt）：12 支箭头从外向里射进来，一支比一支快（错峰越来越短），射的过程带径向拖影；
//   核心玻璃圆盘从深处托起，核心词逐字升起；一圈波纹从核心往外扩一次，停成一道淡环；
//   每条注释在它的 at：左边竖条从上往下描出，字逐字升起。核心后约 1.2s 做完，之后一帧不动（外环不会一直转）。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit, glassBall, Kinetic, tint } from '../kit/parts';
import { useSec } from '../kit/time';

type Note = { text: string; at: number };
export type RingCoreProps = { t0: number; core: string; coreAt: number; notes?: Note[] };

// 第 k 支箭头出发的时刻：间隔越来越短（越射越快）
const shot = (k: number) => 0.18 + 0.32 * (1 - Math.pow(1 - k / 12, 1.8));

export const RingCore: React.FC<RingCoreProps> = ({ t0, core, coreAt, notes = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const D = Math.min(inner, u(460));
  const c = D / 2;
  const enter = seg(now, t0 + 0.05, t0 + 0.75, E.outExpo);
  const rOuter = D * 0.46;
  const circ = 2 * Math.PI * rOuter;
  const rOut = D * 0.41;
  const rIn = D * 0.29;
  const disc = (t: number) => seg(t, coreAt + 0.1, coreAt + 0.6, E.outExpo);
  const wave = seg(now, coreAt + 0.35, coreAt + 1.1, E.outCubic);
  const noteSize = notes.length ? Math.min(...notes.map((x) => fit(x.text, u(54), inner - u(40)))) : 0;
  return (
    <Card arc="hero">
      <div style={{ position: 'relative', width: D, height: D, alignSelf: 'center' }}>
        <svg width={D} height={D} style={{ position: 'absolute', inset: 0 }}>
          <g transform={`rotate(${lerp(enter, -60, 0)} ${c} ${c})`}>
            <circle cx={c} cy={c} r={rOuter} fill="none" stroke={look.accent} strokeWidth={u(10)}
              strokeDasharray={`${circ / 16 * 0.62} ${circ / 16 * 0.38}`} pathLength={circ}
              opacity={enter} />
          </g>
          <circle cx={c} cy={c} r={D * 0.33} fill="none" stroke={look.ink} strokeOpacity={0.3 * enter} strokeWidth={u(3)} />
          <circle cx={c} cy={c} r={D * 0.22} fill="none" stroke={look.muted} strokeWidth={u(3)} strokeDasharray={`${u(5)} ${u(9)}`}
            opacity={0.6 * enter * (1 - disc(now))} />
          {wave > 0 ? <circle cx={c} cy={c} r={lerp(wave, D * 0.23, D * 0.38)} fill="none" stroke={look.accent} strokeWidth={u(4)}
            opacity={lerp(wave, 0.9, 0.28)} /> : null}
          {Array.from({ length: 12 }, (_, k) => {
            const a = (Math.PI * 2 * k) / 12 - Math.PI / 2;
            const st = coreAt + shot(k);
            const g = seg(now, st, st + 0.28, E.inCubic);
            if (g <= 0) return null;
            const head = lerp(g, rOut, rIn);
            const tail = lerp(seg(now, st, st + 0.42, E.outCubic), rOut, rIn + D * 0.04);
            const tailR = g < 1 ? Math.min(rOut, head + D * 0.12 * (1 - g) + D * 0.02) : tail;
            const cos = Math.cos(a);
            const sin = Math.sin(a);
            const h = u(10);
            const back = [c + (head + h * 1.4) * cos, c + (head + h * 1.4) * sin];
            const side = [-sin * h * 0.7, cos * h * 0.7];
            return (
              <g key={k}>
                <line x1={c + tailR * cos} y1={c + tailR * sin} x2={c + head * cos} y2={c + head * sin} stroke={look.ink} strokeOpacity={0.75}
                  strokeWidth={u(3)} strokeLinecap="round" />
                <polygon points={`${c + head * cos},${c + head * sin} ${back[0] + side[0]},${back[1] + side[1]} ${back[0] - side[0]},${back[1] - side[1]}`}
                  fill={look.ink} fillOpacity={0.75} />
              </g>
            );
          })}
        </svg>
        <div style={{ position: 'absolute', left: '50%', top: '50%', opacity: seg(now, coreAt + 0.1, coreAt + 0.22),
          transform: `translate(-50%, -50%) translateY(${lerp(disc(now), D * 0.08, 0)}px) scale(${lerp(disc(now), 0.5, 1)})`,
          filter: disc(now) < 0.9 ? `blur(${lerp(disc(now), 6, 0)}px)` : 'none' }}>
          <div style={{ ...glassBall(look.accent, D * 0.46), display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ color: '#FFFFFF', fontSize: fit(core, u(66), D * 0.38), fontWeight: 900, whiteSpace: 'nowrap',
              textShadow: `0 1px 3px rgba(0,0,0,.35), 0 0 ${u(10)}px ${tint('#FFFFFF', 0.25)}` }}>
              <Kinetic text={core} now={now} at={coreAt + 0.3} gap={0.06} rise={u(20)} />
            </span>
          </div>
        </div>
      </div>
      {notes.map((x, i) => {
        const bar = seg(now, x.at, x.at + 0.35, E.outCubic);
        const slotIn = seg(now, t0 + 0.3 + i * 0.1, t0 + 0.7 + i * 0.1, E.outCubic);
        return (
          <div key={i} style={{ display: 'flex', alignItems: 'center', marginTop: u(i ? 14 : 24), minHeight: noteSize * 1.25, opacity: slotIn }}>
            <div style={{ width: u(8), alignSelf: 'stretch', borderRadius: u(4), background: look.line, flexShrink: 0, position: 'relative', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', left: 0, right: 0, top: 0, height: `${bar * 100}%`, background: look.accent }} />
            </div>
            <div style={{ marginLeft: u(18), fontSize: noteSize, fontWeight: 800, color: look.ink, whiteSpace: 'nowrap' }}>
              <Kinetic text={x.text} now={now} at={x.at + 0.1} gap={0.035} rise={u(16)} />
            </div>
          </div>
        );
      })}
    </Card>
  );
};
