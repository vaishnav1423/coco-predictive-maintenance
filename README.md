# Predictive Maintenance on Snowflake

Industrial IoT predictive maintenance system that simulates sensor data from 30 assets across 3 manufacturing plants, loads it into Snowflake, and builds an analytics layer for ML-based failure prediction.

## Architecture

```
data_pdm/ (CSVs)                    PREDICT_MAINT_DB
 |                                   |
 +-- generate_pdm_data.py            +-- RAW (landing zone)
 +-- pdm_docs.py                     |    +-- ASSETS
                                     |    +-- SENSOR_READINGS
   PUT + COPY INTO ------>           |    +-- WORK_ORDERS
                                     |    +-- PRODUCTION_LOG
                                     |    +-- SPARE_PARTS
                                     |    +-- MAINTENANCE_DOCS
                                     |
                                     +-- ANALYTICS (curated layer)
                                          +-- ASSET_SENSOR_STATS    [Dynamic Table]
                                          +-- ASSET_HEALTH_SUMMARY  [Dynamic Table]
                                          +-- PRODUCTION_OEE        [Dynamic Table]
                                          +-- MAINTENANCE_COST_SUMMARY [View]
```

## Snowflake Environment

| Resource | Name |
|---|---|
| Warehouse | `PREDICT_MAINT_WH` (X-Small, auto-suspend 120s) |
| Database | `PREDICT_MAINT_DB` |
| Raw Schema | `PREDICT_MAINT_DB.RAW` |
| Analytics Schema | `PREDICT_MAINT_DB.ANALYTICS` |

## Data Overview

**30 industrial assets** across Pune, Chennai, and Aurangabad plants:

| Asset Type | Count | Key Sensor Channels |
|---|---|---|
| CNC_MACHINE | 6 | Vibration, Temperature, RPM, Motor Current |
| PUMP | 6 | Vibration, Temperature, RPM, Motor Current |
| COMPRESSOR | 5 | Vibration, Temperature, RPM, Motor Current |
| MOTOR | 7 | Vibration, Temperature, RPM, Motor Current |
| CONVEYOR | 6 | Vibration, Temperature, RPM, Motor Current |

**5 failure modes**: BEARING_WEAR, IMBALANCE_MISALIGNMENT, OVERHEATING, LUBRICATION_LOSS, MOTOR_ELECTRICAL

Each mode produces a distinct multi-channel degradation signature over 5-13 days, enabling ML models to detect failures before they occur.

### Raw Tables

| Table | Rows | Description |
|---|---|---|
| `ASSETS` | 30 | Asset master with baseline thresholds per sensor channel |
| `SENSOR_READINGS` | 172,800 | 30-min interval readings over 120 days (Jun-Sep 2026) |
| `WORK_ORDERS` | 181 | 120 preventive + 39 corrective + 22 inspection |
| `PRODUCTION_LOG` | 8,730 | Shift-level production for OEE computation |
| `SPARE_PARTS` | 39 | Parts inventory with stock levels and lead times |
| `MAINTENANCE_DOCS` | 36 | Manuals and SOPs for Cortex Search |

### Analytics Objects

| Object | Type | Key Features |
|---|---|---|
| `ASSET_SENSOR_STATS` | Dynamic Table (incremental) | 36 ML features: rolling means/std at 1h/6h/24h/7d, rate-of-change, baseline deviation %, threshold breach flags and counts |
| `ASSET_HEALTH_SUMMARY` | Dynamic Table (full) | Latest health per asset: overall status (NORMAL/ALERT/ALARM), hours since maintenance, recent corrective WO count |
| `PRODUCTION_OEE` | Dynamic Table (incremental) | OEE = Availability x Performance x Quality per shift, with 7-day rolling average |
| `MAINTENANCE_COST_SUMMARY` | View | Total costs, MTBF, avg repair/wait time, spare parts stock status |

## Project Phases

| Phase | Status | Description |
|---|---|---|
| 1 - Data Loading | **Done** | Warehouse, DB, schemas, 6 tables, CSV loading |
| 2 - Feature Engineering | **Done** | 3 dynamic tables + 1 view in ANALYTICS schema |
| 3 - ML Model | **Done** | Random Forest failure detector (F1=0.64, 80% degradation detection) |
| 4 - Cortex Search & Agent | **Done** | Maintenance doc search + conversational agent |
| 5 - Dashboard & Alerting | **Done** | Streamlit dashboard + 3 Snowflake Alerts |

## SQL Files

All Snowflake SQL is in the `sql/` directory, organized by phase:

### Phase 1 - Data Loading
| File | Description |
|---|---|
| `phase1_setup.sql` | Warehouse, database, schemas, file format, stage |
| `phase1_tables.sql` | All 6 RAW table DDLs |
| `phase1_load.sql` | PUT + COPY INTO for all CSVs with validation |

### Phase 2 - Feature Engineering
| File | Description |
|---|---|
| `phase2_feature_engineering.sql` | ASSET_SENSOR_STATS dynamic table (36 ML features) |
| `phase2_health_summary.sql` | ASSET_HEALTH_SUMMARY dynamic table |
| `phase2_production_oee.sql` | PRODUCTION_OEE dynamic table |
| `phase2_maintenance_cost.sql` | MAINTENANCE_COST_SUMMARY view |
| `phase2_validate.sql` | Validation queries for all Phase 2 objects |

