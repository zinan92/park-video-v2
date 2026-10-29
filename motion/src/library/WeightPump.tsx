// 字重脉冲（effort b · 文字）：形态取自 ShotCraft 的 type-rhythm-sync 里的 font-weight-pump。
// 动作弧：每行在它的 at 升起；在他加重语气的那一刻（pumps，默认就是每行出现时），这一行的笔画瞬间变粗、
// 字重跳到最粗，10 帧内幂衰减弹回（(1-t/10)^0.8，10 帧整归零）；accent 里的行额外横向撑宽 8%。
// 字不位移，只是属性跟着他的重音呼吸。最后一次脉冲后约 0.4s 做完，之后一帧不动。
// 两次脉冲至少隔 0.7s（20 帧），挨太近读作抽搐。一条视频最多用一次。
import React from 'react';
import { Card, Kicker, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { Appear, fit } from '../kit/parts';
import { useSec } from '../kit/time';

type Pump = { at: number; line: number };
export type WeightPumpProps = { t0: number; kicker?: string; lines: string[]; ats: number[]; pumps?: Pump[]; accent?: number[] };

const DECAY = 10; // 帧

const env = (now: number, at: number) => {
  const t = (now - at) * 30;
  return t < 0 || t >= DECAY ? 0 : Math.pow(1 - t / DECAY, 0.8);
};

export const WeightPump: React.FC<WeightPumpProps> = ({ t0, kicker, lines, ats, pumps, accent = [] }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const hits = pumps ?? ats.map((at, line) => ({ at, line }));
  return (
    <Card>
      {kicker ? <Kicker>{kicker}</Kicker> : null}
      {lines.map((line, i) => {
        const e = Math.max(0, ...hits.filter((p) => p.line === i).map((p) => env(now, p.at)));
        const size = fit(line, u(i === 0 ? 96 : 80), inner * 0.9); // 留出撑宽和描边的余量
        const hot = accent.includes(i);
        return (
          <Appear key={i} now={now} at={ats[i]} rise={u(14)} style={{ marginTop: u(i ? 14 : 0), display: 'flex', justifyContent: 'center' }}>
            <div style={{ fontSize: size, lineHeight: 1.25, whiteSpace: 'nowrap', fontWeight: e > 0.15 ? 900 : 700,
              color: hot ? look.accent : look.ink, WebkitTextStroke: e > 0 ? `${size * 0.067 * e}px ${hot ? look.accent : look.ink}` : undefined,
              transform: hot && e > 0 ? `scaleX(${1 + 0.08 * e})` : 'none' }}>{line}</div>
          </Appear>
        );
      })}
    </Card>
  );
};
