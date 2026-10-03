// 最多 3 行「图标 + 一句话」（图标形式）：每行在 at 出现。
import React from 'react';
import { Card, Kicker, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { Appear, fit, Ico, iconBg } from '../kit/parts';
import { useSec } from '../kit/time';

type Item = { icon: string; text: string; at: number };
export type IconListProps = { t0: number; kicker?: string; items: Item[]; accent?: number[] };

export const IconList: React.FC<IconListProps> = ({ t0, kicker, items, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const box = u(104);
  const textW = inner - box - u(24);
  const size = Math.min(...items.map((it) => fit(it.text, u(76), textW)));
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      {items.map((it, i) => {
        const hot = accent.includes(i);
        return (
          <Appear key={i} now={now} at={it.at} rise={u(14)} style={{ display: 'flex', alignItems: 'center', marginTop: u(i ? 26 : 0) }}>
            <div style={{ width: box, height: box, borderRadius: u(22), flexShrink: 0, display: 'flex', alignItems: 'center',
              justifyContent: 'center', background: hot ? look.accent : iconBg(look.card, look.accent) }}>
              <Ico name={it.icon} size={u(60)} color={hot ? '#FFFFFF' : look.accent} />
            </div>
            <div style={{ marginLeft: u(24), fontSize: size, fontWeight: 700, whiteSpace: 'nowrap',
              color: hot ? look.accent : look.ink }}>{it.text}</div>
          </Appear>
        );
      })}
    </Card>
  );
};
