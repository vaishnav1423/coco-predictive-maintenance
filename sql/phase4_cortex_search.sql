-- ============================================================
-- Phase 4: Cortex Search Service
-- Hybrid search over maintenance manuals, SOPs, and references
-- ============================================================

USE WAREHOUSE PREDICT_MAINT_WH;
USE SCHEMA PREDICT_MAINT_DB.ANALYTICS;

-- Create search service on maintenance documentation
CREATE OR REPLACE CORTEX SEARCH SERVICE PDM_DOCS_SEARCH
  ON TEXT
  ATTRIBUTES DOC_TYPE, APPLIES_TO, TITLE, SECTION_TITLE
  WAREHOUSE = PREDICT_MAINT_WH
  TARGET_LAG = '1 day'
  COMMENT = 'Search over maintenance manuals, SOPs, and OEE reference docs'
AS (
    SELECT
        TEXT,
        DOC_ID,
        SECTION_ID,
        TITLE,
        SECTION_TITLE,
        DOC_TYPE,
        APPLIES_TO
    FROM PREDICT_MAINT_DB.RAW.MAINTENANCE_DOCS
);

-- Verify search service is active
SHOW CORTEX SEARCH SERVICES IN SCHEMA PREDICT_MAINT_DB.ANALYTICS;

-- Test query: vibration issue
SELECT PARSE_JSON(
  SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
    'PREDICT_MAINT_DB.ANALYTICS.PDM_DOCS_SEARCH',
    '{
       "query": "vibration is high on a pump, what should I check?",
       "columns": ["TEXT", "TITLE", "SECTION_TITLE", "DOC_TYPE", "APPLIES_TO"],
       "limit": 3
    }'
  )
)['results'] AS results;

-- Test query with filter: only bearing wear docs
SELECT PARSE_JSON(
  SNOWFLAKE.CORTEX.SEARCH_PREVIEW(
    'PREDICT_MAINT_DB.ANALYTICS.PDM_DOCS_SEARCH',
    '{
       "query": "what spare parts do I need?",
       "columns": ["TEXT", "TITLE", "SECTION_TITLE"],
       "filter": {"@eq": {"APPLIES_TO": "BEARING_WEAR"}},
       "limit": 3
    }'
  )
)['results'] AS results;
