import { cp, mkdir } from "node:fs/promises";
import { resolve } from "node:path";
await mkdir("public/cesium", { recursive: true });
await cp(
  resolve("node_modules/cesium/Build/Cesium/Cesium.js"),
  resolve("public/cesium/Cesium.js"),
);
await cp(
  resolve("node_modules/cesium/LICENSE.md"),
  resolve("public/cesium/LICENSE.md"),
);
for (const directory of ["Workers", "Assets", "Widgets", "ThirdParty"]) {
  await cp(
    resolve("node_modules/cesium/Build/Cesium", directory),
    resolve("public/cesium", directory),
    { recursive: true },
  );
}
await mkdir("public/plotly", { recursive: true });
await cp(
  resolve("node_modules/plotly.js-cartesian-dist-min/plotly-cartesian.min.js"),
  resolve("public/plotly/plotly-cartesian.min.js"),
);
await cp(
  resolve("node_modules/plotly.js-cartesian-dist-min/LICENSE"),
  resolve("public/plotly/LICENSE"),
);
