// 生意链路（effort c · 示意图）：一条有先后的链路走到结果——「画完图 → 十分钟打印好 → 寄到你家 → 一年 200 万」。
// 画面：一条 S 形的路从上蜿蜒到下，路上几站。说到哪一站，一颗玻璃球沿路走到那一站（先加速后减速、带拖影），
// 走过的路亮成强调色，那一站亮起、旁边写这一站；最后走到终点，终点长出结果（大字）。
// 动作弧：灰色的路和各站空位先描好（不让卡空着等）→ 标题逐字 → 球一站站走 → 结果。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit, glassBall, Kinetic } from '../kit/parts';
import { useSec } from '../kit/time';

type Beat = { text: string; at: number };
export type JourneyProps = { t0: number; title?: Beat; stops: Beat[]; result?: Beat; arc?: 'light' | 'hero' };

const N = 60;

export const Journey: React.FC<JourneyProps> = ({ t0, title, stops, result, arc = 'light' }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const H = u(118) * (stops.length + (result ? 1 : 0)) + u(40);
  const W = inner * 0.34;
  // S 形路：x 在左右之间摆，y 从上到下
  const pts = Array.from({ length: N + 1 }, (_, i) => {
    const t = i / N;
    return [W / 2 + Math.sin(t * Math.PI * (stops.length + (result ? 1 : 0)) - Math.PI / 2) * W * 0.36, u(16) + t * (H - u(70))];
  });
  const len = pts.slice(1).reduce((s, p, i) => s + Math.hypot(p[0] - pts[i][0], p[1] - pts[i][1]), 0);
  const at = (t: number) => {
    const f = Math.min(N, Math.max(0, t * N));
    const i = Math.floor(f);
    const k = f - i;
    const a = pts[i];
    const b = pts[Math.min(N, i + 1)];
    return [lerp(k, a[0], b[0]), lerp(k, a[1], b[1])];
  };
  const marks = [...stops, ...(result ? [result] : [])];
  const stopT = (i: number) => (i + 1) / marks.length; // 每站在路上的位置
  const progress = (t: number) => {
    let p = 0;
    marks.forEach((m, i) => {
      const from = i === 0 ? 0 : stopT(i - 1);
      p = Math.max(p, lerp(seg(t, m.at, m.at + 0.55, E.inOutCubic), from, stopT(i)) * (t >= m.at ? 1 : 0) || p);
    });
    return p;
  };
  const p = progress(now);
  const draw = seg(now, t0 + 0.05, t0 + 0.6, E.inOutCubic);
  const d = pts.map((q, i) => `${i ? 'L' : 'M'} ${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join(' ');
  const [bx, by] = at(p);
  const ball = u(44);
  // 起点：路的最上端也标一个小点（球从这里出发）
  const labelSize = Math.min(...stops.map((s) => fit(s.text, u(50), inner - W - u(30))));
  return (
    <Card arc={arc}>
      {title ? <div style={{ fontSize: fit(title.text, u(54), inner), fontWeight: 900, color: look.ink, whiteSpace: 'nowrap', marginBottom: u(10) }}>
        <Kinetic text={title.text} now={now} at={title.at} rise={u(16)} />
      </div> : null}
      <div style={{ position: 'relative', width: inner, height: H }}>
        <svg width={W} height={H} style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible' }}>
          <path d={d} fill="none" stroke={look.line} strokeWidth={u(10)} strokeLinecap="round" pathLength={1} strokeDasharray={`${draw} 1`} />
          <path d={d} fill="none" stroke={look.accent} strokeWidth={u(10)} strokeLinecap="round" pathLength={1} strokeDasharray={`${p} 1`} />
          {marks.map((m, i) => {
            const [sx, sy] = at(stopT(i));
            const on = p >= stopT(i) - 1e-3;
            return <circle key={i} cx={sx} cy={sy} r={u(15)} fill={on ? look.accent : '#FFFFFF'} stroke={on ? look.accent : look.muted} strokeWidth={u(4)}
              opacity={seg(now, t0 + 0.2 + i * 0.08, t0 + 0.5 + i * 0.08)} />;
          })}
        </svg>
        {p > 0 && p < 0.999 ? <div style={{ position: 'absolute', left: bx - ball / 2, top: by - ball / 2, ...glassBall(look.accent, ball) }} /> : null}
        {stops.map((s, i) => {
          const [, sy] = at(stopT(i));
          return <div key={i} style={{ position: 'absolute', left: W + u(20), top: sy - labelSize * 0.62, fontSize: labelSize, fontWeight: 800,
            color: look.ink, whiteSpace: 'nowrap' }}><Kinetic text={s.text} now={now} at={s.at + 0.35} gap={0.03} rise={u(12)} /></div>;
        })}
        {result ? (() => {
          const [, sy] = at(1);
          const sz = fit(result.text, u(84), inner - W - u(30));
          return <div style={{ position: 'absolute', left: W + u(20), top: sy - sz * 0.55, fontSize: sz, fontWeight: 900, color: look.accent, whiteSpace: 'nowrap' }}>
            <Kinetic text={result.text} now={now} at={result.at + 0.45} gap={0.05} rise={u(20)} dur={0.45} />
          </div>;
        })() : null}
      </div>
    </Card>
  );
};
