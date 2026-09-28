import type { NextConfig } from "next";
const config: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  allowedDevOrigins: ["127.0.0.1"],
  async rewrites() {
    // Server-only configured origin: no browser-controlled proxy destination.
    const backend = process.env.OCEAN_BACKEND_URL ?? "http://127.0.0.1:8000";
    const url = new URL(backend);
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.pathname !== '/' || url.search || url.hash)
      throw new Error('OCEAN_BACKEND_URL must be an HTTP(S) origin without credentials');
    return [
      {source:'/backend/health',destination:`${url.origin}/health`},
      {source:'/backend/ready',destination:`${url.origin}/ready`},
      {source:'/backend/api/v1/:path*',destination:`${url.origin}/api/v1/:path*`},
    ];
  },
};
export default config;
