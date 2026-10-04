-- ============================================================
-- Phase 1: Environment Setup
-- Creates warehouse, database, schemas, file format, and stage
-- ============================================================

-- Warehouse
CREATE WAREHOUSE IF NOT EXISTS PREDICT_MAINT_WH
    WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 120
    AUTO_RESUME = TRUE
    COMMENT = 'Warehouse for Predictive Maintenance project';

USE WAREHOUSE PREDICT_MAINT_WH;

-- Database
CREATE DATABASE IF NOT EXISTS PREDICT_MAINT_DB
    COMMENT = 'Predictive Maintenance - Industrial IoT sensor data, work orders, and maintenance docs';

-- Schemas
CREATE SCHEMA IF NOT EXISTS PREDICT_MAINT_DB.RAW
    COMMENT = 'Raw landing zone for CSV data';

CREATE SCHEMA IF NOT EXISTS PREDICT_MAINT_DB.ANALYTICS
    COMMENT = 'Curated analytics layer - feature engineering, ML models, dashboards';

-- File format for CSV loading
CREATE FILE FORMAT IF NOT EXISTS PREDICT_MAINT_DB.RAW.CSV_FORMAT
    TYPE = 'CSV'
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    SKIP_HEADER = 1
    NULL_IF = ('')
    EMPTY_FIELD_AS_NULL = TRUE;

-- Internal stage for CSV uploads
USE SCHEMA PREDICT_MAINT_DB.RAW;

CREATE STAGE IF NOT EXISTS PDM_STAGE
    COMMENT = 'Internal stage for loading predictive maintenance CSV data';
