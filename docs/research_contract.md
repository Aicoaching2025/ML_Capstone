# Research contract

Comparative machine learning for hour-ahead and 24-hour-ahead electricity demand forecasting in New York City

**Researcher:** Candace Grant  
**Course:** DATA 698, Fall 2026  
**Contract version:** 0.1  
**Created:** November 1, 2026  
**Status:** Initial research specification; source-dependent availability assumptions must pass the data audit before experiments are frozen.

## Purpose and scope

This study compares forecasts of NYISO Load Zone J electricity demand using load history, calendar information, and weather. It evaluates whether machine-learning models improve on simple and statistical baselines at two fixed horizons, and whether their performance changes during peak demand and extreme temperatures.

The core contribution is a reproducible comparison under explicit information-availability constraints. A finding that a complex model does not outperform a baseline is a valid research result. Statistical significance or a particular winning model is not a completion requirement.

The core project includes seasonal-naïve baselines, SARIMAX, Random Forest, XGBoost, chronological validation, feature ablations, and extreme-event evaluation. An LSTM is optional and must not delay the core deliverables. No production serving system or operational cost optimization is required.

## Research questions and hypotheses

| ID | Question or hypothesis |
| --- | --- |
| RQ1 | How accurately do the models forecast Zone J hourly load 1 hour and 24 hours ahead relative to naïve and statistical baselines? |
| RQ2 | How much do calendar and weather features improve on load-history features, and how does the improvement differ by horizon? |
| RQ3 | How does model performance change during high-demand hours, extreme heat, and extreme cold? |
| H1 | Models using load, calendar, and available weather information reduce MAE and RMSE relative to seasonal-naïve and SARIMAX baselines at both horizons. |
| H2 | The incremental value of weather is greater at 24 hours than at 1 hour. |
| H3 | Forecast errors rise during extreme conditions, but weather-informed models degrade less than load-only models. |

Hypotheses will be assessed rather than assumed. H2 will be evaluated using comparable relative improvements within each horizon and a matched weather-coverage period. H3 will distinguish absolute extreme-period errors from degradation relative to ordinary periods.

## Target and study population

- **Geography:** NYISO Load Zone J, representing the New York City load zone.
- **Target product:** NYISO hourly integrated real-time actual load for Zone J.
- **Target units:** MW, using the source product's hourly load definition. This is not a forecast of hourly energy in MWh.
- **Historical period:** January 1, 2018 through December 31, 2025, interpreted as NYC local calendar dates, then represented in UTC.
- **Sampling unit:** One Zone J hourly target interval for one forecast origin and horizon.
- **Primary task:** Point forecasting of the load value associated with that interval.

The acquisition audit must verify the report identity, zone identifier, units, and interval-label convention. Five-minute actual load must not silently replace the hourly integrated product. Any substitution requires a documented amendment and aggregation rule.

## Exact meaning of the forecast horizons

### Canonical interval convention

All modeling records use explicit interval starts and ends in UTC. Intervals are half-open: `[start, end)`. The end belongs to the following interval.

Let:

- `O` be the forecast origin: the instant at which a prediction is issued, on an exact UTC hour boundary.
- `h` be the forecast horizon in elapsed hours, either 1 or 24.
- `E = O + h hours` be the target interval end.
- `S = E − 1 hour` be the target interval start.
- `y[S,E)` be the hourly integrated load value for that target interval.

The prediction is `ŷ_h(O)` for `y[O + (h−1) hours, O + h hours)`.

**In this study, the numerical horizon is measured from the forecast origin to the end of the target interval.** It is not measured to the start or midpoint of the interval. This convention must accompany reported results so the phrase “24 hours ahead” is unambiguous.

Source timestamps may label interval starts or ends. They will be mapped to these canonical boundaries only after inspecting source documentation and sample records. Renaming a source timestamp does not establish its meaning.

### One hour ahead

At origin `O`, the model predicts load for the immediately upcoming hourly interval `[O, O + 1 hour)`.

For example, a prediction issued at `2024-07-15 14:00 UTC` targets the interval from `14:00` through just before `15:00 UTC`. Its target end is `15:00 UTC`, exactly one elapsed hour after issuance.

Only information available at or before `14:00 UTC` may enter that prediction. Observations collected during the target interval are unavailable at issuance and cannot be predictors.

### Twenty four hours ahead

At origin `O`, the model predicts one hourly load value for `[O + 23 hours, O + 24 hours)`.

For example, a prediction issued at `2024-07-15 14:00 UTC` targets the interval from `2024-07-16 13:00` through just before `14:00 UTC`. Its target end is exactly 24 elapsed hours after issuance.

This is a single-target, rolling 24-hour forecast. It does not predict the average load over the next 24 hours, and it does not produce tomorrow's complete 24-hour load profile in one issuance.

