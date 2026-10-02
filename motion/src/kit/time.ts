// 时间约定：props 里所有时刻都写口播原片的绝对秒（查 words.json），组件用 t0（镜头起点）换算成本镜头的帧。
import { useCurrentFrame } from 'remotion';
import { FPS } from './theme';

export const useSec = (t0: number) => {
  const f = useCurrentFrame();
  return f / FPS + t0; // 当前帧对应的原片绝对秒
};
