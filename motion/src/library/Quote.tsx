// 引用卡（文字形式，和 TextLines 不同的样子）：左侧强调色竖条 + 大引号，原话左对齐。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { Appear, fit } from '../kit/parts';
import { useSec } from '../kit/time';

export type QuoteProps = { t0: number; lines: string[]; ats: number[]; accent?: number[] };

export const Quote: React.FC<QuoteProps> = ({ t0, lines, ats, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const avail = useInnerWidth() - u(34);
  return (
    <Card>
      <div style={{ display: 'flex' }}>
        <div style={{ width: u(8), borderRadius: u(4), background: look.accent, flexShrink: 0 }} />
        <div style={{ marginLeft: u(26) }}>
          <div style={{ fontSize: u(130), lineHeight: 0.62, height: u(62), fontWeight: 900, color: look.accent, fontFamily: 'Georgia, serif' }}>“</div>
          {lines.map((line, i) => (
            <Appear key={i} now={now} at={ats[i]} rise={u(12)} style={{ whiteSpace: 'nowrap', lineHeight: 1.25, marginTop: u(i ? 10 : 6),
              fontSize: fit(line, u(i === 0 ? 76 : 64), avail), fontWeight: i === 0 ? 800 : 700,
              color: accent.includes(i) ? look.accent : look.ink }}>{line}</Appear>
          ))}
        </div>
      </div>
    </Card>
  );
};
