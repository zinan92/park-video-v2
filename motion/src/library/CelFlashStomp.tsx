// 底色闪砸字（effort b · 文字）：形态取自 ShotCraft 的 cel-flash-stomp。
// 动作弧：每个词在它的 at 硬切砸下来（0.2s：1.18 倍 → 0.98 → 1，像图章一样歪着，±2.5° 交替，最后一个词摆正），
// 落定那一帧起卡片底色闪几下（每 2 帧一换，共 6 帧；最后一个词 8 帧、对比更强），字纹丝不动——晃的是底，不是字。
// 下一个词出来时上一个词直接切走，最后一个词留着。最后一个词后约 0.5s 做完，之后一帧不动。
// 原卡是给音乐段写的，靠声音撑：Park 在剪映里给每一下砸配一声。一条视频最多用一次。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit, tint } from '../kit/parts';
import { useSec } from '../kit/time';

type Word = { text: string; at: number };
export type CelFlashStompProps = { t0: number; words: Word[] };

const LAND = 0.2; // 6 帧砸落
const FPS = 30;

export const CelFlashStomp: React.FC<CelFlashStompProps> = ({ t0, words }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const size = Math.min(...words.map((w) => fit(w.text, u(150), inner * 0.92))); // 留一点给歪角
  const i = words.reduce((k, w, j) => (now >= w.at ? j : k), -1);
  const last = i === words.length - 1;
  const t = i >= 0 ? now - words[i].at : 0;
  const scale = t < 0.133 ? lerp(seg(t, 0, 0.133, E.outQuint), 1.18, 0.98) : lerp(seg(t, 0.133, LAND, E.outQuad), 0.98, 1);
  const rot = last ? 0 : i % 2 === 0 ? 2.5 : -2.5;
  const f = Math.floor((t - LAND) * FPS + 1e-6);
  const flashing = i >= 0 && f >= 0 && f < (last ? 8 : 6) && Math.floor(f / 2) % 2 === 0;
  return (
    <Card>
      {flashing ? <div style={{ position: 'absolute', inset: 0, background: tint(look.accent, last ? 0.6 : 0.4) }} /> : null}
      <div style={{ position: 'relative', height: size * 1.35, minWidth: inner * 0.92, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        {i >= 0 ? (
          <div style={{ fontSize: size, fontWeight: 900, whiteSpace: 'nowrap', color: last ? look.accent : look.ink,
            transform: t >= LAND && rot === 0 ? 'none' : `scale(${scale}) rotate(${rot}deg)` }}>{words[i].text}</div>
        ) : null}
      </div>
    </Card>
  );
};
