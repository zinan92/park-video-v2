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
