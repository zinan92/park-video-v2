// 组件注册表：plan.json 里每个镜头的 component 字段写这里的名字。
// 想用 ShotCraft 的某张卡：照它的 demo 源码改编成区域原生组件（用 Card / useU / useSec），再加到这里。
import React from 'react';
import { Compare } from './Compare';
import { Gauge } from './Gauge';
import { ListSteps } from './ListSteps';
import { NumberRoll } from './NumberRoll';
import { TextLines } from './TextLines';
import { BigNumber } from './BigNumber';
import { Bars } from './Bars';
import { Cycle } from './Cycle';
import { Flow } from './Flow';
import { Funnel } from './Funnel';
import { IconList } from './IconList';
import { IconPoint } from './IconPoint';
import { Quote } from './Quote';
import { Ratio } from './Ratio';
import { GlassCycle } from './GlassCycle';
import { HaloNumber } from './HaloNumber';
import { HatchBars } from './HatchBars';
import { IconBloom } from './IconBloom';
import { QuoteMarker } from './QuoteMarker';
import { RingCore } from './RingCore';
import { StackPress } from './StackPress';

export const LIBRARY: Record<string, React.FC<any>> = {
  TextLines, Quote, ListSteps, BigNumber, NumberRoll, Ratio, Bars, Gauge, Cycle, Funnel, Flow, Compare, IconPoint, IconList,
  HaloNumber, HatchBars, GlassCycle, RingCore, StackPress, QuoteMarker, IconBloom,
};
