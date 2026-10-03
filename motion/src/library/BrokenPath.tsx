// 断裂（effort c · 示意图）：过去走通的路，延伸不到未来——「你过去的成功，不能变成你未来的成功要素」。
// 画面：左上「过去的成功」一颗实心节点，一条强调色的线从它出发往右下方描过去；
// 说到「不能 / 未来」时线在中途咔地裂开：裂口两边是锯齿，后半截掉下去一点、褪成灰色虚线；
// 裂口上方一个大「≠」落下；右下终点「未来的成功要素」只有一个空心灰圈，够不着。
// 动作弧：两头的节点位置先淡淡标好 → 过去节点亮起、线描出去 → 裂开、后半截掉落 → ≠ 落下 → 未来那头的字出现。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit, Kinetic } from '../kit/parts';
import { useSec } from '../kit/time';

type Beat = { text: string; at: number };
export type BrokenPathProps = { t0: number; from: Beat; to: Beat; breakAt?: number; arc?: 'light' | 'hero' };

export const BrokenPath: React.FC<BrokenPathProps> = ({ t0, from, to, breakAt, arc = 'hero' }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const W = inner;
  const H = u(400);
  const A = [u(50), u(70)];
  const B = [W - u(50), H - u(70)];
  const M = [lerp(0.5, A[0], B[0]), lerp(0.5, A[1], B[1])];
  const brk = breakAt ?? to.at;
  const setup = seg(now, t0 + 0.05, t0 + 0.5, E.outCubic);
  const node = seg(now, from.at, from.at + 0.35, E.outExpo);
  const line = seg(now, from.at + 0.2, from.at + 1.2, E.inOutCubic);
  const crack = seg(now, brk, brk + 0.12, E.outCubic);
  const drop = seg(now, brk + 0.08, brk + 0.55, E.inCubic);
  const neq = seg(now, brk + 0.25, brk + 0.6, E.outExpo);
  const lineEnd = [lerp(line, A[0], B[0]), lerp(line, A[1], B[1])];
  const firstEnd = line < 0.5 ? lineEnd : M;
  const gapV = u(16);
  const dir = [(B[0] - A[0]) / Math.hypot(B[0] - A[0], B[1] - A[1]), (B[1] - A[1]) / Math.hypot(B[0] - A[0], B[1] - A[1])];
  const left = [M[0] - dir[0] * gapV * crack, M[1] - dir[1] * gapV * crack];
  const right = [M[0] + dir[0] * gapV * crack, M[1] + dir[1] * gapV * crack + drop * u(40)];
  const tail = [lineEnd[0], lineEnd[1] + drop * u(40)];
  const jag = (p: number[], s: number) => `${p[0]},${p[1]} ${p[0] + s * u(8)},${p[1] - u(12)} ${p[0] - s * u(6)},${p[1] - u(20)} ${p[0] + s * u(4)},${p[1] + u(12)}`;
  const fromSize = fit(from.text, u(56), W * 0.6);
  const toSize = fit(to.text, u(52), W * 0.75);
  return (
    <Card arc={arc}>
      <div style={{ position: 'relative', width: W, height: H + toSize * 1.4 }}>
        <svg width={W} height={H} style={{ position: 'absolute', inset: 0, overflow: 'visible' }}>
          <circle cx={A[0]} cy={A[1]} r={u(26)} fill="none" stroke={look.line} strokeWidth={u(3)} strokeDasharray={`${u(4)} ${u(6)}`} opacity={setup * (1 - node)} />
          <circle cx={B[0]} cy={B[1]} r={u(26)} fill="none" stroke={look.muted} strokeWidth={u(4)} strokeDasharray={`${u(4)} ${u(6)}`} opacity={setup} />
          {line > 0 ? <line x1={A[0]} y1={A[1]} x2={crack > 0 ? left[0] : firstEnd[0]} y2={crack > 0 ? left[1] : firstEnd[1]} stroke={look.accent} strokeWidth={u(9)} strokeLinecap="round" /> : null}
          {line > 0.5 ? <line x1={crack > 0 ? right[0] : M[0]} y1={crack > 0 ? right[1] : M[1]} x2={tail[0]} y2={tail[1]} stroke={crack > 0 ? look.muted : look.accent}
            strokeWidth={u(9)} strokeLinecap="round" strokeDasharray={drop > 0.3 ? `${u(10)} ${u(12)}` : undefined} opacity={lerp(drop, 1, 0.55)} /> : null}
          {crack > 0 ? <>
            <polyline points={jag(left, 1)} fill="none" stroke={look.accent} strokeWidth={u(4)} strokeLinejoin="bevel" />
            <polyline points={jag(right, -1)} fill="none" stroke={look.muted} strokeWidth={u(4)} strokeLinejoin="bevel" opacity={lerp(drop, 1, 0.6)} />
          </> : null}
          <circle cx={A[0]} cy={A[1]} r={u(26) * lerp(node, 0.4, 1)} fill={look.accent} opacity={node} />
        </svg>
        <div style={{ position: 'absolute', left: A[0] + u(40), top: A[1] - fromSize * 0.65, fontSize: fromSize, fontWeight: 900, color: look.ink, whiteSpace: 'nowrap' }}>
          <Kinetic text={from.text} now={now} at={from.at + 0.1} rise={u(16)} />
        </div>
        {neq > 0 ? <div style={{ position: 'absolute', left: M[0] + u(30), top: M[1] - u(130), fontSize: u(110), fontWeight: 900, color: look.accent, lineHeight: 1,
          opacity: neq, transform: neq < 1 ? `translateY(${lerp(neq, -u(40), 0)}px)` : 'none' }}>≠</div> : null}
        <div style={{ position: 'absolute', right: 0, top: H - u(20), fontSize: toSize, fontWeight: 900, color: look.muted, whiteSpace: 'nowrap', textAlign: 'right' }}>
          <Kinetic text={to.text} now={now} at={to.at + 0.2} gap={0.04} rise={u(16)} />
        </div>
      </div>
    </Card>
  );
};
