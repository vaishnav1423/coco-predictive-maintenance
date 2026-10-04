-- ============================================================
-- Phase 2: Production OEE
-- OEE metrics per asset per shift with rolling averages
-- Dynamic Table | Incremental | 60-min lag | 8,730 rows
-- ============================================================

USE WAREHOUSE PREDICT_MAINT_WH;
USE SCHEMA PREDICT_MAINT_DB.ANALYTICS;

CREATE OR REPLACE DYNAMIC TABLE PRODUCTION_OEE
    TARGET_LAG = '60 minutes'
    WAREHOUSE = PREDICT_MAINT_WH
    AS
SELECT
    p.SHIFT_DATE,
    p.SHIFT,
    p.ASSET_ID,
    a.ASSET_TYPE,
    a.PLANT,
    a.CRITICALITY,
    p.PLANNED_MINUTES,
    p.BREAKDOWN_MINUTES,
    p.PLANNED_MAINTENANCE_MINUTES,
    p.SMALL_STOP_MINUTES,

    -- Run time
    GREATEST(p.PLANNED_MINUTES - p.BREAKDOWN_MINUTES - p.PLANNED_MAINTENANCE_MINUTES, 0) AS RUN_MINUTES,

    p.TOTAL_UNITS,
    p.GOOD_UNITS,

    -- Availability = (Planned - Breakdown - PM) / Planned
    CASE WHEN p.PLANNED_MINUTES > 0
         THEN ROUND((p.PLANNED_MINUTES - p.BREAKDOWN_MINUTES - p.PLANNED_MAINTENANCE_MINUTES)::FLOAT
                     / p.PLANNED_MINUTES, 4)
         ELSE NULL END AS AVAILABILITY,

    -- Performance = (Total Units * Ideal Cycle) / (Run Time in seconds)
    CASE WHEN (p.PLANNED_MINUTES - p.BREAKDOWN_MINUTES - p.PLANNED_MAINTENANCE_MINUTES) > 0
         THEN ROUND((p.TOTAL_UNITS * p.IDEAL_CYCLE_SECONDS)::FLOAT
                     / ((p.PLANNED_MINUTES - p.BREAKDOWN_MINUTES - p.PLANNED_MAINTENANCE_MINUTES) * 60), 4)
         ELSE NULL END AS PERFORMANCE,

    -- Quality = Good Units / Total Units
    CASE WHEN p.TOTAL_UNITS > 0
         THEN ROUND(p.GOOD_UNITS::FLOAT / p.TOTAL_UNITS, 4)
         ELSE NULL END AS QUALITY,

    -- OEE = Availability * Performance * Quality
    CASE WHEN p.PLANNED_MINUTES > 0
              AND (p.PLANNED_MINUTES - p.BREAKDOWN_MINUTES - p.PLANNED_MAINTENANCE_MINUTES) > 0
              AND p.TOTAL_UNITS > 0
         THEN ROUND(
              ((p.PLANNED_MINUTES - p.BREAKDOWN_MINUTES - p.PLANNED_MAINTENANCE_MINUTES)::FLOAT / p.PLANNED_MINUTES)
              * ((p.TOTAL_UNITS * p.IDEAL_CYCLE_SECONDS)::FLOAT
                 / ((p.PLANNED_MINUTES - p.BREAKDOWN_MINUTES - p.PLANNED_MAINTENANCE_MINUTES) * 60))
              * (p.GOOD_UNITS::FLOAT / p.TOTAL_UNITS), 4)
         ELSE NULL END AS OEE,

    -- 7-day rolling average OEE (~21 shifts per asset per week)
    AVG(
        CASE WHEN p.PLANNED_MINUTES > 0
                  AND (p.PLANNED_MINUTES - p.BREAKDOWN_MINUTES - p.PLANNED_MAINTENANCE_MINUTES) > 0
                  AND p.TOTAL_UNITS > 0
             THEN ((p.PLANNED_MINUTES - p.BREAKDOWN_MINUTES - p.PLANNED_MAINTENANCE_MINUTES)::FLOAT / p.PLANNED_MINUTES)
                  * ((p.TOTAL_UNITS * p.IDEAL_CYCLE_SECONDS)::FLOAT
                     / ((p.PLANNED_MINUTES - p.BREAKDOWN_MINUTES - p.PLANNED_MAINTENANCE_MINUTES) * 60))
                  * (p.GOOD_UNITS::FLOAT / p.TOTAL_UNITS)
             ELSE NULL END
    ) OVER (PARTITION BY p.ASSET_ID ORDER BY p.SHIFT_DATE, p.SHIFT
            ROWS BETWEEN 20 PRECEDING AND CURRENT ROW) AS OEE_ROLLING_7D

FROM PREDICT_MAINT_DB.RAW.PRODUCTION_LOG p
JOIN PREDICT_MAINT_DB.RAW.ASSETS a ON p.ASSET_ID = a.ASSET_ID;