### Examples side by side

| Origin UTC | Horizon | Target start UTC | Target end UTC |
| --- | --- | --- | --- |
| 2024-07-15 14:00 | 1 hour | 2024-07-15 14:00 | 2024-07-15 15:00 |
| 2024-07-15 14:00 | 24 hours | 2024-07-16 13:00 | 2024-07-16 14:00 |
| 2024-07-15 15:00 | 1 hour | 2024-07-15 15:00 | 2024-07-15 16:00 |
| 2024-07-15 15:00 | 24 hours | 2024-07-16 14:00 | 2024-07-16 15:00 |

A separate direct model is fitted for each horizon and feature set. The 24-hour prediction does not recursively consume 23 intervening model predictions.

### Rolling forecasts and daylight saving time

Forecast origins advance by one elapsed UTC hour. The 24-hour horizon always means 24 elapsed hours, including across daylight-saving transitions. It may therefore differ from “the same local clock hour tomorrow.”

UTC defines chronology and joins. `America/New_York` defines interpretable local calendar features. Repeated fall-back hours retain distinct UTC timestamps; nonexistent spring-forward local hours are not fabricated.

Operational day-ahead forecasting at a fixed daily cutoff is outside the primary scope. It would require multiple target hours with different lead times and a separately specified evaluation protocol.

## Information available at the forecast origin

A feature is eligible only if its information was available at or before `O`. Event time, availability time, and retrieval time are distinct:

| Time | Meaning |
| --- | --- |
| Event or valid time | When a measurement applies or a forecast is valid |
| Initialization time | When a weather-model run is initialized |
| Availability time | When an input could reasonably have been accessed |
| Retrieval time | When this project downloaded the record |

A historical download date does not prove historical availability. A model initialization timestamp does not prove immediate public release.

### Load history

Let `A(O)` be the latest completed load interval end whose value satisfies the load-availability rule at origin `O`. All load-history features must end at or before `A(O)`.

The source audit will determine a documented publication-delay rule. Until then, no claim is made that the load interval ending exactly at `O` is usable at `O`. If historical publication timestamps are unavailable, the study will use a conservative fixed delay, justify it, and report a sensitivity analysis where feasible.

Load features will be named relative to the origin or latest available interval. Target-relative lag names must include a definition. A target-relative lag of 24 hours is not automatically eligible merely because the prediction horizon is 24 hours.

Rolling statistics use only eligible past observations. They must not extend from the origin toward the target. Centered rolling windows, backward filling from future observations, and interpolation using unavailable future values are prohibited for predictive inputs.

Final revised load may be used as the evaluation target. If predictor history also uses revised values because historical vintages cannot be recovered, that limitation must be disclosed. Publication-delay controls do not eliminate revision-related hindsight.

### Calendar information

Target-interval local hour, weekday, month, holiday status, and deterministic cyclic encodings are known in advance and are eligible at both horizons. Target calendar features use the target interval start in NYC local time. Any alternative convention requires documentation.

Holiday definitions, observed-holiday treatment, and package versions will be recorded. Transformations learned from data must be fitted within training folds.

### Observed weather

Observed weather may enter operational models only when its observation and availability times are no later than `O`. Recent observed weather can support both horizons, subject to reporting delay.

Weather observed during the future target interval is unavailable at `O`. It may appear only in the explicitly labeled retrospective observed-weather experiment or in retrospective evaluation labels.

### Forecast weather

Operational future-weather features must come from archived issued forecasts selected under a frozen rule:

1. Identify the target interval and the weather values needed to represent it.
2. Select only runs whose availability time is no later than `O`.
3. Choose the latest eligible run under the documented provider/model rule.
4. Extract weather valid for the target interval using a documented hourly alignment or aggregation rule.
5. Preserve the initialization time, valid time, lead time, model, location, and availability basis.

If release timestamps are unavailable, use a justified conservative release delay and label availability as assumed. Forecast lead time is measured from initialization to valid time; it can exceed the load-forecast horizon because the eligible weather run may be older than the origin.

An archive containing stitched near-current forecasts, observations, or reanalysis does not automatically qualify as a historical issued-forecast archive. Fixed-lead API products require verification of their timing semantics before operational claims are made.

## Data sources and experiment periods

| Component | Planned source | Audit requirements |
| --- | --- | --- |
| Hourly load | NYISO integrated real-time actual load, Zone J | Product identity, timestamps, units, revisions, coverage |
| Observed weather | NOAA NCEI LCD v2; Central Park primary candidate, LaGuardia/JFK alternatives | Station metadata, time convention, quality flags, variable coverage |
| Forecast weather | Provider and operational model selected after archive pilot | Vintage semantics, release delay, lead coverage, variables, licensing |
| Calendar | Deterministic NYC calendar and documented US holidays | Timezone, holiday definitions, reproducible version |
| Optional benchmark | Archived NYISO published load forecasts | Zone, target definition, issue time, historical vintage availability |

