-- ============================================================
-- Phase 4: Cortex Agent
-- Maintenance technician assistant with search + analytics tools
-- ============================================================

USE WAREHOUSE PREDICT_MAINT_WH;
USE SCHEMA PREDICT_MAINT_DB.ANALYTICS;

-- Create the maintenance agent
CREATE OR REPLACE AGENT PDM_MAINTENANCE_AGENT
  COMMENT = 'Predictive maintenance assistant for plant technicians'
  FROM SPECIFICATION
$$
models:
  orchestration: claude-sonnet-4-6

instructions:
  response: |
    You are a maintenance technician assistant for an industrial manufacturing operation
    with 3 plants (Pune, Chennai, Aurangabad) running CNC machines, pumps, compressors,
    motors, and conveyors.

    When answering questions:
    - Cite the document ID and section (e.g., MNT-001, Section: Symptoms and Signals)
    - Recommend specific actions from the maintenance guides
    - Reference alert/alarm thresholds when discussing sensor readings
    - Mention relevant spare parts and expected downtime when applicable
    - For SOP questions, reference the specific SOP number and steps
    - Be concise and actionable - technicians need clear guidance fast

    Failure modes covered: BEARING_WEAR, IMBALANCE_MISALIGNMENT, OVERHEATING,
    LUBRICATION_LOSS, MOTOR_ELECTRICAL.
  sample_questions:
    - question: "Vibration on CNC Machine 01 has been rising for 3 days. What should I do?"
    - question: "What is the escalation process when an alarm triggers?"
    - question: "What spare parts do I need for a bearing replacement on a pump?"

tools:
  - tool_spec:
      type: cortex_search
      name: maintenance_docs
      description: >
        Search maintenance manuals, SOPs, and reference documents. Contains failure mode
        guides with symptoms, thresholds, causes, actions, and parts lists. Also includes
        alert triage SOPs, work order procedures, and OEE definitions.

tool_resources:
  maintenance_docs:
    search_service: "PREDICT_MAINT_DB.ANALYTICS.PDM_DOCS_SEARCH"
    max_results: "5"
    title_column: "TITLE"
    id_column: "SECTION_ID"
$$;

-- Verify agent is created
SHOW AGENTS IN SCHEMA PREDICT_MAINT_DB.ANALYTICS;

-- Test query
SELECT TRY_PARSE_JSON(
  SNOWFLAKE.CORTEX.DATA_AGENT_RUN(
    'PREDICT_MAINT_DB.ANALYTICS.PDM_MAINTENANCE_AGENT',
    $${
      "messages": [
        {
          "role": "user",
          "content": [
            { "type": "text", "text": "Vibration on CNC Machine 01 has been rising for 3 days. What should I do?" }
          ]
        }
      ]
    }$$
  )
) AS resp;
