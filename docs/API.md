# API Documentation

Base URL (development): `http://localhost:8000`
All routes are mounted under the `/api` prefix. Interactive OpenAPI docs are served at
`/docs` and the raw schema at `/openapi.json`.

Every analysis response has the shape:

```json
{
  "result":     { "...": "machine-readable statistics" },
  "conclusion": { "headline": "...", "details": "...", "recommendation": "..." }
}
```

Errors return `400` (bad input / analysis error) or `404` (unknown dataset) with
`{ "detail": "..." }`.

---

## Shared objects

### `DataSource`

Describes where the analysis data comes from.

| Field | Type | Default | Notes |
|---|---|---|---|
| `source` | `"inline" \| "simulate" \| "dataset" \| "upload"` | `"simulate"` | |
| `records` | array of objects | `null` | required when `source = "inline"` |
| `name` | string | `null` | dataset key, required when `source = "dataset"` |
| `upload_id` | string | `null` | required when `source = "upload"` |
| `simulate` | `SimulateSpec` | `null` | used when `source = "simulate"` |

### `SimulateSpec`

| Field | Type | Default |
|---|---|---|
| `kind` | `"continuous" \| "binary" \| "multimetric" \| "sequential" \| "observational"` | `"binary"` |
| `n_a`, `n_b` | int | `5000` |
| `p_a` | float | `0.10` |
| `relative_lift` | float | `0.10` |
| `mean_a` | float | `10.0` |
| `std` | float | `5.0` |
| `seed` | int | `42` |

---

## Meta

### `GET /`
Returns service name, version, docs path and the list of endpoints.

### `GET /api/health`
```json
{ "status": "ok" }
```

---

## Power & sample size (Milestone 2)

### `POST /api/power/sample-size`
Required sample size per arm for a target power.

| Field | Type | Default |
|---|---|---|
| `metric_type` | `"proportion" \| "continuous"` | `"proportion"` |
| `p_control` | float | `0.10` |
| `p_treatment` | float \| null | `null` |
| `relative_lift` | float \| null | `0.10` |
| `cohens_d` | float | `0.2` |
| `alpha` | float | `0.05` |
| `power` | float | `0.80` |
| `ratio` | float | `1.0` |

```bash
curl -X POST http://localhost:8000/api/power/sample-size \
  -H "Content-Type: application/json" \
  -d '{"metric_type":"proportion","p_control":0.10,"relative_lift":0.10}'
```
```json
{ "method": "two_proportions", "p_control": 0.1, "p_treatment": 0.11,
  "cohens_h": 0.032, "alpha": 0.05, "power": 0.8,
  "n_control": 14748, "n_treatment": 14748, "n_total": 29496 }
```

### `POST /api/power/power`
Statistical power for given sample sizes. Fields: `metric_type`, `p_control`,
`p_treatment`, `n_control`, `n_treatment`, `cohens_d`, `alpha`.

### `POST /api/power/mde`
Minimum detectable effect for a fixed n. Fields: `metric_type`, `p_control`,
`n_control`, `n_treatment`, `alpha`, `power`.

---

## Experiment analysis

### `POST /api/analysis/frequentist` (Milestone 3)
Welch t-test (continuous) or two-proportion z-test (binary).

| Field | Type | Default |
|---|---|---|
| `metric_type` | `"proportion" \| "continuous"` | `"continuous"` |
| `data` | `DataSource` | `{source:"simulate"}` |
| `variant_column` | string | `"variant"` |
| `metric_column` | string | `"converted"` |
| `control_label` / `treatment_label` | string | `"A"` / `"B"` |
| `alpha` | float | `0.05` |

Response adds `distribution` (a histogram or bar payload for charting) alongside
`result` and `conclusion`. `result` includes `p_value`, `absolute_lift`,
`relative_lift`, `ci_lower`, `ci_upper`, `t_stat`/`z_stat`, `cohens_d`/`cohens_h`,
`significant`.

### `POST /api/analysis/multiple-testing` (Milestone 3)

| Field | Type | Default |
|---|---|---|
| `pvalues` | list of float | required |
| `metric_names` | list of string \| null | `null` |
| `methods` | list of string | `["bonferroni","benjamini-hochberg"]` |
| `alpha` | float | `0.05` |

```bash
curl -X POST http://localhost:8000/api/analysis/multiple-testing \
  -H "Content-Type: application/json" -d '{"pvalues":[0.001,0.02,0.03,0.2]}'
```
Response: `{ metric_names, pvalues, n_tests, alpha, by_method: { <method>: {
pvalues, adjusted_pvalues, reject, alpha } } }`.

