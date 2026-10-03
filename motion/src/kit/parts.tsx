// 组件共用的小零件：按宽度定字号、克制的出现（淡入 + 上移，0.3s 落定、不冲过头）、图标、强调色浅底。
import React from 'react';
import { icons } from 'lucide-react';
import { E, lerp, seg } from './Motion';
import { emWidth } from './Card';

// 一行不折行时能用的字号：不超过 max，也不超过可用宽度
export const fit = (text: string, max: number, avail: number) => Math.min(max, Math.floor(avail / Math.max(1, emWidth(text))));

// 在 at（原片绝对秒）出现：淡入 + 从下方 rise px 上移，0.3s 落定
export const Appear: React.FC<{ now: number; at: number; rise: number; style?: React.CSSProperties; children: React.ReactNode }> = ({
  now, at, rise, style, children,
}) => {
  const p = seg(now, at, at + 0.3, E.outCubic);
  return <div style={{ ...style, opacity: p, transform: `translateY(${lerp(p, rise, 0)}px)` }}>{children}</div>;
};

// 线条在 at 起 dur 秒内画出来（0→1，缓出、不过冲）
export const draw = (now: number, at: number, dur = 0.5) => seg(now, at, at + dur, E.outCubic);

// lucide 图标，plan.json 里写短横线名字（如 users、trending-up），见 https://lucide.dev/icons
const pascal = (name: string) => name.split('-').map((p) => p.charAt(0).toUpperCase() + p.slice(1)).join('');
export const Ico: React.FC<{ name: string; size: number; color: string; stroke?: number }> = ({ name, size, color, stroke = 2 }) => {
  const C = (icons as Record<string, React.FC<{ size?: number; color?: string; strokeWidth?: number }>>)[pascal(name)];
  if (!C) throw new Error(`图标库里没有 ${name}`);
  return <C size={size} color={color} strokeWidth={stroke} />;
};

// 图标底：浅色卡片上用白底（强调色浅底叠在毛玻璃上发灰），深色/无卡片用强调色浅底
export const iconBg = (card: string, accent: string) => (card === 'dark' || card === 'none' ? tint(accent, 0.22) : 'rgba(255,255,255,0.8)');

// 强调色加透明度当浅底（只认 #rrggbb）
export const tint = (hex: string, alpha: number) =>
  /^#[0-9a-fA-F]{6}$/.test(hex) ? `${hex}${Math.round(alpha * 255).toString(16).padStart(2, '0')}` : hex;

// —— 「像专业 AE」那一档（effort c）共用的质感零件。全部画在卡片里（Card 有 overflow:hidden），
//    不往卡片外溢光、溢阴影：毛玻璃按层的 alpha 做模糊，卡外的半透明会把人脸糊出一圈。
//    每个效果都在给定时间窗里做完，之后完全静止（终检会比 hold 之后的两帧）。

// 一道斜向高光从左扫到右，只扫一次（start 起 dur 秒），扫完消失
export const Sheen: React.FC<{ now: number; start: number; dur?: number }> = ({ now, start, dur = 0.7 }) => {
  const p = seg(now, start, start + dur, E.inOutCubic);
  if (p <= 0 || p >= 1) return null;
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden', borderRadius: 'inherit' }}>
      <div style={{ position: 'absolute', top: '-20%', bottom: '-20%', width: '38%', left: `${lerp(p, -45, 115)}%`,
        transform: 'skewX(-18deg)', background: 'linear-gradient(90deg, rgba(255,255,255,0) 0%, rgba(255,255,255,.55) 50%, rgba(255,255,255,0) 100%)' }} />
    </div>
  );
};

// 45° 斜纹（占位条的「草稿」质感）
export const hatch = (color: string, gap: number) =>
  `repeating-linear-gradient(45deg, ${color} 0 ${gap * 0.42}px, transparent ${gap * 0.42}px ${gap}px)`;

// 玻璃球：顶部高光 + 底部暗面 + 内描边，看起来有体积（颜色 body）
export const glassBall = (body: string, size: number): React.CSSProperties => ({
  width: size, height: size, borderRadius: '50%',
  background: `radial-gradient(circle at 32% 26%, rgba(255,255,255,.55) 0%, rgba(255,255,255,0) 38%), radial-gradient(circle at 50% 120%, rgba(0,0,0,.35) 0%, rgba(0,0,0,0) 55%), ${body}`,
  boxShadow: `inset 0 ${size * 0.03}px ${size * 0.08}px rgba(255,255,255,.35), inset 0 -${size * 0.05}px ${size * 0.1}px rgba(0,0,0,.25)`,
  border: `${Math.max(1, size * 0.012)}px solid rgba(255,255,255,.5)`,
});
