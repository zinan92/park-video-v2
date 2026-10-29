// 只有一个合成 Shot：画布尺寸 = 镜头要放的区域，时长 = 镜头时长，全部由 props 决定。
// scripts/layers.py 逐个镜头调用：--props='{"component": "...", "zone": {w, h}, "start", "end", "props": {...}}'
import React from 'react';
import { CalculateMetadataFunction, Composition } from 'remotion';
import { LIBRARY } from './library';
import { FPS } from './kit/theme';
import { LookProvider, Style } from './kit/look';
import { PassProps, ShotcraftPass } from './shotcraft/Pass';

type ShotProps = { component: string; zone: { w: number; h: number }; start: number; end: number; props: Record<string, unknown>;
  style?: Partial<Style> };

const Shot: React.FC<ShotProps> = ({ component, start, props, style }) => {
  const C = LIBRARY[component];
  if (!C) throw new Error(`组件库里没有 ${component}，可用：${Object.keys(LIBRARY).join(', ')}`);
  return <LookProvider style={style}><C t0={start} {...props} /></LookProvider>;
};

const metadata: CalculateMetadataFunction<ShotProps> = ({ props }) => ({
  width: Math.round(props.zone.w / 2) * 2,
  height: Math.round(props.zone.h / 2) * 2,
  durationInFrames: Math.max(1, Math.round((props.end - props.start) * FPS)),
  fps: FPS,
});

// ShotCraft 直通：原卡在 1920×1080 透明画布上播（裁剪和摆放在合成时做）
const passMeta: CalculateMetadataFunction<PassProps> = ({ props }) => ({ width: 1920, height: 1080, fps: FPS,
  durationInFrames: Math.max(1, props.frames) });

export const Root: React.FC = () => (
  <>
  <Composition id="ShotcraftPass" component={ShotcraftPass} calculateMetadata={passMeta} width={1920} height={1080} fps={FPS}
    durationInFrames={90} defaultProps={{ card: 'brace-expand', lead: 0, frames: 120 }} />
  <Composition id="Shot" component={Shot} calculateMetadata={metadata} width={600} height={600} fps={FPS} durationInFrames={90}
    defaultProps={{ component: 'TextLines', zone: { w: 600, h: 600 }, start: 0, end: 3,
      props: { lines: ['示例标题', '第二行'], ats: [0.2, 1.0] } }} />
  </>
);
