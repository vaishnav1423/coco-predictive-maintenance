-- ============================================================
-- Phase 1: Table Definitions
-- All 6 raw tables in PREDICT_MAINT_DB.RAW
-- ============================================================

USE SCHEMA PREDICT_MAINT_DB.RAW;

-- 30 industrial assets across 3 plants
CREATE TABLE IF NOT EXISTS ASSETS (
    ASSET_ID                    VARCHAR(10)     NOT NULL,
    ASSET_NAME                  VARCHAR(50)     NOT NULL,
    ASSET_TYPE                  VARCHAR(30)     NOT NULL,
    PLANT                       VARCHAR(30)     NOT NULL,
    LINE                        VARCHAR(20)     NOT NULL,
    MANUFACTURER                VARCHAR(50)     NOT NULL,
    INSTALL_DATE                DATE            NOT NULL,
    CRITICALITY                 VARCHAR(1)      NOT NULL,
    RATED_RPM                   NUMBER(38,0)    NOT NULL,
    BASELINE_VIBRATION_MM_S     FLOAT           NOT NULL,
    VIB_ALERT_MM_S              FLOAT           NOT NULL,
    VIB_ALARM_MM_S              FLOAT           NOT NULL,
    BASELINE_TEMP_C             FLOAT           NOT NULL,
    TEMP_ALERT_C                FLOAT           NOT NULL,
    TEMP_ALARM_C                FLOAT           NOT NULL,
    BASELINE_CURRENT_A          FLOAT           NOT NULL,
    IDEAL_CYCLE_SECONDS         FLOAT           NOT NULL,
    DOWNTIME_COST_PER_HOUR_INR  NUMBER(38,0)    NOT NULL,
    CONSTRAINT PK_ASSETS PRIMARY KEY (ASSET_ID)
);

-- 172,800 sensor readings (30-min intervals, 120 days, 30 assets)
CREATE TABLE IF NOT EXISTS SENSOR_READINGS (
    READING_TS          TIMESTAMP_NTZ(9)    NOT NULL,
    ASSET_ID            VARCHAR(10)         NOT NULL,
    VIBRATION_MM_S      FLOAT,
    TEMPERATURE_C       FLOAT,
    RPM                 FLOAT,
    MOTOR_CURRENT_A     FLOAT
);

-- 39 spare parts across 3 plants
CREATE TABLE IF NOT EXISTS SPARE_PARTS (
    PART_ID                 VARCHAR(20)     NOT NULL,
    PART_NAME               VARCHAR(100)    NOT NULL,
    USED_FOR_FAILURE_MODE   VARCHAR(50)     NOT NULL,
    COMPATIBLE_ASSET_TYPES  VARCHAR(200)    NOT NULL,
    PLANT                   VARCHAR(30)     NOT NULL,
    UNIT_COST_INR           NUMBER(38,0)    NOT NULL,
    ON_HAND_QTY             NUMBER(38,0)    NOT NULL,
    REORDER_POINT           NUMBER(38,0)    NOT NULL,
    LEAD_TIME_DAYS          NUMBER(38,0)    NOT NULL,
    SUPPLIER_NAME           VARCHAR(50)     NOT NULL,
    CONSTRAINT PK_SPARE_PARTS PRIMARY KEY (PART_ID)
);

-- 181 work orders (corrective, preventive, inspection)
CREATE TABLE IF NOT EXISTS WORK_ORDERS (
    WO_ID                   VARCHAR(20)         NOT NULL,
    ASSET_ID                VARCHAR(10)         NOT NULL,
    WO_TYPE                 VARCHAR(20)         NOT NULL,
    PRIORITY                VARCHAR(10)         NOT NULL,
    STATUS                  VARCHAR(20)         NOT NULL,
    CREATED_TS              TIMESTAMP_NTZ(9)    NOT NULL,
    STARTED_TS              TIMESTAMP_NTZ(9),
    COMPLETED_TS            TIMESTAMP_NTZ(9),
    CAUSE_CODE              VARCHAR(50),
    PART_ID                 VARCHAR(20),
    PART_QTY                NUMBER(38,0),
    LABOR_HOURS             FLOAT               NOT NULL,
    PARTS_COST_INR          NUMBER(38,0)        NOT NULL,
    TOTAL_COST_INR          NUMBER(38,0)        NOT NULL,
    WAITING_FOR_PARTS_HOURS FLOAT               NOT NULL,
    TECHNICIAN              VARCHAR(50)         NOT NULL,
    DESCRIPTION             VARCHAR(500)        NOT NULL,
    CONSTRAINT PK_WORK_ORDERS PRIMARY KEY (WO_ID)
);

-- 8,730 production shifts (OEE source data)
CREATE TABLE IF NOT EXISTS PRODUCTION_LOG (
    SHIFT_DATE                  DATE            NOT NULL,
    SHIFT                       VARCHAR(1)      NOT NULL,
    ASSET_ID                    VARCHAR(10)     NOT NULL,
    PLANNED_MINUTES             NUMBER(38,0)    NOT NULL,
    BREAKDOWN_MINUTES           NUMBER(38,0)    NOT NULL,
    PLANNED_MAINTENANCE_MINUTES NUMBER(38,0)    NOT NULL,
    SMALL_STOP_MINUTES          NUMBER(38,0)    NOT NULL,
    IDEAL_CYCLE_SECONDS         FLOAT           NOT NULL,
    TOTAL_UNITS                 NUMBER(38,0)    NOT NULL,
    GOOD_UNITS                  NUMBER(38,0)    NOT NULL
);

-- 36 maintenance manual/SOP sections for Cortex Search
CREATE TABLE IF NOT EXISTS MAINTENANCE_DOCS (
    DOC_ID          VARCHAR(20)     NOT NULL,
    SECTION_ID      VARCHAR(30)     NOT NULL,
    TITLE           VARCHAR(200)    NOT NULL,
    SECTION_TITLE   VARCHAR(200)    NOT NULL,
    DOC_TYPE        VARCHAR(20)     NOT NULL,
    APPLIES_TO      VARCHAR(100)    NOT NULL,
    VERSION         VARCHAR(10)     NOT NULL,
    EFFECTIVE_DATE  DATE            NOT NULL,
    OWNER           VARCHAR(100)    NOT NULL,
    TEXT            VARCHAR(5000)   NOT NULL
);
