// 飞轮 / 循环（示意图形式）：2–3 个节点围成一圈，节点之间是顺时针箭头弧线，中间可放一个词。
// 节点在各自的 at 出现，弧线在源节点出现后 0.5s 内画出来。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { Appear, draw, fit } from '../kit/parts';
import { useSec } from '../kit/time';

type Node = { text: string; at: number };
export type CycleProps = { t0: number; nodes: Node[]; center?: string; centerAt?: number; accent?: number[] };

export const Cycle: React.FC<CycleProps> = ({ t0, nodes, center, centerAt, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const S = Math.min(useInnerWidth(), u(600));
  const R = S * 0.3;
  const c = S / 2;
  const n = nodes.length;
  const ang = (i: number) => -Math.PI / 2 + (2 * Math.PI * i) / n;
  const pt = (a: number, r = R) => [c + r * Math.cos(a), c + r * Math.sin(a)];
  const gap = n === 2 ? 0.75 : 0.62; // 弧线在节点两侧让开的角度（弧度）
  const sw = u(7);
  const pill = Math.min(...nodes.map((nd) => fit(nd.text, u(60), S * 0.38)));
  return (
    <Card>
      <div style={{ position: 'relative', width: S, height: S, alignSelf: 'center' }}>
        <svg width={S} height={S} style={{ position: 'absolute', inset: 0 }}>
          {nodes.map((nd, i) => {
            const a0 = ang(i) + gap;
            const a1 = ang(i) + (2 * Math.PI) / n - gap;
            const [x0, y0] = pt(a0);
            const [x1, y1] = pt(a1);
            const p = draw(now, nd.at, 0.5);
            const tx = -Math.sin(a1);
            const ty = Math.cos(a1);
            const L = u(26);
            const W = u(15);
            const head = `${x1 + tx * L},${y1 + ty * L} ${x1 - ty * W},${y1 + tx * W} ${x1 + ty * W},${y1 - tx * W}`;
            return (
              <g key={i}>
                <path d={`M ${x0} ${y0} A ${R} ${R} 0 0 1 ${x1} ${y1}`} stroke={look.accent} strokeWidth={sw} fill="none"
                  strokeLinecap="round" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - p} />
                <polygon points={head} fill={look.accent} opacity={p > 0.92 ? 1 : 0} />
              </g>
            );
          })}
        </svg>
        {nodes.map((nd, i) => {
          const [x, y] = pt(ang(i));
          const hot = accent.includes(i);
          return (
            <div key={i} style={{ position: 'absolute', left: x, top: y, transform: 'translate(-50%, -50%)' }}>
              <Appear now={now} at={nd.at} rise={u(10)} style={{ whiteSpace: 'nowrap', fontSize: pill, fontWeight: 800,
                padding: `${u(12)}px ${u(22)}px`, borderRadius: u(999), background: hot ? look.accent : look.card === 'none' ? 'rgba(0,0,0,0.35)' : look.card === 'dark' ? '#2A2D35' : '#FFFFFF',
                color: hot ? '#FFFFFF' : look.ink, border: `${u(3)}px solid ${look.accent}` }}>{nd.text}</Appear>
            </div>
          );
        })}
        {center ? (
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Appear now={now} at={centerAt ?? nodes[0].at} rise={u(10)} style={{ fontSize: fit(center, u(84), R * 1.2),
              fontWeight: 900, color: look.accent, whiteSpace: 'nowrap' }}>{center}</Appear>
          </div>
        ) : null}
      </div>
    </Card>
  );
};
