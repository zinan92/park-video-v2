// 抓重点（effort c · 示意图）：一堆并列的东西里只有一个是关键——「他考虑 10 个因素、20 个因素，真正的主要矛盾只有一个」。
// 做工基准：客户咨询1 旧流程 V04（Park 认可过），形态取自 ShotCraft data/avatar-grid-radial-build-colorize。
// 每个因素是一张小卡：圆角白底、细描边、一道灰条（像一行字）、右上角一个状态点、轻投影——不是抽象圆点。
// 选中那张放大到 1.35（旧版 1.15，这里卡更窄，要让卡里的字够大）。
// 动作：
//   顶部小字（谁在考虑）+ 大号计数，计数从第一档翻到第二档（旧数上飞带模糊、新数从下滑入）；
//   小卡从中心按「环」往外错峰长出来（环号×4f + 随机×3f，只做淡入 + 0.8→1 缩放，不位移），第一档铺内圈、第二档铺外圈；
//   说「摘开」时网格间距拉开（14f）；说到重点时，选中那张的底色、描边、状态点同一条曲线染成强调色、放大 1.15、
//   卡里换成重点的字，其余退到 35%。重点后约 0.6s 做完，之后一帧不动。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { E, lerp, rand, seg } from '../kit/Motion';
import { fit } from '../kit/parts';
import { useSec } from '../kit/time';

type Stage = { count: number; label: string; at: number };
export type PickOneProps = {
  t0: number; who?: { text: string; at: number }; stages: Stage[]; unit?: string;
  focus: { text: string; at: number }; spread?: { at: number }; pick?: number; arc?: 'light' | 'hero';
};

const hex = (h: string): [number, number, number] => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const mix = (a: string, b: string, t: number) => {
  const A = hex(a);
  const B = hex(b);
  return `rgb(${A.map((v, i) => Math.round(v + (B[i] - v) * t)).join(',')})`;
};
const FPS = 30;

