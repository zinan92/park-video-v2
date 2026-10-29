// __scT：原卡里每段字都经过它（slot-loader.cjs 在每个原卡文件开头 import 它）。
// 原卡很多字是模块一加载就算好的常量，所以对照表在模块加载前就从渲染参数（getInputProps）里读，不等组件渲染。
// 原卡共用的品牌字（video-shotcraft、宣传语）默认换成空：他的视频里不给别人的产品打广告；方案给了对照就用他的话。
import { getInputProps } from 'remotion';
// @ts-ignore 由 remotion.config.ts 指到生成的品牌字表（或空表）
import { BRAND_TEXT } from '@sc-brand';

const given: Record<string, string> = ((getInputProps() as { texts?: Record<string, string> }).texts) || {};
const map: Record<string, string> = { ...Object.fromEntries((BRAND_TEXT as string[]).map((t) => [t, ''])), ...given };
export const seen = new Set<string>();
export const __scT = (s: string): string => {
  seen.add(s);
  return map[s] ?? s;
};
