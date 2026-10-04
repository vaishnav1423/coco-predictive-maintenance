-- ============================================================
-- Phase 2: Asset Health Summary
-- One row per asset with latest health snapshot
-- Dynamic Table | Full refresh | 60-min lag | 30 rows
-- ============================================================

USE WAREHOUSE PREDICT_MAINT_WH;
USE SCHEMA PREDICT_MAINT_DB.ANALYTICS;

CREATE OR REPLACE DYNAMIC TABLE ASSET_HEALTH_SUMMARY
    TARGET_LAG = '60 minutes'
    WAREHOUSE = PREDICT_MAINT_WH
    AS
WITH latest_readings AS (
    SELECT *
    FROM PREDICT_MAINT_DB.ANALYTICS.ASSET_SENSOR_STATS
    QUALIFY ROW_NUMBER() OVER (PARTITION BY ASSET_ID ORDER BY READING_TS DESC) = 1
),
maintenance_history AS (
    SELECT
        ASSET_ID,
        MAX(CASE WHEN WO_TYPE IN ('PREVENTIVE','CORRECTIVE') THEN COMPLETED_TS END) AS LAST_MAINTENANCE_TS,
        COUNT(CASE WHEN WO_TYPE = 'CORRECTIVE'
                    AND CREATED_TS >= DATEADD('day', -30, CURRENT_TIMESTAMP()) THEN 1 END) AS CORRECTIVE_WO_30D,
        COUNT(CASE WHEN WO_TYPE = 'CORRECTIVE' THEN 1 END) AS TOTAL_CORRECTIVE_WOS
    FROM PREDICT_MAINT_DB.RAW.WORK_ORDERS
    GROUP BY ASSET_ID
)
SELECT
    lr.ASSET_ID,
    lr.ASSET_TYPE,
    lr.PLANT,
    lr.CRITICALITY,
    lr.READING_TS                       AS LATEST_READING_TS,
    lr.VIBRATION_MM_S                   AS LATEST_VIBRATION,
    lr.TEMPERATURE_C                    AS LATEST_TEMPERATURE,
    lr.RPM                              AS LATEST_RPM,
    lr.MOTOR_CURRENT_A                  AS LATEST_CURRENT,
    lr.VIB_AVG_24H,
    lr.TEMP_AVG_24H,
    lr.CURR_AVG_24H,
    lr.VIB_BASELINE_DEV_PCT,
    lr.TEMP_BASELINE_DEV_PCT,
    lr.CURR_BASELINE_DEV_PCT,
    lr.VIB_STATUS,
    lr.TEMP_STATUS,
    CASE WHEN lr.VIB_STATUS = 'ALARM' OR lr.TEMP_STATUS = 'ALARM' THEN 'ALARM'
         WHEN lr.VIB_STATUS = 'ALERT' OR lr.TEMP_STATUS = 'ALERT' THEN 'ALERT'
         ELSE 'NORMAL' END             AS OVERALL_STATUS,
    lr.VIB_BREACH_COUNT_24H,
    lr.TEMP_BREACH_COUNT_24H,
    mh.LAST_MAINTENANCE_TS,
    DATEDIFF('hour', mh.LAST_MAINTENANCE_TS, lr.READING_TS) AS HOURS_SINCE_LAST_MAINT,
    mh.CORRECTIVE_WO_30D,
    mh.TOTAL_CORRECTIVE_WOS
FROM latest_readings lr
LEFT JOIN maintenance_history mh ON lr.ASSET_ID = mh.ASSET_ID;
