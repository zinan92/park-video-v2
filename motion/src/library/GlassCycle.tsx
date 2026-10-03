// 玻璃飞轮（effort c · 示意图）：形态取自 ShotCraft 的 cycle-glass-node-morph。
// 2–3 个节点围成一圈：每个节点在它的 at 从下方托起一颗玻璃球（带高光、暗面、内描边），
// 随后从它出发的弧线描出、箭头沿弧线走到下一个节点；整组从 0.9 连续推近到 1（不停顿、不二次起步）；
// 中间的词在 centerAt 出现。最后一个节点后 0.9s 内做完。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit, glassBall } from '../kit/parts';
import { useSec } from '../kit/time';

type Node = { text: string; at: number };
export type GlassCycleProps = { t0: number; nodes: Node[]; center?: string; centerAt?: number; accent?: number[] };

export const GlassCycle: React.FC<GlassCycleProps> = ({ t0, nodes, center, centerAt, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const S = Math.min(useInnerWidth(), u(620));
  const R = S * 0.31;
  const ball = S * 0.27;
  const c = S / 2;
  const n = nodes.length;
  const first = Math.min(...nodes.map((x) => x.at));
  const last = Math.max(...nodes.map((x) => x.at));
  const push = seg(now, first, last + 0.8, E.inOutCubic);
  const ang = (i: number) => -Math.PI / 2 + (2 * Math.PI * i) / n;
  const pt = (a: number) => [c + R * Math.cos(a), c + R * Math.sin(a)];
  const gap = Math.asin(Math.min(0.95, (ball * 0.62) / R)); // 弧线在玻璃球边上让开
  const guide = seg(now, first, first + 0.3);
  const label = Math.min(...nodes.map((x) => fit(x.text, u(44), ball * 0.8)));
  return (
    <Card>
      <div style={{ position: 'relative', width: S, height: S, alignSelf: 'center', transform: `scale(${lerp(push, 0.9, 1)})` }}>
        <svg width={S} height={S} style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>
          <circle cx={c} cy={c} r={R} fill="none" stroke={look.line} strokeWidth={u(3)} strokeDasharray={`${u(6)} ${u(10)}`} opacity={guide} />
          {nodes.map((nd, i) => {
            const a0 = ang(i) + gap;
            const a1 = ang(i) + (2 * Math.PI) / n - gap;
            const p = seg(now, nd.at + 0.15, nd.at + 0.8, E.inOutCubic);
            if (p <= 0) return null;
            const ae = lerp(p, a0, a1);
            const [x0, y0] = pt(a0);
            const [x1, y1] = pt(ae);
            const large = ae - a0 > Math.PI ? 1 : 0;
            const tx = -Math.sin(ae);
            const ty = Math.cos(ae);
            const L = u(28);
            const W = u(16);
            return (
              <g key={i}>
                <path d={`M ${x0} ${y0} A ${R} ${R} 0 ${large} 1 ${x1} ${y1}`} fill="none" stroke={look.accent} strokeWidth={u(8)} strokeLinecap="round" />
                <polygon points={`${x1 + tx * L},${y1 + ty * L} ${x1 - ty * W},${y1 + tx * W} ${x1 + ty * W},${y1 - tx * W}`} fill={look.accent} />
              </g>
            );
          })}
        </svg>
        {nodes.map((nd, i) => {
          const [x, y] = pt(ang(i));
          const rise = seg(now, nd.at, nd.at + 0.45, look.pop);
          const show = seg(now, nd.at, nd.at + 0.18);
          const hot = accent.includes(i);
          return (
            <div key={i} style={{ position: 'absolute', left: x, top: y, opacity: show,
              transform: `translate(-50%, -50%) translateY(${lerp(rise, ball * 0.45, 0)}px) scale(${lerp(rise, 0.8, 1)})` }}>
              <div style={{ ...glassBall(hot ? look.accent : '#2B2F38', ball), display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span style={{ color: '#FFFFFF', fontSize: label, fontWeight: 900, whiteSpace: 'nowrap', textShadow: '0 1px 2px rgba(0,0,0,.35)' }}>{nd.text}</span>
              </div>
            </div>
          );
        })}
        {center ? (() => {
          const q = seg(now, centerAt ?? last, (centerAt ?? last) + 0.4, look.pop);
          return (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ fontSize: fit(center, u(88), R * 1.05), fontWeight: 900, color: look.accent, whiteSpace: 'nowrap',
                opacity: seg(now, centerAt ?? last, (centerAt ?? last) + 0.2), transform: `scale(${lerp(q, 0.6, 1)})` }}>{center}</span>
            </div>
          );
        })() : null}
      </div>
    </Card>
  );
};
