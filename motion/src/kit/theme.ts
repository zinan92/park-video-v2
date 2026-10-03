// 卡片外观由 defaults.yaml / brief.yaml 的 card、accent、overshoot 决定，经 props.style 传进来（见 kit/look.tsx）。
// paper 沿用 Park 认可过的 park-card-overlay-c-v1：纸白底、墨黑字、朱红强调。
export const FONT = '"PingFang SC", "Noto Sans SC", "Hiragino Sans GB", sans-serif';
export const FPS = 30;
// 画布四周给投影留的边（px），卡片本体在这圈以内
export const SHADOW_MARGIN = 28;

export type CardKind = 'glass' | 'paper' | 'dark' | 'none';
export type Palette = { ink: string; muted: string; line: string; fill: string; border: string; shadow: boolean; textShadow: string };

// glass：层里只画一层半透明白（不透明度 glassAlpha），背后的模糊在合成时由 render.py 用原画面做（Remotion 单独渲染层时背后没有东西可模糊）。
// 所以 glass 不能有投影：投影的 alpha 会被当成「这里要模糊」。
export const palette = (card: CardKind, glassAlpha: number): Palette => {
  switch (card) {
    case 'glass':
      return { ink: '#121418', muted: '#3E3F44', line: 'rgba(18,20,24,0.18)', fill: `rgba(255,255,255,${glassAlpha})`,
        border: 'rgba(255,255,255,0.55)', shadow: false, textShadow: 'none' };
    case 'dark':
      return { ink: '#F4F1EA', muted: '#B9B4AA', line: 'rgba(255,255,255,0.18)', fill: 'rgba(20,22,28,0.9)',
        border: 'transparent', shadow: true, textShadow: 'none' };
    case 'none':
      return { ink: '#FFFFFF', muted: '#E8E4DC', line: 'rgba(255,255,255,0.45)', fill: 'transparent',
        border: 'transparent', shadow: false, textShadow: '0 2px 10px rgba(0,0,0,0.75), 0 0 2px rgba(0,0,0,0.9)' };
    default:
      return { ink: '#15171C', muted: '#6B655B', line: '#E4DFD4', fill: 'rgba(244,241,234,0.97)',
        border: 'transparent', shadow: true, textShadow: 'none' };
  }
};