### `POST /api/analysis/sequential` (Milestone 4)
Peek-safe monitoring. Fields: `metric_type`, `data`, `variant_column`,
`metric_column`, `control_label`, `treatment_label`, `n_looks` (default 5),
`spending` (`"obrien-fleming"` | `"pocock"`), `alpha`.

`result` contains `looks` (per-look `naive_p_value`, `always_valid_p_value`,
`nominal_p_boundary`, `z_boundary`, `crosses_boundary`) and `final_decision`.

### `POST /api/analysis/bayesian` (Milestone 5)
Bayesian A/B. Fields: `metric_type`, `data`, `variant_column`, `metric_column`,
`control_label`, `treatment_label`, `draws` (default 3000), `seed`.

`result` includes `prob_treatment_better` (P(B beats A)), `credible_interval`,
`expected_loss_if_ship_treatment`, `decision`, `engine` and
`posterior_histogram`.

---

## Causal inference (Milestone 6)

### `POST /api/causal/propensity`
Propensity-score matching.

| Field | Default |
|---|---|
| `treatment_column` | `"treatment"` |
| `outcome_column` | `"outcome"` |
| `covariates` | `["age","prior_spend"]` |
| `caliper` | `0.1` |
| `use_dowhy` | `false` |
| `alpha` | `0.05` |

`result`: `effect`/`ate`, `ci`, `naive_estimate`, `confounding_bias`,
`balance_smd_before`, `balance_smd_after`, `max_smd_after`, `balanced`.

### `POST /api/causal/did`
Difference-in-differences. Fields: `outcome_column` (`"fte_employment"`),
`treated_column` (`"treated"`), `post_column` (`"post"`), `covariates`, `alpha`.

`result`: `att`/`effect`, `ci`, `p_value`, `std_err`, `naive_estimate`,
`cell_means`, `r_squared`.

```bash
curl -X POST http://localhost:8000/api/causal/did \
  -H "Content-Type: application/json" \
  -d '{"data":{"source":"dataset","name":"card_krueger"}}'
```

### `POST /api/causal/synthetic-control`
| Field | Default |
|---|---|
| `unit_column` | `"state"` |
| `time_column` | `"year"` |
| `outcome_column` | `"cigsales"` |
| `treated_unit` | `"California"` |
| `treatment_time` | `1989` |
| `donor_units` | `null` (all others) |

`result`: `effect`/`att`, `pre_period_rmse`, `p_value`, `weights`, `treated`,
`synthetic`, `gap`, `pre_mask`.

### `POST /api/causal/uplift`
Heterogeneous treatment effects / CATE.

| Field | Default |
|---|---|
| `treatment_column` | `"segment"` |
| `outcome_column` | `"visit"` |
| `features` | `["recency","history","mens","womens","newbie"]` |
| `positive_treatment` | `null` (auto) |
| `learner` | `"causal_forest"` (or `"t_learner"`) |
| `n_estimators` | `200` |
| `seed` | `42` |

`result`: `ate`, `cate_mean`, `cate_std`, `cate_positive_share`,
`feature_importance`, `qini` (`fraction`, `qini`, `random_baseline`), `auuc`,
`qini_at_10pct`, `qini_at_30pct`, `engine`.

---

## Datasets

### `GET /api/datasets`
```json
{ "datasets": [
  { "name": "cookie_cats", "description": "...", "analysis": "binary" },
  { "name": "hillstrom",  "description": "...", "analysis": "uplift" },
  { "name": "lalonde",    "description": "...", "analysis": "propensity" },
  { "name": "card_krueger","description": "...", "analysis": "did" },
  { "name": "prop99",     "description": "...", "analysis": "synthetic_control" },
  { "name": "ihdp",       "description": "...", "analysis": "uplift" }
] }
```

### `GET /api/datasets/{name}?limit=2000`
Load a bundled dataset and return `{ name, columns, dtypes, n_rows, preview }`.

### `POST /api/datasets/simulate`
Body is a `DataSource` with `source = "simulate"`; returns a preview of the generated
frame.

### `POST /api/datasets/upload`
`multipart/form-data` with a `file` field (CSV). Returns
`{ upload_id, filename, columns, dtypes, n_rows, preview }`. Use the `upload_id` as
`{"source":"upload","upload_id":"..."}` in any analysis endpoint.
