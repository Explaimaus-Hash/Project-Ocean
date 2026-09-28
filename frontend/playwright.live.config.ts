import {defineConfig} from "@playwright/test";
export default defineConfig({
  testDir:"./tests",testMatch:"live-integration.spec.ts",workers:1,fullyParallel:false,timeout:60000,
  use:{baseURL:"http://127.0.0.1:4317",viewport:{width:1440,height:960},launchOptions:{channel:"msedge",args:["--enable-unsafe-swiftshader"]},screenshot:"only-on-failure"},
});
