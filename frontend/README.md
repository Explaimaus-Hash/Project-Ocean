# Project Ocean frontend

Recovered Next.js/React/TypeScript workspace using Cesium and Plotly, integrated with the existing FastAPI prepared-data APIs. Read [integration instructions and limits](../docs/FRONTEND_INTEGRATION.md) and the root project documents first.

From this directory: `npm.cmd ci`, `npm.cmd run build`, then `npm.cmd run start -- --hostname 127.0.0.1 --port 4317`. Backend must run separately on 127.0.0.1:8000. For editing use `npm.cmd run dev -- --hostname 127.0.0.1 --port 4317` instead.

Checks: `npm.cmd run typecheck`, `npm.cmd run lint`, `npm.cmd run build`, then (both servers running) `npm.cmd exec playwright test -- --config playwright.live.config.ts`. Use this dedicated live config; the recovered older demo tests are not the current live acceptance suite.

Server-only `OCEAN_BACKEND_URL` defaults to `http://127.0.0.1:8000`; configure before building/starting if different. Never expose provider credentials. Browser traffic goes through the fixed same-origin `/backend` proxy. Failed requests do not fall back to demo data.

Source recovery provenance and capability limitations are explicit in the linked integration document. Original supplied frontend is unchanged.
