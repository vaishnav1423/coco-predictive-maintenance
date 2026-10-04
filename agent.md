# Predictive Maintenance Project - Agent Context

## Project Overview

Industrial IoT predictive maintenance system built on Snowflake. Synthetic data simulates 30 assets across 3 Indian manufacturing plants (Pune, Chennai, Aurangabad) with realistic sensor degradation, failure events, and maintenance workflows.

## Snowflake Environment

- **Warehouse**: `PREDICT_MAINT_WH` (X-Small, auto-suspend 120s)
- **Database**: `PREDICT_MAINT_DB`
- **Schemas**: `RAW` (landing zone), `ANALYTICS` (curated layer)

## Object Inventory

### RAW Schema (source tables)

| Table | Rows | Description |
|---|---|---|
| `ASSETS` | 30 | Asset master data with baselines and thresholds |
| `SENSOR_READINGS` | 172,800 | 30-min interval IoT data (vibration, temp, RPM, current) over 120 days |
| `WORK_ORDERS` | 181 | Corrective, preventive, and inspection work orders |
| `PRODUCTION_LOG` | 8,730 | Shift-level production data for OEE |
| `SPARE_PARTS` | 39 | Parts inventory across 3 plants |
| `MAINTENANCE_DOCS` | 36 | Manuals/SOPs for Cortex Search |

### ANALYTICS Schema (curated layer)

| Object | Type | Rows | Description |
|---|---|---|---|
| `ASSET_SENSOR_STATS` | Dynamic Table (incremental, 30-min lag) | 172,800 | 36 ML features: rolling means/std, rate-of-change, baseline deviation, threshold breaches |
| `ASSET_HEALTH_SUMMARY` | Dynamic Table (full, 60-min lag) | 30 | Latest health snapshot per asset with overall status |
| `PRODUCTION_OEE` | Dynamic Table (incremental, 60-min lag) | 8,730 | OEE = Availability x Performance x Quality with 7-day rolling average |
| `MAINTENANCE_COST_SUMMARY` | View | 30 | Maintenance costs, MTBF, repair times, spare parts stock |

### Supporting Objects

| Object | Schema | Type |
|---|---|---|
| `CSV_FORMAT` | RAW | File Format |
| `PDM_STAGE` | RAW | Internal Stage |

## Data Characteristics

- **5 asset types**: CNC_MACHINE, PUMP, COMPRESSOR, MOTOR, CONVEYOR
- **5 failure modes**: BEARING_WEAR, IMBALANCE_MISALIGNMENT, OVERHEATING, LUBRICATION_LOSS, MOTOR_ELECTRICAL
- **Degradation physics**: Power-law curves over 5-13 days, each mode has a distinct multi-channel sensor signature
- **Hidden validation data**: 5 currently-degrading assets + 6 false-alarm assets (ground_truth_failures.csv, not loaded into Snowflake)
- **Sensor dropouts**: ~0.4% NULLs across all channels

## Key Relationships

```
ASSETS.ASSET_ID  -->  SENSOR_READINGS.ASSET_ID
ASSETS.ASSET_ID  -->  WORK_ORDERS.ASSET_ID
ASSETS.ASSET_ID  -->  PRODUCTION_LOG.ASSET_ID
ASSETS.PLANT     -->  SPARE_PARTS.PLANT
WORK_ORDERS.PART_ID --> SPARE_PARTS.PART_ID
```

## Project Phases

| Phase | Status | Description |
|---|---|---|
| 1 - Data Loading | Done | Warehouse, DB, schemas, tables, CSV loading |
| 2 - Feature Engineering | Done | Dynamic tables with rolling stats, OEE, health summary |
| 3 - ML Model | Done | Random Forest failure detector (F1=0.64, 80% degradation detection) |
| 4 - Cortex Search & Agent | Planned | Maintenance docs search + conversational agent |
| 5 - Dashboard & Alerting | Planned | Streamlit-in-Snowflake app + Snowflake Alerts |

## ML Model (Phase 3)

- **Algorithm**: Random Forest (200 trees, balanced weights, max_depth=15)
- **Input**: 34 numeric features from ASSET_SENSOR_STATS
- **Labels**: Binary — readings in degradation windows = 1, normal = 0
- **Train/test split**: Time-based at Sep 1, 2026
- **Test F1**: 0.64 | Recall: 73% | Precision: 57% | Accuracy: 95%
- **Degradation detection**: 80% (4/5 hidden degrading assets caught)
- **False alarm rejection**: 67% (4/6 correctly ignored)
- **Top features**: VIB_BASELINE_DEV_PCT (12%), TEMP_BASELINE_DEV_PCT (8%), TEMP_AVG_7D (8%)
- **Artifacts**: `model_artifacts/failure_detector.pkl`, feature_importance.png, confusion_matrix.png

## SQL Files

All SQL is in the `sql/` directory, organized by phase:

- `phase1_setup.sql` - Warehouse, database, schemas, file format, stage
- `phase1_tables.sql` - All 6 RAW table DDLs
- `phase1_load.sql` - PUT + COPY INTO for all CSVs
- `phase2_feature_engineering.sql` - ASSET_SENSOR_STATS dynamic table
- `phase2_health_summary.sql` - ASSET_HEALTH_SUMMARY dynamic table
- `phase2_production_oee.sql` - PRODUCTION_OEE dynamic table
- `phase2_maintenance_cost.sql` - MAINTENANCE_COST_SUMMARY view
- `phase2_validate.sql` - Validation queries for Phase 2
- `phase3_model_inference.sql` - Batch inference and asset risk scoring

## Naming Conventions

- **Snowflake objects**: `PREDICT_MAINT_` prefix for warehouse/database
- **Tables**: UPPER_SNAKE_CASE
- **SQL files**: `phase{N}_{description}.sql`
- **Asset IDs**: `AST-001` through `AST-030`
- **Work order IDs**: `WO-NNNNN`
- **Part IDs**: `SP-NNN-{PLANT_CODE}` (PUN/CHE/AUR)