export const PickOne: React.FC<PickOneProps> = ({ t0, who, stages, unit, focus, spread, pick, arc = 'hero' }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  const total = Math.max(...stages.map((s) => s.count));
  const cols = total > 12 ? 5 : 4;
  const rows = Math.ceil(total / cols);
  const accent = /^#[0-9a-fA-F]{6}$/.test(look.accent) ? look.accent : '#C0391B';
  const sp = spread ? seg(now, spread.at, spread.at + 14 / FPS, E.outCubic) : 0;
  const gap0 = u(10);
  const gap = lerp(sp, gap0, u(24));
  const cw = (inner - (cols - 1) * u(24)) / cols; // 按拉开后的间距定卡宽，拉开时不出界
  const ch = cw * 0.7;
  const gw = cols * cw + (cols - 1) * gap;
  const gh = rows * ch + (rows - 1) * gap;
  // 每张卡：所在行列、到中心的距离、环号；第一档铺中间几行（内圈），第二档铺外圈
  const base = Array.from({ length: cols * rows }, (_, i) => {
    const r = Math.floor(i / cols);
    const c = i % cols;
    const dist = Math.hypot(c - (cols - 1) / 2, (r - (rows - 1) / 2) / 0.85);
    const outer = Math.abs(r - (rows - 1) / 2) > rows / 4 ? 1 : 0;
    return { i, r, c, dist, ring: Math.round(dist), outer };
  });
  const order = [...base].sort((a, b) => a.outer - b.outer || a.dist - b.dist || a.i - b.i).slice(0, total);
  const target = pick ?? order[Math.min(order.length - 1, 1)].i;
  const raw = (g: (typeof base)[number]) => g.ring * 4 + rand(g.i + 40) * 3;
  const startOf = (k: number) => {
    let lo = 0;
    for (const s of stages) {
      if (k < s.count) {
        const group = order.slice(lo, s.count);
        return s.at + (raw(order[k]) - Math.min(...group.map(raw))) / FPS;
      }
      lo = s.count;
    }
    return Infinity;
  };
  const cT = seg(now, focus.at, focus.at + 6 / FPS, E.outQuad);
  const dim = seg(now, focus.at, focus.at + 6 / FPS, E.outQuad);
  const counts = stages.map((s) => s.count);
  const num = u(96);
  const label = fit(focus.text, u(40), cw * 0.84); // 卡放大 1.35 时字跟着一起放大
  return (
    <Card arc={arc}>
      {who ? <div style={{ fontSize: u(30), fontWeight: 700, color: look.muted, opacity: seg(now, who.at, who.at + 0.25) }}>{who.text}</div> : null}
      <div style={{ position: 'relative', height: num * 1.15, marginTop: u(4), marginBottom: u(18), overflow: 'hidden' }}>
        {stages.map((s, i) => {
          const into = i === 0 ? seg(now, s.at, s.at + 8 / FPS, E.outCubic) : seg(now, s.at, s.at + 8 / FPS, E.outCubic);
          const nx = stages[i + 1];
          const out = nx ? seg(now, nx.at, nx.at + 8 / FPS, E.outCubic) : 0;
          if (into <= 0 || out >= 1) return null;
          const show = into * (1 - out);
          const dy = (1 - into) * num * 0.62 - out * num * 0.62;
          return (
            <div key={i} style={{ position: 'absolute', left: 0, top: 0, whiteSpace: 'nowrap', opacity: show, transform: `translateY(${dy}px)`,
              filter: show < 1 ? `blur(${(1 - show) * 8}px)` : 'none', lineHeight: `${num * 1.15}px` }}>
              <span style={{ fontSize: num, fontWeight: 800, color: look.ink, fontFamily: 'Helvetica, Arial, sans-serif', fontVariantNumeric: 'tabular-nums' }}>{counts[i]}</span>
              <span style={{ fontSize: num * 0.62, fontWeight: 800, color: look.ink, marginLeft: u(10) }}>{unit ?? s.label.replace(/^\d+/, '')}</span>
            </div>
          );
        })}
      </div>
      <div style={{ position: 'relative', width: inner, height: rows * ch + (rows - 1) * u(24) }}>
        {order.map((g, k) => {
          const st = startOf(k);
          const o = seg(now, st, st + 3 / FPS);
          const sc = seg(now, st, st + 5 / FPS, E.outQuad);
          if (o <= 0) return null;
          const red = g.i === target;
          const t = red ? cT : 0;
          const scale = lerp(sc, 0.8, 1) * (red ? lerp(cT, 1, 1.35) : 1);
          const x = (inner - gw) / 2 + g.c * (cw + gap);
          const y = (rows * ch + (rows - 1) * u(24) - gh) / 2 + g.r * (ch + gap);
          return (
            <div key={g.i} style={{ position: 'absolute', left: x, top: y, width: cw, height: ch, boxSizing: 'border-box', borderRadius: u(16),
              background: mix('#FFFFFF', accent, t), border: `${u(2.5)}px solid ${mix('#D6CFC2', accent, t)}`,
              boxShadow: red ? `0 ${lerp(t, u(2), u(14))}px ${lerp(t, u(6), u(30))}px rgba(120,40,20,${lerp(t, 0.06, 0.3)})` : `0 ${u(3)}px ${u(8)}px rgba(0,0,0,0.14)`,
              opacity: o * (red ? 1 : lerp(dim, 1, 0.35)), transform: scale === 1 ? 'none' : `scale(${scale})`, zIndex: red ? 2 : 1,
              display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
              <div style={{ position: 'absolute', left: cw * 0.13, top: ch / 2 - ch * 0.07, width: cw * 0.55, height: ch * 0.14, borderRadius: ch * 0.07,
                background: '#D9D3C7', opacity: 1 - t }} />
              <div style={{ position: 'absolute', right: cw * 0.1, top: ch * 0.14, width: ch * 0.14, height: ch * 0.14, borderRadius: '50%', background: '#9C958A', opacity: 1 - t }} />
              {red ? <div style={{ fontSize: label, fontWeight: 900, color: '#FFFFFF', opacity: t, whiteSpace: 'nowrap' }}>{focus.text}</div> : null}
            </div>
          );
        })}
      </div>
    </Card>
  );
};