Two experiment periods are permitted:

- **Long-history experiment:** 2018–2025 load and observed weather, subject to audited exclusions. Future observed weather is labeled retrospective.
- **Operational-weather experiment:** The audited overlap containing eligible archived forecasts. Its dates are frozen before comparative model evaluation.

Weather ablations must compare models on the same period and eligible timestamps. A model with eight years of evaluation cannot be directly compared with one evaluated on a shorter weather archive to attribute the difference to weather.

If no archive supports a defensible operational experiment, the project will retain operational load/calendar forecasts and report future observed weather as a separate sensitivity analysis. Observed-weather results are an ideal-information reference, not a guaranteed mathematical upper bound on achievable accuracy.

## Data processing and quality rules

- Preserve source files immutably in Bronze, with retrieval timestamps and SHA-256 hashes.
- Store cleaned, typed, timezone-resolved records in Silver.
- Build horizon-specific forecast examples in Gold during the modeling bucket.
- Preserve original timestamps, quality flags, units, and station identities.
- Test uniqueness using source-appropriate keys and canonical UTC intervals.
- Investigate extreme values rather than deleting them solely because they are rare.
- Do not impute missing targets for scored evaluation.
- Define predictive missing-value handling using training information and causal availability rules.
- Document station substitutions; do not treat airport and Central Park measurements as interchangeable.
- Log exclusions with reasons and counts, including their impact on extreme-event coverage.
- Preserve enough pre-period history for lag warm-up where available; otherwise exclude warm-up examples explicitly.
- Derive heating/cooling degree-hours using a documented reference temperature. The initial reference is 18.3°C; any data-driven change must use training data only.

## Models and controlled feature ablations

Core baselines are persistence, previous-day seasonal naïve, previous-week seasonal naïve, and SARIMAX with manageable temporal structure and Fourier regressors. Any weather regressors in SARIMAX follow the same availability rules as ML inputs.

For each horizon, Random Forest and XGBoost use:

| Feature set | Contents |
| --- | --- |
| A | Eligible load history only |
| B | A plus target calendar information |
| C operational | B plus eligible observed history and archived forecast weather |
| C retrospective | B plus explicitly identified future observed weather |

Persistence uses the latest available load observation. Daily and weekly naïve baselines use the target interval shifted by 24 and 168 elapsed hours, respectively, only when the source value is available at the origin. If a baseline value is unavailable, its prescribed missing/fallback rule must be frozen and reported. A same-local-clock-hour baseline may be evaluated separately because DST makes it different from a fixed elapsed-hour shift.

Feature candidates include recent load values, daily/weekly lags, trailing 3/24/168-hour summaries, calendar encodings, temperature, dew point, humidity, and degree-hours. Exact feature definitions and search budgets are frozen using development data. LSTM work starts only after core models and backtests are complete.

## Chronological validation and final holdout

- No random train/test split is permitted.
- The planned development design uses initial training on 2018–2020 and expanding-window validation over 2021–2024.
- Operational-weather experiments may start later, based on audited coverage. Their training and validation schedule must be documented separately before tuning.
- Hyperparameters, transformations, imputation, feature selection, and thresholds are selected within training/development periods.
- At any fitting cutoff, training labels must already be available under the declared training policy. Rows with future targets are excluded even if their origins precede the cutoff.
- Retraining frequency and evaluation cadence must be frozen before the final run.
- Calendar year 2025 is the final performance holdout. Coverage/schema auditing is permitted, but its forecasting errors must not guide model selection.
- Scheduled updates during 2025 are permitted only under a predeclared procedure that uses information available at each update and makes no performance-driven changes to the research design.
- Final comparisons use paired predictions on identical eligible target intervals. Coverage and exclusions are reported alongside accuracy.
- If final-test results prompt a substantive change, the original results remain reported and the revised result is labeled exploratory.

## Metrics and statistical comparisons

Primary metrics are MAE and RMSE in MW, reported separately by horizon and evaluation subset. Secondary metrics include MASE, MAPE, and percentage improvement over a clearly named baseline.

MASE uses a seasonal scaling denominator calculated from training data only, with the seasonal period and pooling rule recorded. MAPE is descriptive, requires strictly positive valid targets, and is not the basis for selecting the primary model. Its tendency to weight lower-load hours more heavily will be acknowledged.

Percentage improvement for an error metric is `100 × (baseline_error − model_error) / baseline_error`, provided baseline error is nonzero. Negative values indicate worse performance.

