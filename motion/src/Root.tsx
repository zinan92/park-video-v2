// 只有一个合成 Shot：画布尺寸 = 镜头要放的区域，时长 = 镜头时长，全部由 props 决定。
// scripts/layers.py 逐个镜头调用：--props='{"component": "...", "zone": {w, h}, "start", "end", "props": {...}}'
import React from 'react';
import { CalculateMetadataFunction, Composition } from 'remotion';
import { LIBRARY } from './library';
import { FPS } from './kit/theme';

type ShotProps = { component: string; zone: { w: number; h: number }; start: number; end: number; props: Record<string, unknown> };

const Shot: React.FC<ShotProps> = ({ component, start, props }) => {
  const C = LIBRARY[component];
  if (!C) throw new Error(`组件库里没有 ${component}，可用：${Object.keys(LIBRARY).join(', ')}`);
  return <C t0={start} {...props} />;
};

const metadata: CalculateMetadataFunction<ShotProps> = ({ props }) => ({
  width: Math.round(props.zone.w / 2) * 2,
  height: Math.round(props.zone.h / 2) * 2,
  durationInFrames: Math.max(1, Math.round((props.end - props.start) * FPS)),
  fps: FPS,
});

export const Root: React.FC = () => (
  <Composition id="Shot" component={Shot} calculateMetadata={metadata} width={600} height={600} fps={FPS} durationInFrames={90}
    defaultProps={{ component: 'TextLines', zone: { w: 600, h: 600 }, start: 0, end: 3,
      props: { lines: ['示例标题', '第二行'], ats: [0.2, 1.0] } }} />
);