### Phase 3 - ML Model
| File | Description |
|---|---|
| `train_model.py` | Training script: data loading, labeling, RF training, validation |
| `sql/phase3_model_inference.sql` | Batch inference and asset risk scoring SQL |

### Phase 4 - Cortex Search & Agent
| File | Description |
|---|---|
| `sql/phase4_cortex_search.sql` | Cortex Search Service over maintenance docs |
| `sql/phase4_cortex_agent.sql` | Cortex Agent with search tool for technician assistance |

### Phase 5 - Dashboard & Alerting
| File | Description |
|---|---|
| `streamlit_app.py` | 4-page Streamlit dashboard (health, OEE, costs, sensor deep dive) |
| `sql/phase5_alerts.sql` | 3 Snowflake Alerts + ALERT_LOG table |

## Dashboard & Alerting (Phase 5)

**Streamlit Dashboard** (`streamlit_app.py`) — 4 pages:
1. **Asset Health** — KPI cards, color-coded status table, baseline deviation chart
2. **OEE Dashboard** — daily trend, A/P/Q breakdown, by plant and asset type
3. **Maintenance Costs** — corrective vs preventive split, top 10 costliest assets, MTBF
4. **Sensor Deep Dive** — per-asset time-series (vibration, temperature, current) with alert/alarm threshold lines

Run: `uv run streamlit run streamlit_app.py`

**Snowflake Alerts** (every 30 min):
| Alert | Condition |
|---|---|
| `PDM_VIB_ALARM_ALERT` | Any asset vibration exceeds alarm threshold |
| `PDM_TEMP_ALARM_ALERT` | Any asset temperature exceeds alarm threshold |
| `PDM_SUSTAINED_BREACH_ALERT` | Any asset has 10+ threshold breaches in trailing 24h |

All alerts log to `ANALYTICS.ALERT_LOG` for audit.

## Cortex Search & Agent (Phase 4)

**Cortex Search Service**: `PDM_DOCS_SEARCH` — hybrid (vector + keyword) search over 36 maintenance doc sections, with filtering on `DOC_TYPE` and `APPLIES_TO`. Target lag = 1 day.

**Cortex Agent**: `PDM_MAINTENANCE_AGENT` — conversational assistant for plant technicians, powered by `claude-sonnet-4-6`. Searches maintenance manuals (5 failure-mode guides), SOPs (alert triage, work orders), and OEE reference. Cites doc IDs, recommends specific actions, references thresholds, and suggests spare parts.

Example query: *"Vibration on CNC Machine 01 has been rising for 3 days. What should I do?"*
The agent searches relevant docs, performs differential diagnosis (bearing wear vs imbalance), cites MNT-001/MNT-002, and gives step-by-step actions with parts and downtime estimates.

## ML Model (Phase 3)

**Algorithm**: Random Forest Classifier (200 trees, max_depth=15, balanced class weights)

**Features**: 34 numeric features from `ASSET_SENSOR_STATS` including rolling means/std, rate-of-change, baseline deviation %, and threshold breach counts.

**Training approach**: Binary classification using ground truth failure events. Readings within degradation windows (5-13 days before failure) are labeled `1`, all others `0`. Time-based train/test split at Sep 1, 2026.

### Results

| Metric | Value |
|---|---|
| Test F1 (pre-failure class) | 0.64 |
| Test Recall (pre-failure) | 73% |
| Test Precision (pre-failure) | 57% |
| Overall accuracy | 95% |
| Degrading asset detection | 80% (4/5 hidden assets caught) |
| False alarm rejection | 67% (4/6 correctly ignored) |

### Top Features (by importance)
1. `VIB_BASELINE_DEV_PCT` — vibration deviation from baseline (12%)
2. `TEMP_BASELINE_DEV_PCT` — temperature deviation from baseline (8%)
3. `TEMP_AVG_7D` — 7-day rolling temperature average (8%)
4. `VIB_STD_24H` — 24-hour vibration standard deviation (7%)
5. `CURR_AVG_7D` — 7-day rolling motor current average (7%)

### Artifacts
- `model_artifacts/failure_detector.pkl` — serialized model + imputer + feature list
- `model_artifacts/feature_importance.png` — feature importance chart
- `model_artifacts/confusion_matrix.png` — test set confusion matrix

## Setup Instructions

### Prerequisites
- Python 3.11+ with `pandas` (for data generation)
- Snowflake account with ACCOUNTADMIN or equivalent privileges

### Step 1: Generate synthetic data
```bash
uv run python generate_pdm_data.py
```
This creates 7 CSV files in `data_pdm/`.

### Step 2: Create Snowflake environment
Run the SQL files in order:
```
sql/phase1_setup.sql    -- warehouse, DB, schemas
sql/phase1_tables.sql   -- table DDLs
sql/phase1_load.sql     -- upload and load CSVs
```

### Step 3: Build analytics layer
```
sql/phase2_feature_engineering.sql
sql/phase2_health_summary.sql
sql/phase2_production_oee.sql
sql/phase2_maintenance_cost.sql
sql/phase2_validate.sql           -- verify everything
```

## Validation Data

`data_pdm/ground_truth_failures.csv` contains 54 events for model evaluation:
- **39 historical failures** (with degradation start/failure timestamps)
- **5 currently-degrading assets** (no failure yet -- model should detect these)
- **6 false-alarm spike events** (model should NOT flag these)

This file is intentionally excluded from Snowflake to prevent data leakage during training.

## License

MIT License - Copyright (c) 2026 Vaishnav Kedar
