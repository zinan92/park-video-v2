// 这条视频的外观（卡片底色、强调色、能不能冲过头），组件用 useLook() 取，不要再直接写颜色。
import React, { createContext, useContext } from 'react';
import { E } from './Motion';
import { CardKind, palette, Palette } from './theme';

export type Style = { card: CardKind; accent: string; overshoot: boolean; glassAlpha: number };
export const DEFAULT_STYLE: Style = { card: 'paper', accent: '#E2461F', overshoot: false, glassAlpha: 0.45 };

type Look = Palette & { card: CardKind; accent: string; glassAlpha: number; pop: (t: number) => number };

// 毛玻璃是浅灰底，原色朱红字对比度不够：文字用的强调色压暗 30%
const darken = (hex: string, f: number) => {
  const n = parseInt(hex.replace('#', ''), 16);
  const c = (v: number) => Math.round(v * (1 - f)).toString(16).padStart(2, '0');
  return `#${c((n >> 16) & 255)}${c((n >> 8) & 255)}${c(n & 255)}`;
};

const Ctx = createContext<Style>(DEFAULT_STYLE);

export const LookProvider: React.FC<{ style?: Partial<Style>; children: React.ReactNode }> = ({ style, children }) => (
  <Ctx.Provider value={{ ...DEFAULT_STYLE, ...style }}>{children}</Ctx.Provider>
);

export const useLook = (): Look => {
  const s = useContext(Ctx);
  // 圆点、符号的弹出：overshoot 为 false 时直接落定，不冲过头
  const accent = s.card === 'glass' && /^#[0-9a-fA-F]{6}$/.test(s.accent) ? darken(s.accent, 0.3) : s.accent;
  return { ...palette(s.card, s.glassAlpha), card: s.card, accent, glassAlpha: s.glassAlpha,
    pop: s.overshoot ? (t: number) => E.outBack(t) : E.outCubic };
};
