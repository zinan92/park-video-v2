// 图标涟漪（effort c · 图标）：形态取自 ShotCraft 的 radial-wave。
// 动作弧：
//   卡片进场时圆盘的位置先用一圈虚线标好（不让卡空着等）；
//   他说出这个概念时（iconAt）：强调色玻璃圆盘从深处托起（由小变大、由下往上、带模糊变清），
//   白色图标像时针扫过一样一笔「画」出来（锥形遮罩转一圈，0.5s）；
//   三圈涟漪一圈比一圈晚、一圈比一圈快地往外推，停在各自的位置成为淡环（不会一直扩）；
//   一两行字逐字升起。约 1.3s 做完，之后一帧不动。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit, glassBall, Ico, Kinetic } from '../kit/parts';
import { useSec } from '../kit/time';

export type IconBloomProps = { t0: number; icon: string; iconAt: number; lines: string[]; ats: number[]; accent?: number[] };

export const IconBloom: React.FC<IconBloomProps> = ({ t0, icon, iconAt, lines, ats, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const D = u(184);
  const box = Math.min(inner, D * 2);
  const rise = seg(now, iconAt, iconAt + 0.5, E.outExpo);
  const sweep = seg(now, iconAt + 0.15, iconAt + 0.65, E.inOutCubic);
  const slot = seg(now, t0 + 0.05, t0 + 0.45, E.outCubic) * (1 - seg(now, iconAt, iconAt + 0.25));
  return (
    <Card>
      <div style={{ position: 'relative', width: box, height: box * 0.86, alignSelf: 'center' }}>
        {slot > 0 ? <div style={{ position: 'absolute', left: '50%', top: '50%', width: D * 0.9, height: D * 0.9, borderRadius: '50%', transform: 'translate(-50%, -50%)',
          border: `${u(3)}px dashed ${look.muted}`, opacity: 0.55 * slot }} /> : null}
        {[0, 1, 2].map((k) => {
          const st = iconAt + 0.2 + [0, 0.16, 0.27][k];
          const q = seg(now, st, st + [0.8, 0.65, 0.55][k], E.outCubic);
          const r = lerp(q, D * 0.5, D * (0.62 + k * 0.17));
          return q > 0 ? <div key={k} style={{ position: 'absolute', left: '50%', top: '50%', width: r * 2, height: r * 2, borderRadius: '50%',
            transform: 'translate(-50%, -50%)', border: `${u(3)}px solid ${look.accent}`, opacity: lerp(q, 0.95, 0.42 - k * 0.12) }} /> : null;
        })}
        <div style={{ position: 'absolute', left: '50%', top: '50%', opacity: seg(now, iconAt, iconAt + 0.12),
          transform: `translate(-50%, -50%) translateY(${lerp(rise, D * 0.25, 0)}px) scale(${lerp(rise, 0.55, 1)})`,
          filter: rise < 0.9 ? `blur(${lerp(rise, 6, 0)}px)` : 'none' }}>
          <div style={{ ...glassBall(look.accent, D), display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={sweep >= 1 ? {} : { WebkitMaskImage: `conic-gradient(#000 ${sweep * 360}deg, transparent ${sweep * 360}deg)`,
              maskImage: `conic-gradient(#000 ${sweep * 360}deg, transparent ${sweep * 360}deg)` }}>
              <Ico name={icon} size={D * 0.5} color="#FFFFFF" stroke={2.2} />
            </div>
          </div>
        </div>
      </div>
      {lines.map((line, i) => {
        const size = fit(line, u(i === 0 ? 82 : 64), inner);
        return (
          <div key={i} style={{ textAlign: 'center', whiteSpace: 'nowrap', marginTop: u(i ? 10 : 4), fontSize: size, fontWeight: i === 0 ? 900 : 800,
            lineHeight: 1.2, minHeight: size * 1.2, color: accent.includes(i) ? look.accent : look.ink }}>
            <Kinetic text={line} now={now} at={Math.max(ats[i], iconAt + 0.25)} gap={0.035} rise={size * 0.3} />
          </div>
        );
      })}
    </Card>
  );
};
