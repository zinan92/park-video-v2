// 玻璃飞轮（effort c · 示意图 · hero 卡）：形态取自 ShotCraft 的 cycle-glass-node-morph。
// 动作弧：
//   卡片从人脸那侧强减速滑入、边缘光描一圈（Card arc=hero）；
//   两层不同速度推近出纵深：底层（虚线轨道 + 弧线）0.86→1，节点层 0.92→1，到最后一个节点后 0.8s 一起停在 1；
//   卡片一进场，虚线轨道转着描好，几个节点的空位先淡淡地标出来（不让卡片空着等）；
//   每个节点在它的 at 从深处托起：玻璃球由小变大、由下往上、带竖向速度拖影，脚下一团接触阴影跟着变实；
//   节点托起后，从它出发的弧线像彗星一样描向下一个节点（头上一颗光点，到头熄灭、换成箭头）；
//   中间的词在 centerAt 逐字升起。最后一个节点后约 0.9s 做完，之后一帧不动。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { DirBlur, fit, glassBall, Kinetic, speed, tint } from '../kit/parts';
import { useSec } from '../kit/time';

type Node = { text: string; at: number };
export type GlassCycleProps = { t0: number; nodes: Node[]; center?: string; centerAt?: number; accent?: number[] };

export const GlassCycle: React.FC<GlassCycleProps> = ({ t0, nodes, center, centerAt, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const S = Math.min(useInnerWidth(), u(640));
  const R = S * 0.31;
  const ball = S * 0.29;
  const c = S / 2;
  const n = nodes.length;
  const first = Math.min(...nodes.map((x) => x.at));
  const last = Math.max(...nodes.map((x) => x.at));
  const push = seg(now, first - 0.1, last + 0.8, E.inOutCubic);
  const ang = (i: number) => -Math.PI / 2 + (2 * Math.PI * i) / n;
  const pt = (a: number) => [c + R * Math.cos(a), c + R * Math.sin(a)];
  const gap = Math.asin(Math.min(0.95, (ball * 0.6) / R));
  const guide = seg(now, t0 + 0.05, t0 + 0.55, E.outCubic);
  const label = Math.min(...nodes.map((x) => fit(x.text, u(48), ball * 0.8)));
  const layer = (from: number): React.CSSProperties => {
    const s = lerp(push, from, 1);
    return { position: 'absolute', inset: 0, transform: push >= 1 ? 'none' : `scale(${s})` };
  };
  return (
    <Card arc="hero">
      <div style={{ position: 'relative', width: S, height: S, alignSelf: 'center' }}>
        <div style={layer(0.86)}>
          <svg width={S} height={S} style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>
            <circle cx={c} cy={c} r={R} fill="none" stroke={look.muted} strokeWidth={u(3)} strokeDasharray={`${u(5)} ${u(11)}`} opacity={0.6 * guide}
              transform={`rotate(${lerp(guide, -25, 0)} ${c} ${c})`} />
            {nodes.map((nd, i) => {
              const a0 = ang(i) + gap;
              const a1 = ang(i) + (2 * Math.PI) / n - gap;
              const p = seg(now, nd.at + 0.22, nd.at + 0.82, E.inOutCubic);
              if (p <= 0) return null;
              const ae = lerp(p, a0, a1);
              const [x0, y0] = pt(a0);
              const [x1, y1] = pt(ae);
              const large = ae - a0 > Math.PI ? 1 : 0;
              const tx = -Math.sin(ae);
              const ty = Math.cos(ae);
              const L = u(30);
              const W = u(17);
              const done = p >= 1;
              return (
                <g key={i}>
                  <path d={`M ${x0} ${y0} A ${R} ${R} 0 ${large} 1 ${x1} ${y1}`} fill="none" stroke={look.accent} strokeWidth={u(9)} strokeLinecap="round" />
                  {done ? <polygon points={`${x1 + tx * L},${y1 + ty * L} ${x1 - ty * W},${y1 + tx * W} ${x1 + ty * W},${y1 - tx * W}`} fill={look.accent} />
                    : <circle cx={x1} cy={y1} r={u(28)} fill="url(#comet)" />}
                </g>
              );
            })}
            <defs>
              <radialGradient id="comet">
                <stop offset="0" stopColor="#FFFFFF" stopOpacity="1" />
                <stop offset="0.35" stopColor={look.accent} stopOpacity="0.9" />
                <stop offset="1" stopColor={look.accent} stopOpacity="0" />
              </radialGradient>
            </defs>
          </svg>
        </div>
        <div style={layer(0.92)}>
          {nodes.map((nd, i) => {
            const [x, y] = pt(ang(i));
            const ghost = seg(now, t0 + 0.15 + i * 0.08, t0 + 0.5 + i * 0.08, E.outCubic) * (1 - seg(now, nd.at, nd.at + 0.3));
            return ghost > 0 ? <div key={`g${i}`} style={{ position: 'absolute', left: x, top: y, width: ball * 0.86, height: ball * 0.86, borderRadius: '50%',
              transform: 'translate(-50%, -50%)', border: `${u(3)}px dashed ${look.muted}`, opacity: 0.55 * ghost }} /> : null;
          })}
          {nodes.map((nd, i) => {
            const [x, y] = pt(ang(i));
            const rise = (t: number) => seg(t, nd.at, nd.at + 0.5, E.outExpo);
            const r = rise(now);
            const lift = (t: number) => lerp(rise(t), ball * 0.7, 0);
            const hot = accent.includes(i);
            return (
              <div key={i} style={{ position: 'absolute', left: x, top: y, opacity: seg(now, nd.at, nd.at + 0.12) }}>
                <div style={{ position: 'absolute', left: 0, top: ball * 0.46, width: ball * 0.9, height: ball * 0.22, borderRadius: '50%',
                  transform: 'translate(-50%, -50%)', background: 'radial-gradient(ellipse, rgba(0,0,0,.32) 0%, rgba(0,0,0,0) 70%)', opacity: r }} />
                <DirBlur id={`n${i}`} y={speed(lift, now) * 0.01}
                  style={{ transform: `translate(-50%, -50%) translateY(${lift(now)}px) scale(${lerp(r, 0.55, 1)})` }}>
                  <div style={{ ...glassBall(hot ? look.accent : '#2B2F38', ball), display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <span style={{ color: '#FFFFFF', fontSize: label, fontWeight: 900, whiteSpace: 'nowrap', textShadow: '0 1px 3px rgba(0,0,0,.4)' }}>{nd.text}</span>
                  </div>
                </DirBlur>
              </div>
            );
          })}
          {center ? (
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ fontSize: fit(center, u(92), R * 1.05), fontWeight: 900, color: look.accent, whiteSpace: 'nowrap',
                textShadow: `0 0 ${u(14)}px ${tint(look.accent, 0.3)}` }}>
                <Kinetic text={center} now={now} at={centerAt ?? last + 0.3} gap={0.07} rise={u(30)} dur={0.45} />
              </span>
            </div>
          ) : null}
        </div>
      </div>
    </Card>
  );
};
