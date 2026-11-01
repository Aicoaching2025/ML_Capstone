# Research decisions

| Date | Decision | Rationale | Holdout errors viewed |
| --- | --- | --- | --- |
| 2026-11-01 | Horizon measured to target interval end | Makes issuance and target boundaries explicit | No |
| 2026-11-01 | Python 3.12 with uv.lock; local-first portable setup | Stable local baseline independent of managed runtime | No |
| 2026-11-01 | Use a synthetic fixture for platform smoke tests | Verify infrastructure without implying real-data validation | No |
| 2026-11-01 | Do not select a forecast provider or assume publication delays yet | Requires source pilot | No |
| 2026-11-01 | Databricks smoke test uses managed volume and dedicated setup table | Avoid legacy DBFS assumptions and isolate test objects | No |

Record subsequent changes, rationale, affected experiments, and whether final-holdout performance was viewed.
