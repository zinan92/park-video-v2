// 描边圈注（effort b · 文字）：形态取自 ShotCraft 的 draw-svg-trace。
// 动作弧：卡片出现时，一支强调色的笔沿卡片的圆角边跑一整圈把它「画」出来（1s，先慢后快再慢，笔头比线粗、跑在最前）；
// 闭合那一下线变深变粗闪一次（2 帧冲上、6 帧回落）——「画完了」的句号；之后字才淡入（8 帧），
// 字不抢在闭合前。accent 里的行字出来后再画一道下划线（0.6s，一张卡最多一条）。
// 画完的线留成细边。最后一个动作后一帧不动。drawAt 默认是镜头开头（字比画慢一拍，镜头可以早于他说出口 1s 开始）。
import React from 'react';
import { useVideoConfig } from 'remotion';
import { Card, emWidth, Kicker, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit } from '../kit/parts';
import { SHADOW_MARGIN } from '../kit/theme';
import { useSec } from '../kit/time';

export type DrawTraceProps = { t0: number; kicker?: string; lines: string[]; ats: number[]; accent?: number[]; drawAt?: number };

const DRAW = 1.0;
const PEN = 0.045;

export const DrawTrace: React.FC<DrawTraceProps> = ({ t0, kicker, lines, ats, accent = [], drawAt }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const { width } = useVideoConfig();
  const d = drawAt ?? t0;
  const p = seg(now, d, d + DRAW, E.inOutCubic);
  const closed = d + DRAW;
  const flash = now < closed + 0.067 ? seg(now, closed, closed + 0.067) : 1 - seg(now, closed + 0.067, closed + 0.267, E.outQuad);
  const rest = seg(now, closed + 0.2, closed + 0.5); // 画完的线退成细边
  const sw = u(4) + flash * u(4) - rest * u(1.5);
  const pen = p > 0.02 && p < 0.985;
  const k = (width - 2 * SHADOW_MARGIN) / 600;
  const r = 30 * k; // 和 Card 的圆角一致，交棒时不错型
  const shown = (at: number) => Math.max(at, closed);
  return (
    <Card>
      {p > 0 ? (
        <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', overflow: 'visible', pointerEvents: 'none' }}>
          <rect x={sw / 2} y={sw / 2} rx={r - sw / 2} style={{ width: `calc(100% - ${sw}px)`, height: `calc(100% - ${sw}px)` }} fill="none"
            stroke={flash > 0.5 ? look.ink : look.accent} strokeWidth={sw} pathLength={1} strokeDasharray="1" strokeDashoffset={1 - p}
            opacity={lerp(rest, 1, 0.55)} />
          {pen ? (
            <rect x={sw / 2} y={sw / 2} rx={r - sw / 2} style={{ width: `calc(100% - ${sw}px)`, height: `calc(100% - ${sw}px)` }} fill="none"
              stroke={look.accent} strokeWidth={sw * 1.8} strokeLinecap="round" pathLength={1} strokeDasharray={`${PEN} ${1 - PEN}`}
              strokeDashoffset={PEN - p} />
          ) : null}
        </svg>
      ) : null}
      {kicker ? <div style={{ opacity: seg(now, closed, closed + 0.27, E.outQuad) }}><Kicker>{kicker}</Kicker></div> : null}
      {lines.map((line, i) => {
        const size = fit(line, u(i === 0 ? 92 : 76), inner);
        const at = shown(ats[i]);
        const under = accent.includes(i) ? seg(now, at + 0.1, at + 0.7, E.outCubic) : 0;
        return (
          <div key={i} style={{ position: 'relative', marginTop: u(i ? 14 : 0), alignSelf: 'flex-start' }}>
            <div style={{ fontSize: size, lineHeight: 1.25, fontWeight: 800, whiteSpace: 'nowrap', color: look.ink,
              opacity: seg(now, at, at + 0.27, E.outQuad) }}>{line}</div>
            {under > 0 ? <div style={{ position: 'absolute', left: 0, bottom: -size * 0.04, height: Math.max(3, size * 0.07),
              width: emWidth(line) * size * under, background: look.accent, borderRadius: size }} /> : null}
          </div>
        );
      })}
    </Card>
  );
};
