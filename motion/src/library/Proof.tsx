// 证据截图卡（10/5 Park）：内容工作台骨架页里点过「要」的真截图——新闻、数据、原推、他自己的后台截图。
// 图在项目的 v2/evidence/ 里（渲染时 --public-dir 指过去），src 是文件名（按内容取哈希：换图就换名，层会重渲）。
// 图在 at 出现（淡入 + 轻微放大落定，0.45s 做完），下面一行来源和日期在 sourceAt（默认 at + 0.3s）出现，之后不动。
import React from 'react';
import { Img, staticFile, useVideoConfig } from 'remotion';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { Appear } from '../kit/parts';
import { SHADOW_MARGIN } from '../kit/theme';
import { useSec } from '../kit/time';

export type ProofProps = { t0: number; src: string; at: number; source: string; sourceAt?: number };

export const Proof: React.FC<ProofProps> = ({ t0, src, at, source, sourceAt }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const { height } = useVideoConfig();
  const w = useInnerWidth();
  const p = seg(now, at, at + 0.45, E.outCubic);
  return (
    <Card>
      <div style={{ opacity: p, transform: p >= 1 ? 'none' : `scale(${lerp(p, 0.96, 1)})`, transformOrigin: 'center top' }}>
        <Img src={staticFile(src)} style={{ display: 'block', width: w, height: 'auto', maxHeight: height - 2 * SHADOW_MARGIN - u(190),
          objectFit: 'contain', borderRadius: u(12), boxShadow: `0 0 0 ${u(1.5)}px ${look.line}` }} />
      </div>
      <Appear now={now} at={sourceAt ?? at + 0.3} rise={u(8)} style={{ marginTop: u(18), maxWidth: w, fontSize: u(34), fontWeight: 600,
        color: look.muted, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{source}</Appear>
    </Card>
  );
};
