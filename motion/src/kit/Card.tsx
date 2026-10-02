// 区域原生的纸卡：画布就是 brief 推出来的那块区域（左/右），卡片铺满画布、四周留投影边。
// 字号用 u()：按区域宽度缩放，600px 宽时 u(1) = 1px。
// 进：10f 淡入 + 上移 24px；出：末 9f 淡出。中间不做任何持续漂移——停住就是停住。
import React, { createContext, useContext } from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from 'remotion';
import { E, lerp, seg } from './Motion';
import { FONT, INK, PAPER, SHADOW_MARGIN } from './theme';

const Unit = createContext(1);
export const useU = () => {
  const k = useContext(Unit);
  return (px: number) => px * k;
};

export const Card: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const f = useCurrentFrame();
  const { width, durationInFrames: D } = useVideoConfig();
  const k = (width - 2 * SHADOW_MARGIN) / 600;
  const pIn = seg(f, 0, 10, E.outCubic);
  const pOut = seg(f, D - 9, D - 1, E.inQuad);
  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', padding: SHADOW_MARGIN }}>
      <div
        style={{
          width: '100%', maxHeight: '100%', boxSizing: 'border-box', padding: `${36 * k}px ${42 * k}px`,
          background: PAPER, borderRadius: 30 * k, boxShadow: `0 ${10 * k}px ${SHADOW_MARGIN * 0.8}px rgba(0,0,0,0.28)`,
          fontFamily: FONT, color: INK, overflow: 'hidden', display: 'flex', flexDirection: 'column',
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
  return <div style={{ fontSize: u(26), fontWeight: 600, color: '#6B655B', letterSpacing: u(1), marginBottom: u(18) }}>{children}</div>;
};
