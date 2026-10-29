import { Config } from '@remotion/cli/config';
import fs from 'fs';
import os from 'os';
import path from 'path';
import webpack from 'webpack';

Config.setVideoImageFormat('png');
Config.setOverwriteOutput(true);

// ShotCraft 直通（src/shotcraft/）：原卡源码在本机缓存的原仓库里（scripts/shotcraft.py 同步），不进本仓库。
// 原卡 import 的舞台件（_fixtures/Look、Polish、Motion、Brand）换成 src/shotcraft/shims/ 里的透明版，原卡一行不改。
const here = process.cwd();
const repo = process.env.PV2_SHOTCRAFT_REPO || path.join(os.homedir(), '.cache', 'park-video-v2', 'video-shotcraft');
const demos = path.join(repo, 'demos');
const generated = path.join(here, 'src', 'shotcraft', 'registry.generated.ts');
const synced = fs.existsSync(generated) && fs.existsSync(demos);
const registry = synced ? generated : path.join(here, 'src', 'shotcraft', 'registry.empty.ts');
const brand = path.join(here, 'src', 'shotcraft', synced ? 'brand.generated.ts' : 'brand.empty.ts');

Config.overrideWebpackConfig((config) => ({
  ...config,
  resolve: {
    ...config.resolve,
    modules: [path.join(here, 'node_modules'), 'node_modules'],  // 原卡在缓存目录里，react / remotion 从这里找
    alias: { ...(config.resolve?.alias as Record<string, string>), '@sc-registry': registry, '@sc-brand': brand, '@sc-demos': demos,
      '@sc-orig': path.join(demos, '_fixtures') },
  },
  module: {
    ...config.module,
    rules: [
      { test: /\.tsx?$/, include: [demos], enforce: 'pre', use: [{ loader: path.join(here, 'src', 'shotcraft', 'slot-loader.cjs') }] },
      ...(config.module?.rules ?? []),
    ],
  },
  plugins: [
    ...(config.plugins ?? []),
    new webpack.NormalModuleReplacementPlugin(/_fixtures\/(Look|Polish|Motion|Brand)$/, (res) => {
      const m = /_fixtures\/(Look|Polish|Motion|Brand)$/.exec(res.request);
      if (m && res.context.startsWith(demos)) res.request = path.join(here, 'src', 'shotcraft', 'shims', `${m[1]}.tsx`);
    }),
  ],
}));
