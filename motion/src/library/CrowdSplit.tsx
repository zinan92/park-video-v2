// 少数派（effort c · 图表）：一个比例把人群切成大头和小头——「90% 的人在前端，我在后端」。
// 画面：一群小人（默认 10 个），说到大多数时一个个冒出来挤在上半区、上面写大多数在哪；
// 说到少数时，中间一条分界线描出来，一个强调色的小人从人群里走出来、越过分界线到下半区，下面写少数在哪；
// 人群其余的小人退成灰色。动作弧：上下两个区的框先淡淡铺好 → 人群冒出（越冒越快）→ 分界线 → 一个人走过去。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { DirBlur, fit, Kinetic, speed } from '../kit/parts';
import { useSec } from '../kit/time';

type Beat = { text: string; at: number };
export type CrowdSplitProps = { t0: number; total?: number; crowd: Beat; minority: Beat; arc?: 'light' | 'hero' };

const Person: React.FC<{ size: number; color: string }> = ({ size, color }) => (
  <svg width={size} height={size * 1.25} viewBox="0 0 40 50">
    <circle cx="20" cy="12" r="9" fill={color} />
    <path d="M4 50 C4 32 12 25 20 25 C28 25 36 32 36 50 Z" fill={color} />
  </svg>
);

export const CrowdSplit: React.FC<CrowdSplitProps> = ({ t0, total = 10, crowd, minority, arc = 'light' }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const cols = 5;
  const P = Math.min(u(74), inner / (cols + 1));
  const gapX = (inner - cols * P) / (cols + 1);
  const rowH = P * 1.4;
  const topH = rowH * Math.ceil((total - 1) / cols) + u(20);
  const botH = rowH + u(20);
  const setup = seg(now, t0 + 0.05, t0 + 0.5, E.outCubic);
  const popT = (i: number) => crowd.at + 0.6 * (1 - Math.pow(1 - i / total, 1.7));
  const line = seg(now, minority.at, minority.at + 0.35, E.inOutCubic);
  const walk = (t: number) => seg(t, minority.at + 0.15, minority.at + 0.85, E.inOutCubic);
  const me = total - 1; // 最后一个是「我」
  const startX = gapX + (me % cols) * (P + gapX);
  const startY = Math.floor(me / cols) * rowH;
  const endX = (inner - P) / 2;
  const endY = topH + u(20) + u(10);
  const textSize = Math.min(fit(crowd.text, u(54), inner), fit(minority.text, u(54), inner));
  const dim = seg(now, minority.at + 0.3, minority.at + 0.7, E.outCubic);
  return (
    <Card arc={arc}>
      <div style={{ fontSize: textSize, fontWeight: 900, color: look.ink, whiteSpace: 'nowrap', marginBottom: u(12), minHeight: textSize * 1.2 }}>
        <Kinetic text={crowd.text} now={now} at={crowd.at} rise={u(16)} />
      </div>
      <div style={{ position: 'relative', width: inner, height: topH + u(20) + botH }}>
        <div style={{ position: 'absolute', left: 0, top: 0, width: inner, height: topH, borderRadius: u(16), background: look.line, opacity: 0.5 * setup }} />
        <div style={{ position: 'absolute', left: 0, top: topH + u(20), width: inner, height: botH, borderRadius: u(16), border: `${u(3)}px dashed ${look.line}`, opacity: setup }} />
        <div style={{ position: 'absolute', left: inner * (1 - line) / 2, width: inner * line, top: topH + u(8), height: u(5), borderRadius: u(3), background: look.accent }} />
        {Array.from({ length: total }, (_, i) => {
          const p = seg(now, popT(i), popT(i) + 0.3, E.outExpo);
          if (p <= 0) return null;
          const isMe = i === me;
          const w = walk(now);
          const x = isMe ? lerp(w, startX, endX) : gapX + (i % cols) * (P + gapX);
          const y0 = isMe ? lerp(w, startY, endY) : Math.floor(i / cols) * rowH;
          const lift = (t: number) => (isMe ? lerp(walk(t), startY, endY) : 0);
          const color = isMe && now >= minority.at ? look.accent : look.ink;
          return (
            <DirBlur key={i} id={`p${i}`} y={isMe ? speed(lift, now) * 0.012 : 0}
              style={{ position: 'absolute', left: x, top: y0 + u(10), opacity: isMe ? 1 : lerp(dim, 1, 0.45),
                transform: p < 1 ? `translateY(${lerp(p, u(24), 0)}px) scale(${lerp(p, 0.6, 1)})` : 'none' }}>
              <Person size={P} color={color} />
            </DirBlur>
          );
        })}
      </div>
      <div style={{ fontSize: textSize, fontWeight: 900, color: look.accent, whiteSpace: 'nowrap', marginTop: u(12), textAlign: 'center', minHeight: textSize * 1.2 }}>
        <Kinetic text={minority.text} now={now} at={minority.at + 0.5} rise={u(16)} />
      </div>
    </Card>
  );
};
