// 两个条件（effort c · 图表）：两个独立条件都满足才成立——「认可你的专业 × 能接受价格 → 成交一单」。
// 画面：两根坐标轴。说到第一个条件时横轴亮起、轴下写条件；说到第二个条件时竖轴亮起、轴旁竖着写条件；
// 说到「两个都满足」时，一颗光点从原点沿弧线飞进右上角，那一格从角上铺满强调色；说到结果时，格子里出现结果和一个勾。
// 动作弧：两根轴的灰线和四个格子先淡淡铺好 → 横轴亮 → 竖轴亮 → 光点飞进去 → 格子铺满 → 结果。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit, Ico, Kinetic, tint } from '../kit/parts';
import { useSec } from '../kit/time';

type Beat = { text: string; at: number };
export type QuadrantProps = { t0: number; x: Beat; y: Beat; both: { at: number }; result: Beat; arc?: 'light' | 'hero' };

export const Quadrant: React.FC<QuadrantProps> = ({ t0, x, y, both, result, arc = 'hero' }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const yLabelW = u(64);
  const S = Math.min(inner - yLabelW - u(10), u(520));
  const setup = seg(now, t0 + 0.05, t0 + 0.55, E.outCubic);
  const ax = seg(now, x.at, x.at + 0.5, E.inOutCubic);
  const ay = seg(now, y.at, y.at + 0.5, E.inOutCubic);
  const fly = seg(now, both.at, both.at + 0.6, E.inOutCubic);
  const fill = seg(now, both.at + 0.5, both.at + 0.9, E.outCubic);
  const res = seg(now, result.at, result.at + 0.35, E.outExpo);
  const o = [0, S];
  const target = [S * 0.75, S * 0.25];
  const ctrl = [S * 0.2, S * 0.2];
  const bez = (t: number) => [
    (1 - t) ** 2 * o[0] + 2 * (1 - t) * t * ctrl[0] + t * t * target[0],
    (1 - t) ** 2 * o[1] + 2 * (1 - t) * t * ctrl[1] + t * t * target[1],
  ];
  const [px, py] = bez(fly);
  const trail = Array.from({ length: 8 }, (_, k) => bez(Math.max(0, fly - k * 0.04)));
  const labelX = fit(x.text, u(46), S);
  const labelY = Math.min(u(46), (S * 0.95) / Math.max(1, [...y.text].length));
  return (
    <Card arc={arc}>
      <div style={{ display: 'flex', alignItems: 'flex-start' }}>
        <div style={{ width: yLabelW, height: S, display: 'flex', alignItems: 'center', justifyContent: 'center', writingMode: 'vertical-rl',
          fontSize: labelY, fontWeight: 800, color: ay > 0 ? look.ink : look.muted, whiteSpace: 'nowrap' }}>
          <Kinetic text={y.text} now={now} at={y.at} gap={0.03} rise={0} />
        </div>
        <div style={{ position: 'relative', width: S, height: S, marginLeft: u(10) }}>
          {[[0, 0], [1, 0], [0, 1], [1, 1]].map(([i, j], k) => (
            <div key={k} style={{ position: 'absolute', left: (i * S) / 2 + u(4), top: (j * S) / 2 + u(4), width: S / 2 - u(8), height: S / 2 - u(8), borderRadius: u(12),
              background: look.line, opacity: 0.45 * setup }} />
          ))}
          <div style={{ position: 'absolute', left: S / 2 + u(4), top: u(4), width: (S / 2 - u(8)) * fill, height: (S / 2 - u(8)) * fill, borderRadius: u(12),
            background: tint(look.accent, 0.9), transformOrigin: 'left bottom', marginTop: (S / 2 - u(8)) * (1 - fill) }} />
          <svg width={S} height={S} style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>
            <line x1={0} y1={S} x2={S} y2={S} stroke={look.line} strokeWidth={u(5)} opacity={setup} />
            <line x1={0} y1={S} x2={0} y2={0} stroke={look.line} strokeWidth={u(5)} opacity={setup} />
            <line x1={0} y1={S} x2={S * ax} y2={S} stroke={look.accent} strokeWidth={u(6)} strokeLinecap="round" />
            <line x1={0} y1={S} x2={0} y2={S * (1 - ay)} stroke={look.accent} strokeWidth={u(6)} strokeLinecap="round" />
            {fly > 0 && fly < 1 ? trail.map(([tx, ty], k) => <circle key={k} cx={tx} cy={ty} r={u(14) * (1 - k / 9)} fill={look.accent} opacity={0.5 * (1 - k / 8)} />) : null}
            {fly > 0 && fill < 1 ? <circle cx={px} cy={py} r={u(16)} fill="#FFFFFF" stroke={look.accent} strokeWidth={u(5)} opacity={1 - fill} /> : null}
          </svg>
          {res > 0 ? (
            <div style={{ position: 'absolute', left: S / 2, top: 0, width: S / 2, height: S / 2, display: 'flex', flexDirection: 'column', alignItems: 'center',
              justifyContent: 'center', opacity: res, transform: res < 1 ? `scale(${lerp(res, 0.7, 1)})` : 'none' }}>
              <Ico name="circle-check" size={u(56)} color="#FFFFFF" stroke={2.6} />
              <div style={{ fontSize: fit(result.text, u(50), S * 0.46), fontWeight: 900, color: '#FFFFFF', whiteSpace: 'nowrap', marginTop: u(6) }}>{result.text}</div>
            </div>
          ) : null}
        </div>
      </div>
      <div style={{ marginLeft: yLabelW + u(10), width: S, textAlign: 'center', fontSize: labelX, fontWeight: 800, color: ax > 0 ? look.ink : look.muted,
        whiteSpace: 'nowrap', marginTop: u(12), minHeight: labelX * 1.2 }}>
        <Kinetic text={x.text} now={now} at={x.at} gap={0.03} rise={u(12)} />
      </div>
    </Card>
  );
};
