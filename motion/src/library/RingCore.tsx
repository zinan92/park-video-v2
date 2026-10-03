// 核心环形图（effort c · 示意图）：形态取自 ShotCraft 的 ring-diagram-annotation-reveal。
// 他说出核心词时：细环从 1.7 倍收到原位，分段外环淡入并转 40° 后停住，12 支向心箭头错峰长出指向核心，
// 核心玻璃圆盘弹出核心词；下面 1–3 条注释各在它的 at 滑入。核心后 1.2s 内做完（外环不会一直转）。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { Appear, fit, glassBall } from '../kit/parts';
import { useSec } from '../kit/time';

type Note = { text: string; at: number };
export type RingCoreProps = { t0: number; core: string; coreAt: number; notes?: Note[] };

export const RingCore: React.FC<RingCoreProps> = ({ t0, core, coreAt, notes = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const D = Math.min(inner, u(440));
  const c = D / 2;
  const ring = seg(now, coreAt, coreAt + 0.6, E.outCubic);
  const outer = seg(now, coreAt + 0.1, coreAt + 1.2, E.outCubic);
  const disc = seg(now, coreAt + 0.15, coreAt + 0.55, look.pop);
  const rOut = D * 0.41;
  const rIn = D * 0.3;
  const noteSize = notes.length ? Math.min(...notes.map((x) => fit(x.text, u(52), inner - u(34)))) : 0;
  return (
    <Card>
      <div style={{ position: 'relative', width: D, height: D, alignSelf: 'center' }}>
        <svg width={D} height={D} style={{ position: 'absolute', inset: 0 }}>
          <circle cx={c} cy={c} r={D * 0.33 * lerp(ring, 1.7, 1)} fill="none" stroke={look.ink} strokeOpacity={0.35 * ring} strokeWidth={u(3)} />
          <g transform={`rotate(${lerp(outer, -40, 0)} ${c} ${c})`} opacity={outer}>
            <circle cx={c} cy={c} r={D * 0.46} fill="none" stroke={look.accent} strokeWidth={u(10)}
              strokeDasharray={`${(2 * Math.PI * D * 0.46) / 16 * 0.62} ${(2 * Math.PI * D * 0.46) / 16 * 0.38}`} />
          </g>
          {Array.from({ length: 12 }, (_, k) => {
            const a = (Math.PI * 2 * k) / 12;
            const g = seg(now, coreAt + 0.25 + k * 0.025, coreAt + 0.6 + k * 0.025, E.outCubic);
            if (g <= 0) return null;
            const r2 = lerp(g, rOut, rIn);
            const [x1, y1, x2, y2] = [c + rOut * Math.cos(a), c + rOut * Math.sin(a), c + r2 * Math.cos(a), c + r2 * Math.sin(a)];
            const h = u(10);
            const back = [x2 + Math.cos(a) * h * 1.4, y2 + Math.sin(a) * h * 1.4];
            const side = [-Math.sin(a) * h * 0.7, Math.cos(a) * h * 0.7];
            return (
              <g key={k} opacity={0.75}>
                <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={look.ink} strokeWidth={u(3)} strokeLinecap="round" />
                {g > 0.9 ? <polygon points={`${x2},${y2} ${back[0] + side[0]},${back[1] + side[1]} ${back[0] - side[0]},${back[1] - side[1]}`} fill={look.ink} /> : null}
              </g>
            );
          })}
        </svg>
        <div style={{ position: 'absolute', left: '50%', top: '50%', opacity: seg(now, coreAt + 0.15, coreAt + 0.3),
          transform: `translate(-50%, -50%) scale(${lerp(disc, 0.5, 1)})` }}>
          <div style={{ ...glassBall(look.accent, D * 0.46), display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span style={{ color: '#FFFFFF', fontSize: fit(core, u(64), D * 0.38), fontWeight: 900, whiteSpace: 'nowrap',
              textShadow: '0 1px 3px rgba(0,0,0,.35)' }}>{core}</span>
          </div>
        </div>
      </div>
      {notes.map((x, i) => (
        <Appear key={i} now={now} at={x.at} rise={u(12)} style={{ display: 'flex', alignItems: 'center', marginTop: u(i ? 14 : 22) }}>
          <div style={{ width: u(8), alignSelf: 'stretch', borderRadius: u(4), background: look.accent, flexShrink: 0 }} />
          <div style={{ marginLeft: u(18), fontSize: noteSize, fontWeight: 800, color: look.ink, whiteSpace: 'nowrap' }}>{x.text}</div>
        </Appear>
      ))}
    </Card>
  );
};
