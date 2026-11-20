# Architecture & Data Documentation

This document describes how the Experimentation & Causal Inference Platform is put
together, how a request flows through it, and the data it uses.

---

## 1. Layers

The project is a classic three-tier design with a stateless statistical engine in the
middle so the same code powers the API, the notebooks and the tests.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ PRESENTATION                                                                  │
│   React 18 SPA (Vite + Recharts)                                              │
│   pages: PowerCalculator · ABAnalysis · MultipleTesting · CausalInference     │
│   components: Sidebar · Header · StatCard · charts · Loading                  │
│   lib/format.js (number / p-value formatting), api/client.js (fetch wrapper)  │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │  HTTP  (JSON / multipart CSV)
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ SERVICE  — FastAPI                                                           │
│   main.py            app, lifespan, CORS, router mounting                    │
│   schemas.py         Pydantic v2 request/response models                     │
│   dependencies.py    resolve_dataframe · save_upload · split_arms ·          │
│                      binarize_treatment · datasets registry                  │
│   routers/                                                                   │
│     power.py         /api/power/{sample-size,power,mde}                      │
│     experiment.py    /api/analysis/{frequentist,multiple-testing,            │
│                                     sequential,bayesian}                     │
│     causal.py        /api/causal/{propensity,did,synthetic-control,uplift}   │
│     datasets.py      /api/datasets[...]                                      │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │  pure function calls
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ CORE (statistics + causal inference)                                         │
│   power.py            NormalIndPower / TTestIndPower (statsmodels)           │
│   frequentist.py      Welch t-test (scipy), two-proportion z (statsmodels),  │
│                       chi-square (scipy)                                     │
│   multiple_testing.py multipletests: Bonferroni, BH/FDR, Holm, Šidák         │
│   sequential.py       Lan-DeMets alpha spending, canonical joint MVN         │
│                       boundaries, mSPRT always-valid p-values                │
│   bayesian.py         PyMC Beta-Binomial / Normal; conjugate fallback        │
│   conclude.py         plain-English headline/details/recommendation          │
│   causal/                                                                     │
│     propensity.py     logistic PS + 1:1 NN matching, SMD balance, DoWhy      │
│     did.py            OLS  y ~ treated + post + treated:post  (HC1)          │
│     synthetic_control.py  SLSQP weights (Σ=1, ≥0) + placebo test             │
│     uplift.py         EconML CausalForestDML / T-learner, Qini + AUUC        │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │  kernels: numpy · scipy · statsmodels ·
                                │           scikit-learn · pymc · dowhy · econml
┌───────────────────────────────▼──────────────────────────────────────────────┐
│ DATA PIPELINE                                                                 │
│   datasets.py   load_cookie_cats · load_hillstrom · load_lalonde ·           │
│                 load_card_krueger · load_prop99 · load_ihdp                  │
│                 (real download → cache to data/raw → simulated fallback)     │
│   simulate.py   continuous · binary · multimetric · sequential ·             │
│                 confounded-observational                                     │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Why a stateless core?

`src/core` contains only pure functions (`dict` in, `dict` out). This means:

* the API, the notebooks and the tests exercise the **exact same code**;
* results are reproducible (every stochastic routine takes a `seed`);
* the engine is trivially unit-testable — see `tests/`.

---

## 2. Request lifecycle

Example: a user uploads a CSV and runs a Bayesian A/B analysis from the SPA.

```
1. SPA  →  POST /api/datasets/upload (multipart)
           dependencies.save_upload()  →  data/processed/uploads/<id>.csv
           returns { upload_id, columns, preview }

2. SPA  →  POST /api/analysis/bayesian
           { "data": { "source": "upload", "upload_id": "..." },
             "variant_column": "variant", "metric_column": "converted" }

3. Router  resolve_dataframe()  → pd.read_csv(<upload path>)
           split_arms()         → (control[], treatment[], is_binary)
           core.bayesian.bayesian_ab_binary(...)  → PyMC Beta-Binomial model
           core.conclude.bayesian_conclusion(...) → plain-English text

4. Response { result: {...}, conclusion: {...} }  →  SPA renders cards + charts
```

Data sources are uniform — the same endpoints accept:

| `source` | Meaning |
|---|---|
| `simulate` | generate deterministic synthetic data from a `SimulateSpec` |
| `dataset` | load one of the bundled datasets by `name` |
| `upload` | a CSV previously stored via `/api/datasets/upload` |
| `inline` | a list of records sent in the JSON body |

---

## 3. Path handling

A hard requirement of the project is **cross-platform path handling**. Everything is
built with `os.path.join` from a `PROJECT_ROOT` resolved relative to `src/config.py`:

```python
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
```

