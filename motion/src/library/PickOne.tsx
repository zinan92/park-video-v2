// 抓重点（effort c · 示意图）：一堆并列的东西里只有一个是关键——「他考虑 10 个因素、20 个因素，真正的主要矛盾只有一个」。
// 画面：点阵。说到第一档（10 个）时点一颗颗铺出来（越铺越快），说到第二档（20 个）再补满，上面的标签跟着滚到新的说法；
// 说到重点时，所有点暗下去、往里收一点，其中一颗变成强调色放大，脚下一圈光推开，引出一条线连到下面的重点文字。
// 动作弧：点阵的空位先淡淡铺好（不让卡空着等）→ 铺点 → 补满 → 其余变暗、一颗点亮。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, rand, seg } from '../kit/Motion';
import { fit, Kinetic, tint } from '../kit/parts';
import { useSec } from '../kit/time';

type Stage = { count: number; label: string; at: number };
// spread：他说「摘开 / 拆开」时点阵散开一点（每颗朝各自的方向挪一小段），到重点时再收回来
export type PickOneProps = { t0: number; stages: Stage[]; focus: { text: string; at: number }; spread?: { at: number }; pick?: number; arc?: 'light' | 'hero' };

export const PickOne: React.FC<PickOneProps> = ({ t0, stages, focus, spread, pick, arc = 'hero' }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const total = Math.max(...stages.map((s) => s.count));
  const cols = total > 12 ? 5 : 4;
  const rows = Math.ceil(total / cols);
  const cellW = inner / cols;
  const dot = Math.min(cellW * 0.52, u(58));
  const gridH = rows * cellW * 0.78;
  const target = pick ?? Math.min(total - 1, cols * Math.floor(rows / 2) + Math.floor(cols / 2));
  const setup = seg(now, t0 + 0.05, t0 + 0.5, E.outCubic);
  const appear = (i: number) => {
    let prev = 0;
    for (const s of stages) {
      if (i < s.count) {
        const k = (i - prev) / Math.max(1, s.count - prev);
        return s.at + 0.7 * (1 - Math.pow(1 - k, 1.7));
      }
      prev = s.count;
    }
    return Infinity;
  };
  const current = [...stages].reverse().find((s) => now >= s.at);
  const f = seg(now, focus.at, focus.at + 0.5, E.outExpo);
  const pulse = seg(now, focus.at + 0.15, focus.at + 0.9, E.outCubic);
  const linkP = seg(now, focus.at + 0.35, focus.at + 0.7, E.inOutCubic);
  const labelSize = Math.min(...stages.map((s) => fit(s.label, u(56), inner)));
  const cx = (i: number) => (i % cols) * cellW + cellW / 2;
  const cy = (i: number) => Math.floor(i / cols) * cellW * 0.78 + cellW * 0.39;
  const shrink = lerp(f, 1, 0.92);
  const sp = spread ? seg(now, spread.at, spread.at + 0.6, E.outCubic) * (1 - seg(now, focus.at, focus.at + 0.45, E.inOutCubic)) : 0;
  const off = (i: number) => {
    const dx = cx(i) - inner / 2;
    const dy = cy(i) - gridH / 2;
    return [dx * 0.14 * sp + (rand(i) - 0.5) * u(14) * sp, dy * 0.18 * sp + (rand(i + 50) - 0.5) * u(14) * sp];
  };
  return (
    <Card arc={arc}>
      <div style={{ height: labelSize * 1.25, overflow: 'hidden', fontSize: labelSize, fontWeight: 900, color: look.ink, whiteSpace: 'nowrap', marginBottom: u(10) }}>
        {stages.map((s, i) => {
          const into = seg(now, s.at + (i ? 0.18 : 0), s.at + (i ? 0.18 : 0) + 0.3, E.outCubic);
          const next = stages[i + 1];
          const out = next ? seg(now, next.at, next.at + 0.18, E.inCubic) : 0;
          if (into <= 0 || out >= 1) return null;
          return <div key={i} style={{ height: 0, transform: `translateY(${lerp(into, labelSize, 0) - out * labelSize}px)`, opacity: into * (1 - out) }}>
            <div style={{ height: labelSize * 1.25 }}>{s.label}</div>
          </div>;
        })}
      </div>
      <div style={{ position: 'relative', width: inner, height: gridH, transform: f > 0 && f < 1 ? `scale(${shrink})` : f >= 1 ? `scale(${shrink})` : 'none' }}>
        {Array.from({ length: total }, (_, i) => {
          const t = appear(i);
          const p = seg(now, t, t + 0.28, E.outExpo);
          const isPick = i === target;
          const size = isPick ? dot * lerp(f, 1, 1.6) : dot;
          return (
            <React.Fragment key={i}>
              <div style={{ position: 'absolute', left: cx(i) - dot / 2, top: cy(i) - dot / 2, width: dot, height: dot, borderRadius: '50%',
                border: `${u(2)}px dashed ${look.line}`, opacity: setup * (1 - p) }} />
              {isPick && pulse > 0 ? <div style={{ position: 'absolute', left: cx(i), top: cy(i), width: dot * lerp(pulse, 1.6, 3), height: dot * lerp(pulse, 1.6, 3),
                borderRadius: '50%', transform: 'translate(-50%, -50%)', border: `${u(4)}px solid ${look.accent}`, opacity: lerp(pulse, 0.9, 0.25) }} /> : null}
              {p > 0 ? <div style={{ position: 'absolute', left: cx(i) - size / 2 + off(i)[0], top: cy(i) - size / 2 + off(i)[1], width: size, height: size, borderRadius: '50%',
                background: isPick && f > 0 ? look.accent : look.ink, opacity: isPick ? 1 : lerp(f, 1, 0.22),
                boxShadow: isPick && f > 0 ? `0 0 ${u(18) * f}px ${tint(look.accent, 0.6)}` : 'none',
                transform: p < 1 ? `scale(${lerp(p, 0.3, 1)})` : 'none' }} /> : null}
            </React.Fragment>
          );
        })}
        {linkP > 0 ? <div style={{ position: 'absolute', left: cx(target) - u(2.5), top: cy(target) + dot * 0.8, width: u(5),
          height: (gridH - cy(target) - dot * 0.8 + u(16)) * linkP, background: look.accent, borderRadius: u(3) }} /> : null}
      </div>
      <div style={{ fontSize: fit(focus.text, u(64), inner), fontWeight: 900, color: look.accent, whiteSpace: 'nowrap', marginTop: u(18), textAlign: 'center',
        minHeight: u(64) }}>
        <Kinetic text={focus.text} now={now} at={focus.at + 0.5} rise={u(18)} />
      </div>
    </Card>
  );
};
