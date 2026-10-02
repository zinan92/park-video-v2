// 组件注册表：plan.json 里每个镜头的 component 字段写这里的名字。
// 想用 ShotCraft 的某张卡：照它的 demo 源码改编成区域原生组件（用 Card / useU / useSec），再加到这里。
import React from 'react';
import { Compare } from './Compare';
import { Gauge } from './Gauge';
import { ListSteps } from './ListSteps';
import { NumberRoll } from './NumberRoll';
import { TextLines } from './TextLines';

export const LIBRARY: Record<string, React.FC<any>> = { TextLines, NumberRoll, ListSteps, Compare, Gauge };