The primary planned comparison is operational-weather XGBoost against the weekly seasonal-naïve baseline, separately at each horizon. If operational weather is infeasible, a documented amendment will identify the primary eligible feature set before final evaluation.

Paired forecast errors support Diebold–Mariano comparisons with dependence-aware variance estimation and an appropriate small-sample correction where applicable. Block-bootstrap confidence intervals preserve temporal dependence. Exact loss functions, variance settings, block lengths, and multiplicity treatment are specified before final evaluation. Sparse extreme subsets require event-aware inference; ordinary consecutive-hour assumptions must not be applied blindly to filtered observations.

## Peak and extreme-weather evaluation

All event definitions are frozen before final evaluation. Observed weather and realized load may label retrospective evaluation subsets, but those labels are not predictive inputs unless independently available at the origin.

| Subset | Prespecified definition |
| --- | --- |
| Summer | June, July, August in NYC local time |
| Winter | December, January, February in NYC local time |
| Primary extreme heat | Summer hourly temperature strictly above the training-summer 95th percentile |
| Primary extreme cold | Winter hourly temperature strictly below the training-winter 5th percentile |
| Secondary heat days | Local days whose observed daily maximum is at least 90°F; score eligible target hours on those days |
| Realized peak load | Top 5% of valid target load values in the evaluation period; retrospective descriptive subset |
| Fixed-threshold high load | Target load strictly above the training-period 95th percentile |

Thresholds use the declared event station and fold-specific training data. The final holdout uses thresholds frozen from pre-2025 training data. Quantile method, boundary handling, and ties must be recorded. Missing event-weather labels are excluded from the affected subset and counted.

Report subset thresholds, scored hours, local days, and distinct events. For event counts, contiguous qualifying hourly intervals form one event unless another rule is frozen before evaluation. Compare extremes with the corresponding non-extreme seasonal hours as well as the overall sample. Summer ramp analysis is secondary and requires its own predeclared hour/ramp definition.

## Robustness and interpretation

Report sensitivity to the pandemic period, distinguishing removal of 2020 from training from any descriptive reporting by year. Do not describe a 2025-only test as having test results “with and without 2020.”

Where feasible, examine weather-station choice, availability-delay assumptions, and weather-archive gaps. Sensitivity analyses must not silently replace primary results.

SHAP explanations describe fitted model behavior; they do not establish causal effects. Improved forecasting accuracy does not by itself demonstrate reduced operating costs, reserve requirements, or outage risk.

## Reproducibility and platform policy

Use Databricks Free Edition for lakehouse work and MLflow where feasible, with portable Python code that also runs locally. Paid compute is a contingency requiring a separate budget decision, not a prerequisite. No paid purchase is authorized by this contract.

Track source URLs, hashes, dataset versions, code commit, dependency lockfile, managed runtime, random seeds, feature definitions, split boundaries, and prediction artifacts. Git contains code, configuration, documentation, and permitted small fixtures; credentials and large raw datasets remain outside Git.

The repository will document a small demonstration command and a full acquisition/backtest workflow. Record measured runtime and resource needs. Back up code and research artifacts outside the free workspace. Respect source attribution and redistribution terms.

## Decisions to resolve during Bucket 1

These are explicit audit dependencies, not permission to leave timing ambiguous in final results.

| Decision | Required resolution |
| --- | --- |
| NYISO interval labeling | Confirm source start/end convention and canonical mapping |
| Load availability | Select documented delay and identify revision/vintage limitations |
| Weather observations | Confirm timestamp convention, reporting delay, station choice, hourly selection, and backup rules |
| Forecast archive | Select provider/model, variables, coverage, location extraction, and availability rule |
| Experiment overlap | Freeze operational-weather start/end dates and eligible sample policy |
| Source gaps | Freeze exclusion and causal feature-missingness handling |

The availability rules must be resolved before model tuning. If a source cannot establish exact historical availability, the assumption and resulting limitation must be stated rather than represented as verified fact.

## Completion criteria and change control

Bucket 1 is complete when source pilots and full-period coverage are audited; UTC/DST handling is verified; archived forecast feasibility is decided; availability checks reject future inputs; and the reproducible data build produces documented datasets, manifests, exclusions, and quality results.

The capstone is complete when the core comparisons answer RQ1–RQ3, report uncertainty and extreme-period coverage, preserve final-holdout discipline, and can be reproduced from the documented repository. Beating a baseline is a finding, not a requirement for successful research.

Record amendments in `docs/decisions.md` with date, rationale, affected experiments, and whether final-holdout performance had been viewed. Preserve earlier contract versions in Git. Source feasibility can justify a shorter operational experiment; it cannot justify silently using future observed weather as an operational input.
