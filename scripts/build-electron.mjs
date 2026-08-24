import { build } from "esbuild";

const common = {
  bundle: true,
  platform: "node",
  target: "node22",
  format: "cjs",
  sourcemap: false,
  external: ["electron", "electron/main", "electron/renderer"],
  logLevel: "info",
};

await Promise.all([
  build({
    ...common,
    entryPoints: ["electron/main.ts"],
    outfile: "dist-electron/main.js",
  }),
  build({
    ...common,
    entryPoints: ["electron/preload.ts"],
    outfile: "dist-electron/preload.js",
  }),
]);
