import { defineConfig, globalIgnores } from "eslint/config";
import nextPlugin from "@next/eslint-plugin-next";
import tseslint from "typescript-eslint";
export default defineConfig([
  ...tseslint.configs.recommended,
  nextPlugin.configs["core-web-vitals"],
  globalIgnores([
    ".next/**",
    "public/cesium/**",
    "public/plotly/**",
    "next-env.d.ts",
    "playwright-report/**",
    "test-results/**",
  ]),
]);
