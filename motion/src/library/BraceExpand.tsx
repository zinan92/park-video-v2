// 括号拉幕（effort b · 文字）：形态取自 ShotCraft 的 brace-expand。
// 动作弧：一对强调色花括号在 at 硬切出现（小号、紧贴），随即带一次过冲向两边撑开并放大到标题级；
// 字的露出宽度严格绑在括号间距上（像拉开幕布，从中间往两边露），字和括号共用同一个缩放；
// 落定后字距再松一点。全片只有撑开这一下过冲，at 后约 1.4s 做完，之后一帧不动。
// 文案要短（居中的一个词或短句），字长了括号会裁到字。
import React from 'react';
import { Card, emWidth, Kicker, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { Appear } from '../kit/parts';
import { useSec } from '../kit/time';

export type BraceExpandProps = { t0: number; kicker?: string; kickerAt?: number; text: string; at: number };

const BRACE = 0.36; // 括号中心离字边的距离（字号的倍数）
const RELAX = 0.04; // 落定后每个字多松开的字距（字号的倍数）

export const BraceExpand: React.FC<BraceExpandProps> = ({ t0, kicker, kickerAt, text, at }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const n = [...text].length;
  const size = Math.min(u(96), Math.floor(inner / (emWidth(text) + n * RELAX + 2 * BRACE + 0.8)));
  const on = now >= at ? 1 : 0; // 硬切出现，先看清「这是一对括号」
  const ex = seg(now, at + 0.07, at + 0.77, E.outBack);
  const sc = lerp(ex, 0.6, 1);
  const ls = lerp(seg(now, at + 0.85, at + 1.4, E.inOutQuad), 0, RELAX * size);
  const half = (emWidth(text) * size + n * RELAX * size) / 2 + BRACE * size; // 落定后括号中心离正中多远
  const x = half * ex * sc; // 位移和缩放乘在一起：放大本身也在推开括号
  const boxW = 2 * half + size * 0.8;
  const brace = (ch: string, dx: number) => (
    <div style={{ position: 'absolute', left: '50%', top: '50%', fontSize: size * 1.15, fontWeight: 800, lineHeight: 1, color: look.accent,
      transform: `translate(-50%, -54%) translateX(${dx}px) scale(${sc})`, opacity: on }}>{ch}</div>
  );
  return (
    <Card>
      {kicker ? <Appear now={now} at={kickerAt ?? at} rise={u(10)}><Kicker>{kicker}</Kicker></Appear> : null}
      <div style={{ position: 'relative', width: boxW, height: size * 1.35, alignSelf: 'center' }}>
        <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', width: Math.max(0, 2 * x - size * 0.62),
          height: size * 1.35, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: on }}>
          <div style={{ fontSize: size, fontWeight: 800, whiteSpace: 'nowrap', letterSpacing: ls, color: look.ink,
            transform: sc === 1 ? 'none' : `scale(${sc})` }}>{text}</div>
        </div>
        {brace('{', -x)}
        {brace('}', x)}
      </div>
    </Card>
  );
};
