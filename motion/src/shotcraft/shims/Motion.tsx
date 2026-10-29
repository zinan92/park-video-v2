// 480×270 设计坐标的舞台：照原样等比放大，只把底色换成透明。
import React from 'react';
import { AbsoluteFill, useVideoConfig } from 'remotion';
export * from '@sc-orig/Motion';

export const DesignStage: React.FC<{ w?: number; h?: number; bg?: string; raster?: 'scale' | 'zoom'; children: React.ReactNode }> = ({
  w = 480, h = 270, raster = 'scale', children,
}) => {
  const { width } = useVideoConfig();
  const scale = width / w;
  return (
    <AbsoluteFill style={{ overflow: 'hidden' }}>
      <div style={{ position: 'absolute', left: 0, top: 0, width: w, height: h, overflow: 'hidden',
        ...(raster === 'zoom' ? { zoom: scale } : { transform: `scale(${scale})`, transformOrigin: 'top left' }) }}>{children}</div>
    </AbsoluteFill>
  );
};
