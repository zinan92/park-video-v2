// 聚光扫字（effort b · 文字）：形态取自 ShotCraft 的 spotlight-sweep-moves（A 式醒睡扫过）。
// 动作弧：每行在它的 at 被一道光从左往右匀速扫过（0.9s，严格匀速——加缓动读作光有意图）：
// 光到哪里字亮到哪里，前面还暗着；光头贴着这行字的下沿走，带三层强调色辉光（宽糊 + 中层 + 亮芯）。
// 扫完光在 0.35s 内退掉，字全亮停住。辉光都收在卡片里（毛玻璃的模糊靠层的透明度判断，不能往外溢）。
// 最后一行后约 1.3s 做完，之后一帧不动。
import React from 'react';
import { Card, emWidth, Kicker, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit, tint } from '../kit/parts';
import { useSec } from '../kit/time';

export type SpotlightSweepProps = { t0: number; kicker?: string; lines: string[]; ats: number[]; accent?: number[] };

const SWEEP = 0.9;
const FADE = 0.35;
const FEATHER = 14; // 亮暗交界的羽化（%）

export const SpotlightSweep: React.FC<SpotlightSweepProps> = ({ t0, kicker, lines, ats, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      {lines.map((line, i) => {
        const size = fit(line, u(i === 0 ? 92 : 76), inner);
        const w = emWidth(line) * size;
        const p = seg(now, ats[i], ats[i] + SWEEP); // 匀速
        const glow = now < ats[i] ? 0 : 1 - seg(now, ats[i] + SWEEP, ats[i] + SWEEP + FADE, E.outQuad);
        const head = lerp(p, -FEATHER, 100 + FEATHER);
        const mask = p >= 1 ? undefined
          : `linear-gradient(90deg, #000 ${head - FEATHER}%, rgba(0,0,0,${now < ats[i] ? 0 : 0.08}) ${head + FEATHER}%)`;
        const hx = (w * head) / 100;
        const len = w * 0.42;
        const band = (h: number, blur: number, color: string, cover = 1) => (
          <div style={{ position: 'absolute', left: hx - len * cover, top: size * 1.12 - h / 2, width: len * cover, height: h, filter: `blur(${blur}px)`,
            background: `linear-gradient(90deg, rgba(0,0,0,0), ${color})`, borderRadius: h }} />
        );
        return (
          <div key={i} style={{ position: 'relative', marginTop: u(i ? 16 : 0), height: size * 1.3, width: w, alignSelf: 'center' }}>
            {glow > 0 ? (
              <div style={{ position: 'absolute', inset: 0, opacity: glow }}>
                <div style={{ position: 'absolute', left: hx - size * 1.2, top: -size * 0.1, width: size * 2.4, height: size * 1.5,
                  background: `radial-gradient(ellipse at 50% 60%, ${tint(look.accent, 0.28)}, rgba(0,0,0,0) 70%)` }} />
                {band(size * 0.34, size * 0.16, tint(look.accent, 0.45))}
                {band(size * 0.12, size * 0.05, tint(look.accent, 0.85), 0.8)}
                {band(size * 0.035, 0.6, '#FFFFFF', 0.6)}
              </div>
            ) : null}
            <div style={{ position: 'relative', fontSize: size, lineHeight: 1.25, fontWeight: 800, whiteSpace: 'nowrap',
              color: accent.includes(i) ? look.accent : look.ink, WebkitMaskImage: mask, maskImage: mask }}>{line}</div>
          </div>
        );
      })}
    </Card>
  );
};
