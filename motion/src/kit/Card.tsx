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

export const Card: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const f = useCurrentFrame();
  const { width, durationInFrames: D } = useVideoConfig();
  const k = (width - 2 * SHADOW_MARGIN) / 600;
  const pIn = seg(f, 0, 10, E.outCubic);
  const pOut = seg(f, D - 9, D - 1, E.inQuad);
  const look = useLook();
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', padding: SHADOW_MARGIN }}>
      <div
        style={{
          maxWidth: '100%', maxHeight: '100%', boxSizing: 'border-box', padding: `${36 * k}px ${PAD_X * k}px`,
          background: look.fill, borderRadius: 30 * k, border: `${1.5 * k}px solid ${look.border}`,
          boxShadow: look.shadow ? `0 ${10 * k}px ${SHADOW_MARGIN * 0.8}px rgba(0,0,0,0.28)` : 'none',
          textShadow: look.textShadow, fontFamily: FONT, color: look.ink, overflow: 'hidden', display: 'flex', flexDirection: 'column',
          opacity: pIn * (1 - pOut), transform: `translateY(${lerp(pIn, 24 * k, 0)}px)`,
        }}
      >
        <Unit.Provider value={k}>{children}</Unit.Provider>
      </div>
    </AbsoluteFill>
  );
};

export const Kicker: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const u = useU();
  const { muted } = useLook();
  return <div style={{ fontSize: u(26), fontWeight: 600, color: muted, letterSpacing: u(1), marginBottom: u(18) }}>{children}</div>;
};
