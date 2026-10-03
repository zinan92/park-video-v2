// 图标涟漪（effort c · 图标）：形态取自 ShotCraft 的 radial-wave。
// 他说出这个概念时：强调色玻璃圆盘从中心圆形擦出、露出白色图标，三圈涟漪错峰向外扩散后停在各自的位置（不会一直扩）；
// 一两行字在各自的 at 出现。1.2s 内做完。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { Appear, fit, glassBall, Ico } from '../kit/parts';
import { useSec } from '../kit/time';

export type IconBloomProps = { t0: number; icon: string; iconAt: number; lines: string[]; ats: number[]; accent?: number[] };

export const IconBloom: React.FC<IconBloomProps> = ({ t0, icon, iconAt, lines, ats, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const D = u(180);
  const box = Math.min(inner, D * 2);
  const reveal = seg(now, iconAt, iconAt + 0.45, E.outCubic);
  return (
    <Card>
      <div style={{ position: 'relative', width: box, height: box * 0.86, alignSelf: 'center' }}>
        {[0, 1, 2].map((k) => {
          const q = seg(now, iconAt + 0.15 + k * 0.12, iconAt + 0.95 + k * 0.12, E.outCubic);
          const r = lerp(q, D * 0.5, D * (0.62 + k * 0.17));
          return <div key={k} style={{ position: 'absolute', left: '50%', top: '50%', width: r * 2, height: r * 2, borderRadius: '50%',
            transform: 'translate(-50%, -50%)', border: `${u(3)}px solid ${look.accent}`, opacity: q > 0 ? lerp(q, 0.9, 0.42 - k * 0.12) : 0 }} />;
        })}
        <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', clipPath: `circle(${lerp(reveal, 0, 72)}% at 50% 50%)` }}>
          <div style={{ ...glassBall(look.accent, D), display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Ico name={icon} size={D * 0.5} color="#FFFFFF" stroke={2.2} />
          </div>
        </div>
      </div>
      {lines.map((line, i) => (
        <Appear key={i} now={now} at={ats[i]} rise={u(14)} style={{ textAlign: 'center', whiteSpace: 'nowrap', marginTop: u(i ? 10 : 4),
          fontSize: fit(line, u(i === 0 ? 80 : 62), inner), fontWeight: i === 0 ? 900 : 800, lineHeight: 1.2,
          color: accent.includes(i) ? look.accent : look.ink }}>{line}</Appear>
      ))}
    </Card>
  );
};
