# Experimentation & Causal Inference Platform — Frontend

A React 18 + Vite single-page application for designing experiments, analysing A/B
tests correctly, and estimating causal effects when randomised experiments are not
possible. It talks to the FastAPI backend that lives in the repository root
(`src/api`).

## Features

- **Power Calculator** — required sample size per arm/total for proportions and
  continuous metrics, plus a client-side "what-if" curve of required sample size vs.
  effect size.
- **A/B Analysis** — simulate, load a bundled dataset or upload a CSV; run a
  frequentist, Bayesian or sequential (peek-safe) analysis with charts.
- **Multiple Testing** — Bonferroni and Benjamini–Hochberg corrections for a batch of
  p-values, with a comparison chart and an alpha reference line.
- **Causal Inference** — propensity-score matching, difference-in-differences,
  synthetic control and uplift (CATE) with method-specific charts.

Every result is accompanied by a plain-English conclusion callout (green = win,
amber = inconclusive, red = negative / no effect).

## Requirements

- Node.js 18+ (tested on Node 23) and npm.
- The backend API running on `http://localhost:8000`.

## Getting started

```bash
# 1. Install dependencies
npm install

# 2. Start the backend (from the repository root, in a separate terminal)
#    e.g. uvicorn src.api.main:app --reload --port 8000

# 3. Start the dev server
npm run dev
```

Open the printed URL (default <http://localhost:5173>). The dev server proxies all
requests to `/api` onto `http://localhost:8000`, so no CORS configuration is needed.

## Production build

```bash
npm run build     # outputs static assets into ./dist
npm run preview   # serve the production build locally (proxies /api as well)
```

## Project structure

```
frontend/
  index.html
  vite.config.js
  package.json
  src/
    main.jsx                 # React entry point
    App.jsx                  # layout + tab routing
    styles.css               # global styles (indigo / slate palette)
    api/client.js            # fetch wrapper around the /api endpoints
    lib/format.js            # number / p-value formatting helpers
    components/              # Sidebar, Header, StatCard, ... , charts
    pages/                   # PowerCalculator, ABAnalysis, MultipleTesting, CausalInference
```
