// ShotCraft 原卡的舞台件换成透明：只留镜头本身，背景、主光、暗角、颗粒全部不画（叠在口播画面上用）。
// 调色板跟着这条视频的卡片底色走（渲染参数 look：paper / midnight…）：卡底是浅的，原卡就用浅场配色（深色字），反之亦然。
// 其余导出（TYPE、TextReveal…）原样转出去，原卡源码一行不改。
import React from 'react';
import { getInputProps } from 'remotion';
import { LOOKS as ORIGINAL } from '@sc-orig/Look';
export * from '@sc-orig/Look';

const force = (getInputProps() as { look?: string }).look;
export const LOOKS = force && force in ORIGINAL
  ? new Proxy(ORIGINAL, { get: (t, k) => (typeof k === 'string' && k in t ? t[force] : (t as Record<string | symbol, unknown>)[k]) })
  : ORIGINAL;

export const Stage: React.FC<{ children?: React.ReactNode; style?: React.CSSProperties; [k: string]: unknown }> = ({ children, style }) => {
  const { background, backgroundColor, backgroundImage, ...rest } = style || {};
  return <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', ...rest }}>{children}</div>;
};
