// 一个关键数字整块出现（数字形式，克制版：不滚动）。unit 跟在数字后面，caption 是下面一行说明。
import React from 'react';
import { Card, useInnerWidth, useU } from '../kit/Card';
import { useLook } from '../kit/look';
import { Appear, fit } from '../kit/parts';
import { useSec } from '../kit/time';

export type BigNumberProps = { t0: number; value: string; unit?: string; at: number; caption?: string; captionAt?: number };

export const BigNumber: React.FC<BigNumberProps> = ({ t0, value, unit, at, caption, captionAt }) => {
  const u = useU();
  const look = useLook();
  const now = useSec(t0);
  const inner = useInnerWidth();
  // 单位按 0.42 倍字号算进宽度
  const size = fit(value + (unit ? '一'.repeat(Math.ceil(unit.length * 0.42)) : ''), u(190), inner);
  return (
    <Card>
      <Appear now={now} at={at} rise={u(18)} style={{ textAlign: 'center', whiteSpace: 'nowrap', lineHeight: 1.05 }}>
        <span style={{ fontSize: size, fontWeight: 900, color: look.accent, fontVariantNumeric: 'tabular-nums', letterSpacing: -size * 0.02 }}>
          {value}
        </span>
        {unit ? <span style={{ fontSize: size * 0.42, fontWeight: 800, color: look.ink, marginLeft: u(8) }}>{unit}</span> : null}
      </Appear>
      {caption ? (
        <Appear now={now} at={captionAt ?? at} rise={u(12)} style={{ textAlign: 'center', whiteSpace: 'nowrap', marginTop: u(12),
          fontSize: fit(caption, u(52), inner), fontWeight: 700, color: look.ink }}>{caption}</Appear>
      ) : null}
    </Card>
  );
};
