// 流程（示意图形式）：2–3 个框自上而下，中间是向下箭头；accent 里的框用强调色实底。每个框在 at 出现。
import React from 'react';
import { Card, Kicker, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { Appear, fit, Ico } from '../kit/parts';
import { useSec } from '../kit/time';

type Step = { text: string; at: number };
export type FlowProps = { t0: number; kicker?: string; steps: Step[]; accent?: number[] };

export const Flow: React.FC<FlowProps> = ({ t0, kicker, steps, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const size = Math.min(...steps.map((s) => fit(s.text, u(72), inner - u(60))));
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      <div style={{ width: inner }}>
        {steps.map((s, i) => {
          const hot = accent.includes(i);
          return (
            <Appear key={i} now={now} at={s.at} rise={u(12)}>
              {i ? (
                <div style={{ display: 'flex', justifyContent: 'center', margin: `${u(6)}px 0` }}>
                  <Ico name="arrow-down" size={u(56)} color={look.accent} stroke={2.6} />
                </div>
              ) : null}
              <div style={{ borderRadius: u(20), padding: `${u(20)}px ${u(28)}px`, textAlign: 'center', whiteSpace: 'nowrap',
                border: `${u(3)}px solid ${hot ? look.accent : look.line}`, background: hot ? look.accent : 'transparent',
                fontSize: size, fontWeight: 800, color: hot ? '#FFFFFF' : look.ink }}>{s.text}</div>
            </Appear>
          );
        })}
      </div>
    </Card>
  );
};
