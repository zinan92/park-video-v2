// 断裂（effort c · 示意图）：过去让你成功的那些条件，接不到未来——「你过去的成功，不能变成你未来的成功要素」。
// 做工基准：客户咨询1 旧流程 V09（Park 认可过）：两栏标题 + 短粗下划线，条件一行行在口播词首 blur-slide 入场；
// 说到「未来」的那一帧，朱红「≠」弹入、分隔线从中点向两头描开表示断开；右栏写未来那头的逻辑。
// 这里的区域在人脸旁边，比旧版窄，所以上下排：上「过去」+ 条件，中间一道从 ≠ 向左右描开的断开线，下「未来」+ 它的逻辑。
// 比旧版多一拍：说到未来那头的最后一句（「平台有平台的逻辑」）时，上面过去的条件退淡——它们接不过来。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, seg } from '../kit/Motion';
import { fit } from '../kit/parts';
import { useSec } from '../kit/time';

type Beat = { text: string; at: number };
export type BrokenPathProps = { t0: number; from: Beat; to: Beat; past?: Beat[]; future?: Beat[]; arc?: 'light' | 'hero' };

// blur-slide：y 24→0、blur 10→0、透明度 0→1，0.33s outCubic（旧版 kit Reveal）
const Reveal: React.FC<{ now: number; at: number; dy: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ now, at, dy, style, children }) => {
  const p = seg(now, at, at + 0.33, E.outCubic);
  return <div style={{ ...style, opacity: p * ((style?.opacity as number) ?? 1), transform: p < 1 ? `translateY(${lerp(p, dy, 0)}px)` : 'none',
    filter: p < 1 ? `blur(${(1 - p) * 10}px)` : 'none' }}>{children}</div>;
};

export const BrokenPath: React.FC<BrokenPathProps> = ({ t0, from, to, past = [], future = [], arc = 'hero' }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const W = useInnerWidth();
  const titleSize = Math.min(fit(from.text, u(50), W * 0.9), fit(to.text, u(50), W * 0.9));
  const rowSize = Math.min(u(38), ...past.map((b) => fit(b.text, u(38), W - u(40))));
  const last = future[future.length - 1];
  const futSize = (b: Beat) => (b === last ? fit(b.text, u(44), W) : fit(b.text, u(34), W));
  const split = to.at;
  const neqRaw = seg(now, split, split + 0.33, E.linear);
  const neq = now < split ? 0 : look.pop(neqRaw);
  const div = seg(now, split, split + 0.4, E.outCubic);
  const fade = last ? seg(now, last.at + 0.1, last.at + 0.6, E.outCubic) : 0;
  const bar = (at: number, color: string) => (
    <div style={{ height: u(5), width: u(110), borderRadius: u(3), background: color, margin: `${u(16)}px 0 ${u(22)}px`, transformOrigin: 'left center',
      transform: `scaleX(${seg(now, at + 0.13, at + 0.5, E.outCubic)})` }} />
  );
  const gutter = u(112);
  return (
    <Card arc={arc}>
      <div style={{ width: W }}>
        {/* 过去 */}
        <Reveal now={now} at={from.at} dy={u(24)} style={{ fontSize: titleSize, fontWeight: 900, color: look.ink, whiteSpace: 'nowrap', lineHeight: 1.2 }}>{from.text}</Reveal>
        {bar(from.at, look.ink)}
        <div style={{ minHeight: past.length * rowSize * 1.65 }}>
          {past.map((b) => (
            <Reveal key={b.text} now={now} at={b.at} dy={u(20)} style={{ display: 'flex', alignItems: 'center', height: rowSize * 1.65, opacity: lerp(fade, 1, 0.55) }}>
              <div style={{ width: u(10), height: u(10), borderRadius: '50%', background: look.muted, marginRight: u(18), flexShrink: 0 }} />
              <div style={{ fontSize: rowSize, fontWeight: 600, color: look.ink, whiteSpace: 'nowrap' }}>{b.text}</div>
            </Reveal>
          ))}
        </div>

        {/* 断开：分隔线从 ≠ 向左右描开 */}
        <div style={{ position: 'relative', height: gutter }}>
          <div style={{ position: 'absolute', top: gutter / 2 - u(2), left: lerp(div, W / 2, 0), width: lerp(div, 0, W), height: u(4), borderRadius: u(2), background: look.line }} />
          {neqRaw > 0 ? (
            <div style={{ position: 'absolute', left: W / 2 - u(48), top: gutter / 2 - u(48), width: u(96), height: u(96), borderRadius: '50%',
              background: look.card === 'glass' ? 'rgba(255,255,255,0.92)' : look.fill, display: 'flex', alignItems: 'center', justifyContent: 'center',
              opacity: Math.min(1, neqRaw * 2.5), transform: neq < 1 || neq > 1 ? `scale(${lerp(neq, 0.4, 1)})` : 'none',
              boxShadow: `0 0 0 ${u(3)}px ${look.line}` }}>
              <div style={{ fontSize: u(92), fontWeight: 700, color: look.accent, lineHeight: 1, fontFamily: 'Helvetica, Arial, sans-serif', marginTop: -u(8) }}>≠</div>
            </div>
          ) : null}
        </div>

        {/* 未来 */}
        <Reveal now={now} at={split} dy={u(24)} style={{ fontSize: titleSize, fontWeight: 900, color: look.ink, whiteSpace: 'nowrap', lineHeight: 1.2 }}>
          {to.text}
        </Reveal>
        {bar(split, look.accent)}
        <div style={{ minHeight: future.reduce((n, b) => n + futSize(b) * 1.45, 0) }}>
          {future.map((b) => (
            <Reveal key={b.text} now={now} at={b.at} dy={u(20)} style={{ fontSize: futSize(b), fontWeight: b === last ? 900 : 600,
              color: b === last ? look.accent : look.muted, whiteSpace: 'nowrap', lineHeight: 1.45 }}>{b.text}</Reveal>
          ))}
        </div>
      </div>
    </Card>
  );
};
