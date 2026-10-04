-- ============================================================
-- Phase 1: Data Loading
-- Upload CSVs to stage and COPY INTO tables
-- Prerequisite: Run phase1_setup.sql and phase1_tables.sql first
-- ============================================================

USE WAREHOUSE PREDICT_MAINT_WH;
USE SCHEMA PREDICT_MAINT_DB.RAW;

-- ---- Upload files to internal stage ----
-- NOTE: Update the file paths to match your local data_pdm/ directory

PUT 'file://G:/CoCo/coco-predictive-maintenance/data_pdm/assets.csv'           @PDM_STAGE/assets           AUTO_COMPRESS=TRUE;
PUT 'file://G:/CoCo/coco-predictive-maintenance/data_pdm/sensor_readings.csv'  @PDM_STAGE/sensor_readings  AUTO_COMPRESS=TRUE;
PUT 'file://G:/CoCo/coco-predictive-maintenance/data_pdm/spare_parts.csv'      @PDM_STAGE/spare_parts      AUTO_COMPRESS=TRUE;
PUT 'file://G:/CoCo/coco-predictive-maintenance/data_pdm/work_orders.csv'      @PDM_STAGE/work_orders      AUTO_COMPRESS=TRUE;
PUT 'file://G:/CoCo/coco-predictive-maintenance/data_pdm/production_log.csv'   @PDM_STAGE/production_log   AUTO_COMPRESS=TRUE;
PUT 'file://G:/CoCo/coco-predictive-maintenance/data_pdm/maintenance_docs.csv' @PDM_STAGE/maintenance_docs AUTO_COMPRESS=TRUE;

-- ---- Load into tables ----

COPY INTO ASSETS
    FROM @PDM_STAGE/assets
    FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);

COPY INTO SENSOR_READINGS
    FROM @PDM_STAGE/sensor_readings
    FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);

COPY INTO SPARE_PARTS
    FROM @PDM_STAGE/spare_parts
    FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);

COPY INTO WORK_ORDERS
    FROM @PDM_STAGE/work_orders
    FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);

COPY INTO PRODUCTION_LOG
    FROM @PDM_STAGE/production_log
    FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);

COPY INTO MAINTENANCE_DOCS
    FROM @PDM_STAGE/maintenance_docs
    FILE_FORMAT = (FORMAT_NAME = CSV_FORMAT);

-- ---- Validate row counts ----

SELECT 'ASSETS'           AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM ASSETS
UNION ALL SELECT 'SENSOR_READINGS',  COUNT(*) FROM SENSOR_READINGS
UNION ALL SELECT 'SPARE_PARTS',      COUNT(*) FROM SPARE_PARTS
UNION ALL SELECT 'WORK_ORDERS',      COUNT(*) FROM WORK_ORDERS
UNION ALL SELECT 'PRODUCTION_LOG',   COUNT(*) FROM PRODUCTION_LOG
UNION ALL SELECT 'MAINTENANCE_DOCS', COUNT(*) FROM MAINTENANCE_DOCS
ORDER BY ROW_COUNT DESC;

-- Expected counts:
--   SENSOR_READINGS  172,800
--   PRODUCTION_LOG     8,730
--   WORK_ORDERS          181
--   SPARE_PARTS           39
--   MAINTENANCE_DOCS      36
--   ASSETS                30
