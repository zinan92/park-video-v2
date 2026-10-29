// ShotCraft 直通：原卡组件原样渲染在 1920×1080 的透明画布上，三件事统一做、原卡源码一行不改：
// 1. 去底：舞台件换成透明（shims/），渲染时再把「铺满整个画面」的元素的底色一律去掉——叠在口播上只留镜头本身；
// 2. 换字：原卡里每段字都经过 __scT（slot-loader.cjs + slot.ts），texts 里给了对照就换成他的原话；
// 3. 时间：从 lead 帧开始播，播完停在最后一帧（ShotCraft 的规矩是收尾真静止）。
// 裁哪一块、放到人脸旁边哪里，由 layers.py 按 manifest 里量好的内容框做（src_rect + fit）。
import React, { useLayoutEffect, useRef } from 'react';
import { Freeze, useCurrentFrame, useVideoConfig } from 'remotion';
// @ts-ignore 由 remotion.config.ts 指到生成的注册表（或空表）
import { REGISTRY } from '@sc-registry';

export type PassProps = { card: string; lead: number; frames: number; texts?: Record<string, string>; look?: string; strip?: boolean };

export const ShotcraftPass: React.FC<PassProps> = ({ card, lead, strip = true }) => {
  const f = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const box = useRef<HTMLDivElement>(null);
  useLayoutEffect(() => {
    if (!strip || !box.current) return;
    const root = box.current.getBoundingClientRect();
    box.current.querySelectorAll<HTMLElement>('*').forEach((el) => {
      const r = el.getBoundingClientRect();
      if (r.width >= 0.9 * root.width && r.height >= 0.9 * root.height) {
        el.style.background = 'transparent';
        el.style.backgroundImage = 'none';
        el.style.boxShadow = 'none';
      }
    });
    // 量卡用：这一帧真正显示出来的字
    (window as unknown as { __scText?: string }).__scText = box.current.innerText;
  });
  const entry = REGISTRY[card];
  if (!entry) throw new Error(`ShotCraft 里没有 ${card}（先 pv2.py shotcraft-sync）`);
  if (f < lead) return null;
  const { C, D } = entry;
  return <div ref={box} style={{ position: 'absolute', inset: 0, width, height }}><Freeze frame={Math.min(f - lead, D - 1)}><C /></Freeze></div>;
};
