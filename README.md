<div align="center">

# Project Ocean

### Ocean models and observations. One interactive workspace.

A browser-native ocean-data visualization platform built with **Next.js · CesiumJS · FastAPI · Python**.

[Overview](#overview) · [Features](#features) · [Quick start](#quick-start) · [Data sources](#data-sources) · [Documentation](#documentation)

</div>

---

> **Status — local working prototype · September 28, 2026**  
> The frontend and backend are integrated with prepared local data. This is not a production deployment or an independently validated scientific comparison system.

## Overview

Project Ocean brings numerical ocean models and in-situ observations into a shared, interactive workspace designed around the INCOIS visualization problem statement. Explore surface fields on a 3D globe, select actual source timestamps, inspect grid-cell time series, and review observation quality and model–observation comparison results.

The project preserves **INCOIS, Copernicus Marine, Argo and IFREMER gliders** together. Their availability and scientific readiness are tracked separately: a downloaded file is not automatically ready for comparison.

The common project comparison region is **30°E–120°E, 30°S–30°N**. This is a working selection, not a claim that every source shares the same coverage.

## Features

| Workspace | Available now |
| --- | --- |
| **Explorer** | Cesium globe, prepared BIO-ROMS surface temperature/salinity, colour controls, observation overlays and grid-cell inspection. |
| **Timeline** | 480 actual source timestamps, exact UTC selection, playback, bounded next-frame prefetch and visual crossfades. |
| **Analysis** | Scientific grid-cell time series with units, source location and provenance; PNG and plotted-data CSV exports. |
| **Profiles** | Observation samples with QC and raw/adjusted provenance. The current Argo selection contains points, not identified vertical profiles. |
| **Comparison** | A saved, explicitly exploratory Copernicus salinity–Argo result, with matched/excluded samples and summary statistics. |
| **Data Sources** | Source registry, acquisition status and prepared-product metadata, with unavailable capabilities kept explicit. |

### Built for clear, responsive exploration

- Keep the previous labelled frame visible while new data loads.
- Crossfade prepared display rasters over **480ms**, respecting reduced-motion preferences.
- Preserve colour settings across compatible batches and keep the bottom timeline layout stable.
- Accept only available source timestamps—no invented dates or silent nearest-time substitution.
- Keep chart headings, units and provenance readable on narrow and wide screens.
- Show actual errors and retry actions; never substitute demo data after a live request fails.

Visual blending does **not** create intermediate scientific measurements. Scientific values, masks, inspection results and comparison inputs remain separate from display previews.

## Data sources

| Source | Role | Current local integration |
| --- | --- | --- |
| **INCOIS BIO-ROMS V2** | Surface model fields | Verified local input; SST and SSS prepared for all 480 source timestamps. Other fields are not yet served by this workflow. |
| **INCOIS GODAS** | Physical ocean model | Operator acquisition support and catalogue references exist; local access attempts timed out. Not currently a working globe layer. |
| **Copernicus Marine** | Numerical physical ocean model | A small four-variable selection was acquired and a native model product prepared; used in the saved exploratory comparison. Not a full-archive globe layer. |
| **Argo Global** | In-situ float observations | Official observations accessed through Argopy; 14 preserved local samples with QC and provenance. Argopy is the access client, not the data owner. |
| **IFREMER gliders** | In-situ glider observations | Bella acquisition succeeded; unresolved time metadata/QC constraints prevent claiming a scientifically ready glider layer. |

### Prepared BIO-ROMS archive

| Property | Current selection |
| --- | --- |
| Variables | SST and SSS |
| Time coverage | **1980-01-24 → 2019-12-25** |
| Available timestamps | **480 actual source dates**, not daily coverage |
| Region | 30–120°E / 30°S–30°N, bounded by native cell centres |
| Storage | 120 immutable four-date products, plus the preserved original three-date product |
| Resolution | Native scientific data and separate stride-8 display previews |

The frontend combines compatible batches into one timeline. **Analysis charts currently cover the selected batch**, not a concatenated 480-point full-history series.

See [archive preparation and verification](docs/BIO_ROMS_ARCHIVE.md) for exact coverage, commands and limits.

## Tech stack

| Layer | Technologies |
| --- | --- |
| Web application | Next.js, React, TypeScript |
| Globe and charts | CesiumJS, Plotly.js, Lucide icons |
| API | FastAPI, Uvicorn, Pydantic |
| Scientific processing | Python 3.12, netCDF4, NumPy, xarray, pandas, cftime, GSW |
| Source access | Copernicus Marine Toolbox, Argopy, pydap, Python ftplib |
| Quality checks | pytest, HTTPX, Ruff, TypeScript, ESLint, Playwright |

Dependency versions are pinned in [backend requirements](backend/requirements.txt) and the frontend [package manifest](frontend/package.json) / [lockfile](frontend/package-lock.json). Reuse the project environment rather than global Python packages.

## Architecture

~~~mermaid
flowchart LR
    A[INCOIS · Copernicus · Argo · Gliders] --> B[Explicit operator acquisition]
    B --> C[Preserved local inputs]
    C --> D[Bounded preparation and QC]
    D --> E[Scientific products and display previews]
    E --> F[Read-only FastAPI endpoints]
    F --> G[Next.js same-origin proxy]
    G --> H[Cesium globe and Plotly charts]
~~~

Raw NetCDF files are **not sent to the browser**. The backend serves bounded, prepared selections; the frontend requests the data needed for the current view.

Downloads, preparation and matching are explicit operator workflows. They do not run during application startup, health checks or browser requests. Provider credentials remain server-side.

See [ARCHITECTURE.md](ARCHITECTURE.md) for component contracts, scientific decisions and their rationale.

## Quick start

The commands below use **Windows PowerShell**. Run them from the project root, **ocean_2**, unless a step says otherwise.

### 1. Prerequisites

- Python **3.12**; the existing local environment is named **ocean-env**.
- Node.js and npm; local verification used **Node 24.20.0**.
- A WebGL-capable browser. The live browser test configuration uses Microsoft Edge.
- Prepared local products for populated data views. Raw inputs and generated data are not included in a source-only checkout.

> A fresh checkout can run the backend health endpoint without ocean data. It will not reproduce the populated local globe until the required inputs have been acquired and prepared. Follow the [data workflow](docs/BIO_ROMS_ARCHIVE.md); startup does not download datasets.

### 2. Install dependencies

Create the environment **only if ocean-env does not already exist**:

~~~powershell
py -3.12 -m venv ocean-env
~~~

Install backend dependencies into that environment:

~~~powershell
.\ocean-env\Scripts\python.exe -m pip install -r .\backend\requirements-dev.txt
.\ocean-env\Scripts\python.exe -m pip check
~~~

Install the frontend from its lockfile:

~~~powershell
Set-Location .\frontend
npm.cmd ci
Set-Location ..
~~~

Environment activation is optional because these commands use the Python executable explicitly. Keep the pinned Argopy/erddapy combination: independently upgrading erddapy previously broke imports in this build.

### 3. Start the backend

In the first terminal, from the project root:

~~~powershell
# Existing local starting product; use this ID only if its prepared files exist.
$env:OCEAN_REQUIRED_PRODUCT_IDS='["p_7c8210052d41d41259724e2d"]'
.\ocean-env\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
~~~

On a fresh checkout, omit that environment setting until you have a valid prepared product. The health endpoint can still succeed; readiness intentionally returns HTTP 503 when required products are unconfigured or unavailable.

### 4. Start the frontend

In a second terminal, from the project root:

~~~powershell
Set-Location .\frontend
npm.cmd run build
npm.cmd run start -- --hostname 127.0.0.1 --port 4317
~~~

Open **[Project Ocean → Explorer](http://127.0.0.1:4317/explorer)**.

For frontend development, run this from the frontend directory **instead of** the production server:

~~~powershell
npm.cmd run dev -- --hostname 127.0.0.1 --port 4317
~~~

Do not run development and production servers on the same port. Rebuild after source/config changes when using production start. Stop a foreground server with **Ctrl+C**.

### Local endpoints

| Address | Purpose |
| --- | --- |
| [127.0.0.1:4317/explorer](http://127.0.0.1:4317/explorer) | Interactive application |
| [127.0.0.1:8000/health](http://127.0.0.1:8000/health) | Process liveness; no dataset or provider work |
| [127.0.0.1:8000/ready](http://127.0.0.1:8000/ready) | Availability of explicitly configured prepared products |
| [127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | FastAPI interactive API documentation |

Health is not data readiness, and data readiness is not scientific comparison readiness. The default Swagger page uses external assets; its browser UI may need internet even when local endpoints work.

## Configuration and security

| Environment variable | Purpose |
| --- | --- |
| OCEAN_BACKEND_URL | Server-only Next.js backend origin; defaults to http://127.0.0.1:8000. Set before frontend build/start if changing it. |
| OCEAN_REQUIRED_PRODUCT_IDS | Backend JSON list of required prepared product IDs for readiness. |
| OCEAN_DOCS_ENABLED | Enable/disable developer docs and OpenAPI; defaults to true. |
| OCEAN_PROJECT_ROOT | Optional absolute trusted backend project root. |
| COPERNICUSMARINE_SERVICE_USERNAME | Private operator-side Copernicus username for live acquisition. |
| COPERNICUSMARINE_SERVICE_PASSWORD | Private operator-side Copernicus password for live acquisition. |

The backend reads process environment settings; [backend/.env.example](backend/.env.example) is a reference, **not an automatically loaded file**. Browsers use the same-origin backend proxy and never require a provider login.

Never put credentials in public frontend environment variables, source files, browser storage, logs or commits. Keep raw/prepared data, virtual environments and private history out of the repository. Viewing the existing prepared local data does not require another provider download or login.

## Project structure

~~~text
ocean_2/
├── backend/       # FastAPI application, scientific services and Python tests
├── frontend/      # Next.js workspace, Cesium/Plotly views and browser tests
├── config/        # Source registry, bounded processing and comparison policies
├── scripts/       # Explicit acquisition, preparation, audit and verification tools
├── docs/          # API guides, design records and milestone evidence
├── data/          # Private local inputs and prepared products; Git-ignored
├── ocean-env/     # Local Python environment; Git-ignored
└── README.md      # Project overview and getting started
~~~

See [FILE_STRUCTURE.md](FILE_STRUCTURE.md) for module-level responsibilities.

## Testing

From the project root:

~~~powershell
.\ocean-env\Scripts\python.exe -m pytest -c backend/pyproject.toml backend/tests
.\ocean-env\Scripts\python.exe -m ruff check --config backend/pyproject.toml backend scripts
.\ocean-env\Scripts\python.exe -m ruff format --check --config backend/pyproject.toml backend scripts
~~~

From the frontend directory:

~~~powershell
npm.cmd run typecheck
npm.cmd run lint
npm.cmd run build
# Requires both local servers, prepared data and Microsoft Edge:
npx.cmd playwright test --config playwright.live.config.ts
~~~

### Recorded local verification

- **Frontend:** 16 live checks passed on September 28, 2026, including delayed batch responses, stable desktop/mobile timeline layout, transition state, reduced motion, graph layout and PNG export.
- **Archive:** all 480 source dates checked through 960 preview-frame requests, with 960 preview-point and 960 native-point comparisons against the original SST/SSS source.
- **Backend:** the recorded archive regression run passed 1,026 tests with four Windows symlink skips; an additional catalogue-boundary test passed separately.

These are dated local results, not live CI badges, full-grid scientific validation or deployment performance guarantees. Warnings, test scope and earlier attempts are preserved in the [archive record](docs/BIO_ROMS_ARCHIVE.md) and [frontend verification notes](docs/FRONTEND_INTEGRATION.md).

## Current limitations and roadmap

- **Surface first:** the current BIO-ROMS file has no vertical dimension. Depth slices, ocean volumes and current-vector serving are not enabled by this surface product.
- **Bounded analysis:** time-series plots cover the selected prepared batch; full-history analysis is future work.
- **Exploratory comparison:** the saved result contains two matched pairs from 14 evaluated Argo samples. It is assumption-labelled, not independent model validation; changing Explorer selections does not recompute it.
- **Source-specific readiness:** usable glider layers, broader Copernicus/GODAS coverage and identified vertical profiles require further supported processing and verification.
- **Deployment:** hosting, multi-user load testing and production hardening remain future work. Local functional tests do not establish an FPS or latency guarantee.
- **Extensibility:** CTD, BGC observations, moorings, HF radar and ADCP remain planned extensions.

## Documentation

| Document | Read it for |
| --- | --- |
| [Project context](PROJECT_CONTEXT.md) | Carried-over requirements and current decisions |
| [Architecture](ARCHITECTURE.md) | Components, data flow, boundaries and scientific rationale |
| [File structure](FILE_STRUCTURE.md) | Where implementation belongs |
| [Conventions](CONVENTIONS.md) | Coding, scientific and verification rules |
| [API routes](docs/API_ROUTES.md) | Implemented routes, parameters, errors and examples |
| [Frontend integration](docs/FRONTEND_INTEGRATION.md) | Running the UI, recovery provenance and browser verification |
| [BIO-ROMS archive](docs/BIO_ROMS_ARCHIVE.md) | All-date preparation and source-value verification |
| [Matching policy](docs/MATCHING_POLICY.md) | Comparison assumptions, eligibility and unresolved scientific gates |
| [Performance](docs/performance.md) | Resource bounds and measured results with scope |
| [Development plan](BACKEND_DEVELOPMENT_PLAN.md) | Ordered milestones and historical progress |

For contributors and coding agents, read this file, Project Context, Architecture, File Structure, Conventions and applicable AGENTS.md instructions before editing. Use the latest dated implementation records; older milestone statements are historical, not instructions to repeat completed work.

## Attribution and licensing

Preserve dataset provenance, provider terms and Cesium/basemap credits. Access to a dataset does not imply unrestricted redistribution. No project-level LICENSE file is currently present; choose and review an appropriate code license before describing this repository as open source. Dataset and third-party software licences remain separate.
