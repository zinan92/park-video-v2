// 区域原生的卡片：画布就是 brief 推出来的那块区域（左/右），卡片贴着内容的宽度、在区域里居中，四周留投影边。
// 字号用 u()：按区域宽度缩放，600px 宽时 u(1) = 1px。
// 进：10f 淡入 + 上移 24px；出：末 9f 淡出。中间不做任何持续漂移——停住就是停住。
import React, { createContext, useContext } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { E, lerp, seg } from './Motion';
import { FONT, SHADOW_MARGIN } from './theme';
import { useLook } from './look';

const Unit = createContext(1);
export const useU = () => {
  const k = useContext(Unit);
  return (px: number) => px * k;
};

const PAD_X = 42; // 卡片左右内边距（u）

// 卡片里一行字最多能有多宽（px）：给按宽度定字号的组件用
export const useInnerWidth = () => {
  const { width } = useVideoConfig();
  const k = (width - 2 * SHADOW_MARGIN) / 600;
  return width - 2 * SHADOW_MARGIN - 2 * PAD_X * k;
};

// 一行字大约占几个字宽：汉字 1，数字和英文约 0.6
export const emWidth = (text: string) =>
  [...text].reduce((n, ch) => n + (/[\u0000-\u00ff]/.test(ch) ? (/[%@MW]/.test(ch) ? 0.85 : 0.6) : 1), 0);

// arc：卡片自己的动作弧。
//  light（默认）：10f 淡入 + 上移，末 9f 淡出。
//  hero：从人脸那一侧带强减速滑进来（0.6s，outExpo，进场时带一点透视转角，落定后 transform 为 none——
//        3D 变换下文字会糊），一道光沿卡片边缘描一圈后停成细微的边缘高光（0.9s 内停）；
//        末 9f 朝上方收走。只给关键卡用，12 张都这样就成了模板。
export const Card: React.FC<{ children: React.ReactNode; arc?: 'light' | 'hero' }> = ({ children, arc = 'light' }) => {
  const f = useCurrentFrame();
  const { width, durationInFrames: D, fps } = useVideoConfig();
  const k = (width - 2 * SHADOW_MARGIN) / 600;
  const look = useLook();
  const hero = arc === 'hero';
  const pIn = hero ? seg(f, 0, 0.6 * fps, E.outExpo) : seg(f, 0, 10, E.outCubic);
  const pOut = seg(f, D - 9, D - 1, E.inQuad);
  const dir = look.side === 'left' ? 1 : -1; // 左侧的卡从右边（人脸那侧）进来
  const settled = pIn >= 1 && pOut <= 0;
  const transform = settled ? 'none' : hero
    ? `perspective(${1400 * k}px) translate(${lerp(pIn, dir * 34 * k, 0)}px, ${lerp(pIn, 18 * k, 0) - pOut * 14 * k}px) rotateY(${lerp(pIn, -dir * 9, 0)}deg) scale(${lerp(pIn, 0.94, 1)})`
    : `translateY(${lerp(pIn, 24 * k, 0)}px)`;
  const opacity = (hero ? seg(f, 0, 6) : pIn) * (1 - pOut);
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', padding: SHADOW_MARGIN }}>
      <div
        style={{
          position: 'relative', maxWidth: '100%', maxHeight: '100%', boxSizing: 'border-box', padding: `${36 * k}px ${PAD_X * k}px`,
          background: look.fill, borderRadius: 30 * k, border: `${1.5 * k}px solid ${look.border}`,
          boxShadow: look.shadow ? `0 ${10 * k}px ${SHADOW_MARGIN * 0.8}px rgba(0,0,0,0.28)` : 'none',
          textShadow: look.textShadow, fontFamily: FONT, color: look.ink, overflow: 'hidden', display: 'flex', flexDirection: 'column',
          opacity, transform,
        }}
      >
        <Unit.Provider value={k}>{children}</Unit.Provider>
        {hero && look.card !== 'none' ? <EdgeLight f={f} fps={fps} k={k} accent={look.accent} /> : null}
      </div>
    </AbsoluteFill>
  );
};

// 边缘光：一段亮光沿卡片内沿顺时针描一圈（0.1–0.75s），描完整圈停成淡淡的边缘高光（0.9s 后不再变）。
// 画在卡片里面（inset），不往外溢。
const EdgeLight: React.FC<{ f: number; fps: number; k: number; accent: string }> = ({ f, fps, k, accent }) => {
  const t = f / fps;
  const p = seg(t, 0.1, 0.75, E.inOutCubic);
  const rest = seg(t, 0.7, 0.9, E.outCubic);
  if (p <= 0) return null;
  const w = 3 * k;
  return (
    <svg style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', pointerEvents: 'none', overflow: 'hidden' }}>
      <defs>
        <linearGradient id="edge-rim" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#FFFFFF" stopOpacity="0.9" />
          <stop offset="0.5" stopColor={accent} stopOpacity="0.55" />
          <stop offset="1" stopColor="#FFFFFF" stopOpacity="0.25" />
        </linearGradient>
      </defs>
      {/* 描边一半在卡外，被卡片的 overflow:hidden 裁掉，只留内沿那一半 */}
      <rect x={0} y={0} width="100%" height="100%" rx={30 * k} fill="none"
        stroke="url(#edge-rim)" strokeWidth={w * 2} pathLength={1} strokeDasharray={`${p} 1`} opacity={lerp(rest, 1, 0.55)} />
      {/* 描线的头：一小段白亮光跟着走，描完就没了 */}
      {p < 1 ? <rect x={0} y={0} width="100%" height="100%" rx={30 * k} fill="none" stroke="#FFFFFF" strokeWidth={w * 3.2}
        pathLength={1} strokeDasharray={`0.07 1`} strokeDashoffset={-(p - 0.07)} opacity={0.95 * (1 - seg(p, 0.85, 1))} /> : null}
    </svg>
  );
};

export const Kicker: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const u = useU();
  const { muted } = useLook();
  return <div style={{ fontSize: u(26), fontWeight: 600, color: muted, letterSpacing: u(1), marginBottom: u(18) }}>{children}</div>;
};
