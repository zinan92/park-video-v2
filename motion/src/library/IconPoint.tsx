// 一个图标 + 一两行字（图标形式）：图标放在强调色浅底圆里，字在下方居中。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { Appear, fit, Ico, iconBg } from '../kit/parts';
import { useSec } from '../kit/time';

export type IconPointProps = { t0: number; icon: string; iconAt: number; lines: string[]; ats: number[]; accent?: number[] };

export const IconPoint: React.FC<IconPointProps> = ({ t0, icon, iconAt, lines, ats, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  return (
    <Card>
      <Appear now={now} at={iconAt} rise={u(14)} style={{ alignSelf: 'center', marginBottom: u(22) }}>
        <div style={{ width: u(170), height: u(170), borderRadius: '50%', background: iconBg(look.card, look.accent),
          display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Ico name={icon} size={u(96)} color={look.accent} />
        </div>
      </Appear>
      {lines.map((line, i) => (
        <Appear key={i} now={now} at={ats[i]} rise={u(14)} style={{ textAlign: 'center', whiteSpace: 'nowrap',
          fontSize: fit(line, u(i === 0 ? 84 : 64), inner), fontWeight: i === 0 ? 800 : 700, lineHeight: 1.25,
          marginTop: u(i ? 10 : 0), color: accent.includes(i) ? look.accent : look.ink }}>{line}</Appear>
      ))}
    </Card>
  );
};
