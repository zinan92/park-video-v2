// ShotCraft 的底板、颗粒、暗角：叠在口播画面上时都不要（它们只是给全屏黑场 / 白场加质感）。
export * from '@sc-orig/Polish';

export const Backdrop: React.FC<Record<string, unknown>> = () => null;
export const Grain: React.FC<Record<string, unknown>> = () => null;
export const Vignette: React.FC<Record<string, unknown>> = () => null;