`src.config` exposes `data_path()`, `raw_path()`, `processed_path()`, `simulated_path()`
and `artifact_path()` helpers plus `ensure_directories()`. The notebooks bootstrap by
walking up from the current directory until they find `src/config.py`, so they can be run
from `notebooks/`, from the repo root, or from an IDE.

---

## 4. Statistical methods

| Area | Method | Implementation notes |
|---|---|---|
| Power | Sample size / power / MDE | `statsmodels` `NormalIndPower` (proportions, Cohen's *h*), `TTestIndPower` (continuous, Cohen's *d*) |
| Frequentist | Welch t-test | `scipy.stats.ttest_ind(equal_var=False)` + Welch–Satterthwaite df + Cohen's *d* |
| Frequentist | Two-proportion z-test | `statsmodels.stats.proportion.proportions_ztest` + Wald CI + Cohen's *h* |
| Frequentist | Chi-square | `scipy.stats.chi2_contingency` + Cramér's V |
| Multiplicity | Bonferroni, BH, Holm, Šidák | `statsmodels.stats.multitest.multipletests` |
| Sequential | Group-sequential boundaries | Lan-DeMets α-spending (O'Brien-Fleming, Pocock); crossing probabilities from the canonical joint MVN with `corr_ij = √(t_i/t_j)` |
| Sequential | Always-valid p-values | mSPRT with a Gaussian mixture prior (continuous & binary) |
| Bayesian | Binary metric | Beta-Binomial — PyMC MCMC, exact conjugate fallback |
| Bayesian | Continuous metric | Normal-Normal — PyMC MCMC, normal-approximation fallback |
| Causal | Propensity matching | logit-PS logistic regression + 1:1 nearest neighbour, caliper, bootstrap CI, SMD balance; DoWhy cross-check + refutation |
| Causal | Difference-in-differences | OLS `y ~ treated + post + treated:post` with HC1 robust SE; ATT = interaction |
| Causal | Synthetic control | SLSQP weights (non-negative, sum to 1), pre-period RMSE, placebo permutation p-value |
| Causal | Uplift / CATE | EconML `CausalForestDML` (DML debiasing); T-learner fallback; Qini curve + AUUC |

---

## 5. Datasets

| Key | Source | Rows (typical) | Key columns | Analysis |
|---|---|---|---|---|
| `cookie_cats` | kagglehub `yufengsui/mobile-games-ab-testing` | ~90k | `version`, `retention_1`, `retention_7`, `sum_gamerounds` | binary A/B |
| `hillstrom` | MineThatData public CSV | ~64k | `segment`, `visit`, `conversion`, `spend`, `history` | uplift |
| `lalonde` | `causaldata` / `dowhy.datasets` | ~700 | `treat`, `re78`, `age`, `education` | propensity |
| `card_krueger` | simulated panel (cached) | ~4k | `state`, `year`, `treated`, `post`, `fte_employment` | DiD |
| `prop99` | synthetic panel (cached) | ~1.2k | `state`, `year`, `cigsales` | synthetic control |
| `ihdp` | `causalml` / simulated | ~747 | `x1..x25`, `treatment`, `y_factual` | uplift |

Every loader follows the same resilient pattern:

```
cached copy in data/raw?  ──yes──►  return it
        │ no
        ▼
try real download (kagglehub / URL / bundled)
        │ fail
        ▼
simulated, structurally identical dataset  ──►  cache to data/raw
```

This guarantees the notebooks, tests and demo work with or without network access.

---

## 6. Front end

* **Framework** – React 18 + Vite 5, charts with Recharts.
* **Routing** – lightweight in-app tab state (`App.jsx`); four pages.
* **API access** – `src/api/client.js` wraps `fetch`; the Vite dev server proxies `/api`
  to `http://localhost:8000`.
* **Result rendering** – every page shows numbers in `StatCard`s, a method-specific chart
  and the plain-English `conclusion` callout (green = win, amber = inconclusive,
  red = negative).

```
frontend/src/
  main.jsx          React entry point
  App.jsx           shell + tab routing
  styles.css        global styles
  api/client.js     fetch wrappers for every endpoint
  lib/format.js     number / p-value / percent formatting
  components/       Sidebar, Header, StatCard, Loading, charts
  pages/            PowerCalculator, ABAnalysis, MultipleTesting, CausalInference
```

---

## 7. Testing

`tests/` contains 31 tests:

* `test_power.py` – sample-size / power / MDE math;
* `test_frequentist.py` – t-test, z-test, chi-square on known inputs;
* `test_multiple_testing.py` – Bonferroni & BH behaviour;
* `test_sequential.py` – boundaries preserve α, always-valid p-values;
* `test_bayesian.py` – posterior direction and decision thresholds;
* `test_causal.py` – PSM reduces confounding bias, DiD recovers a known effect,
  synthetic control detects a negative effect, uplift runs end-to-end;
* `test_api.py` – every FastAPI endpoint via the `TestClient`.

Run with `pytest -q`.
