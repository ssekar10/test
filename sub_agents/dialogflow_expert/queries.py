# sub_agents/dialogflow_expert/queries.py


DIALOGFLOW_METRICS_TABLE = "`dxp-cloud-ivr-prod-751497.alerting_monitoring.dialogflow_metrics`"
DFCX_TRANSCRIPT_TABLE = "dxp-cloud-ivr-prod-751497.dfcx_analytics.dfcx_transcript"



DF_UNIQUE_SESSIONS = f"""
WITH bq AS (
  SELECT
    TIMESTAMP_TRUNC(
      TIMESTAMP_SECONDS(DIV(UNIX_SECONDS(request_start_time), @bucket_seconds) * @bucket_seconds),
      MINUTE
    ) AS time_bucket,
    session_id
  FROM {DIALOGFLOW_METRICS_TABLE}
  WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
)
SELECT
  CAST(time_bucket AS STRING) AS time,
  COUNT(session_id) AS total_sessions,
  COUNT(DISTINCT session_id) AS unique_sessions
FROM bq
GROUP BY time
ORDER BY time
"""


DF_OVERALL_RESPONSE_TIMES = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  AVG(overall_duration_sesionid) AS avg_response_time_seconds
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
GROUP BY time
ORDER BY time
"""


DF_OVERALL_STATUS = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  COUNT(DISTINCT session_id) AS sessions
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND status = @status
GROUP BY time
ORDER BY time
"""


DF_FAILURES_TOTAL = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  COUNT(session_id) AS total_failures
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND status = "failure"
GROUP BY time
ORDER BY time
"""


DF_FAILURES_BY_REASON = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  COUNT(session_id) AS failures,
  failure_reason AS FailureReason
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND status = "failure"
GROUP BY time, failure_reason
ORDER BY time
"""


DF_BACKEND_TOTAL = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  COUNT(session_id) AS total_backend_calls
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND backend_call <> ""
GROUP BY time
ORDER BY time
"""


DF_BACKEND_BY_URI = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  COUNT(session_id) AS calls,
  backend_call AS backend_uri
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND backend_call <> ""
GROUP BY time, backend_call
ORDER BY time
"""


DF_BACKEND_BY_URI_NORMALIZED = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  COUNT(session_id) AS BackEndCalls,
  CASE
    WHEN STRPOS(backend_call, '.com') > 0 THEN SUBSTR(backend_call, 1, STRPOS(backend_call, '.com/') + 3)
    WHEN STRPOS(backend_call, '.net') > 0 THEN SUBSTR(backend_call, 1, STRPOS(backend_call, '.net/') + 3)
    WHEN STRPOS(backend_call, '786354113445') > 0 THEN SUBSTR(backend_call, 1, STRPOS(backend_call, '786354113445') - 2)
    WHEN STRPOS(backend_call, '27523640185') > 0 THEN SUBSTR(backend_call, 1, STRPOS(backend_call, '27523640185') - 2)
    ELSE backend_call
  END AS local_backend_call
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND backend_call <> ""
GROUP BY time, local_backend_call
ORDER BY time
"""


DF_CALL_VOLUME_BY_FLOW = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  COUNT(session_id) AS BackendFlowName,
  flow_name AS FlowName
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND backend_call <> ""
GROUP BY time, flow_name
ORDER BY time
"""


DF_BACKEND_RESPONSE_TIMES = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  AVG(back_call_duration_ms) AS DFBackendResponseTime,
  backend_call AS backend_URI
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND backend_call NOT LIKE '%cr-modem-health-check'
GROUP BY time, backend_call
ORDER BY time
"""


DF_BACKEND_RESPONSE_TIMES_OVERALL = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  AVG(back_call_duration_ms) AS DFBackendResponseTime
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
GROUP BY time
ORDER BY time
"""


DF_BACKEND_RESPONSE_TIMES_MODEM = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  AVG(back_call_duration_ms) AS DFBackendResponseTime,
  backend_call AS backend_URI
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND backend_call LIKE '%cr-modem-health-check'
GROUP BY time, backend_call
ORDER BY time
"""


DF_BACKEND_FAILURES_HTTP_TOTAL = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  COUNT(session_id) AS TotalFailures
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND status = "failure"
  AND SAFE_CAST(backend_reponse_http_code AS INT64) > 100
GROUP BY time
ORDER BY time
"""


DF_BACKEND_FAILURES_HTTP_BY_CODE = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  COUNT(session_id) AS FailuresWithHTTPCode,
  backend_reponse_http_code AS BackendFailure
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND status = "failure"
  AND SAFE_CAST(backend_reponse_http_code AS INT64) > 100
GROUP BY time, backend_reponse_http_code
ORDER BY time
"""


DF_BACKEND_FAILURES_URI_TOTAL = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  COUNT(session_id) AS TotalBackendFailures
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND status = "failure"
GROUP BY time
ORDER BY time
"""


DF_BACKEND_FAILURES_URI_BY_URL = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(request_start_time, MINUTE) AS STRING) AS time,
  COUNT(session_id) AS BackEnd,
  failure_reason AS Error,
  backend_reponse_http_code AS Code,
  CASE
    WHEN STRPOS(backend_call, '.com') > 0 THEN SUBSTR(backend_call, 1, STRPOS(backend_call, '.com/') + 3)
    WHEN STRPOS(backend_call, '.net') > 0 THEN SUBSTR(backend_call, 1, STRPOS(backend_call, '.net/') + 3)
    WHEN STRPOS(backend_call, '786354113445') > 0 THEN SUBSTR(backend_call, 1, STRPOS(backend_call, '786354113445') - 2)
    WHEN STRPOS(backend_call, '27523640185') > 0 THEN SUBSTR(backend_call, 1, STRPOS(backend_call, '27523640185') - 2)
    ELSE backend_call
  END AS url
FROM {DIALOGFLOW_METRICS_TABLE}
WHERE request_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND backend_call <> ""
  AND status = "failure"
GROUP BY time, url, failure_reason, Code
ORDER BY time
"""


# ---------- Session Metadata Queries (dfcx_session_metadata) ----------

DFCX_SESSION_METADATA_TABLE = "`dxp-cloud-ivr-prod-751497.dfcx_analytics.dfcx_session_metadata`"

# # Get detailed information for a specific session
# Get detailed information for a specific session
DF_SESSION_DETAILS = f"""
SELECT
  session_id,
  session_start_time,
  session_end_time,
  TIMESTAMP_DIFF(session_end_time, session_start_time, SECOND) AS duration_seconds,
  channel,
  agent_id,
  location,
  project_id,
  number_of_turns,
  final_language_code,
  head_intent,
  heuristic_outcome,
  has_end_session,
  has_wrapup,
  has_deflection,
  final_session_parameters,
  ani,
  caller_ani,
  dnis,
  caller_dnis,
  sip_term,
  ccaip_selected_menu_id,
  ccaip_selected_menu_name,
  ccaip_queue_id,
  ccaip_call_id,
  ccaip_deflection,
  ccaip_disconnected_by,
  service_type,
  transfer_type_type,
  transfer_type_module,
  transfer_type_subtype,
  transfer_type_exttype,
  division,
  market,
  region,
  latest_insert_time
FROM {DFCX_SESSION_METADATA_TABLE}
WHERE session_id = @session_id
  AND session_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
LIMIT 1
"""


# Search sessions by time window and optional filters
DF_SESSION_SEARCH = f"""
SELECT
  session_id,
  session_start_time,
  session_end_time,
  TIMESTAMP_DIFF(session_end_time, session_start_time, SECOND) AS duration_seconds,
  channel,
  agent_id,
  number_of_turns,
  head_intent,
  heuristic_outcome,
  has_deflection,
  ccaip_selected_menu_name,
  service_type,
  division,
  market
FROM {DFCX_SESSION_METADATA_TABLE}
WHERE session_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
ORDER BY session_start_time DESC
LIMIT @limit
"""


# Session analytics aggregated by time bucket
DF_SESSION_ANALYTICS = f"""
SELECT
  CAST(TIMESTAMP_TRUNC(session_start_time, MINUTE) AS STRING) AS time,
  COUNT(DISTINCT session_id) AS total_sessions,
  AVG(TIMESTAMP_DIFF(session_end_time, session_start_time, SECOND)) AS avg_duration_seconds,
  AVG(number_of_turns) AS avg_turns,
  COUNTIF(has_deflection) AS deflection_count,
  COUNTIF(has_wrapup) AS wrapup_count,
  COUNTIF(NOT has_end_session) AS incomplete_sessions
FROM {DFCX_SESSION_METADATA_TABLE}
WHERE session_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
GROUP BY time
ORDER BY time
"""

# Session breakdown by channel
DF_SESSION_BY_CHANNEL = f"""
SELECT
  channel,
  COUNT(DISTINCT session_id) AS session_count,
  AVG(TIMESTAMP_DIFF(session_end_time, session_start_time, SECOND)) AS avg_duration_seconds,
  AVG(number_of_turns) AS avg_turns,
  COUNTIF(has_deflection) AS deflection_count
FROM {DFCX_SESSION_METADATA_TABLE}
WHERE session_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
GROUP BY channel
ORDER BY session_count DESC
"""

# Session breakdown by outcome
DF_SESSION_BY_OUTCOME = f"""
SELECT
  heuristic_outcome,
  COUNT(DISTINCT session_id) AS session_count,
  AVG(number_of_turns) AS avg_turns,
  COUNTIF(has_deflection) AS deflection_count
FROM {DFCX_SESSION_METADATA_TABLE}
WHERE session_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND heuristic_outcome IS NOT NULL
GROUP BY heuristic_outcome
ORDER BY session_count DESC
"""

# Top intents by session count
DF_SESSION_TOP_INTENTS = f"""
SELECT
  head_intent,
  COUNT(DISTINCT session_id) AS session_count,
  AVG(number_of_turns) AS avg_turns
FROM {DFCX_SESSION_METADATA_TABLE}
WHERE session_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
  AND head_intent IS NOT NULL
GROUP BY head_intent
ORDER BY session_count DESC
LIMIT 20
"""

# ========================================
# CONVERSATION TRANSCRIPT ANALYTICS
# (All queries optimized for 7-day window)
# ========================================

DF_INTENT_CONFIDENCE_DISTRIBUTION = f"""
SELECT
    CASE
        WHEN intent_confidence_score >= 0.9 THEN 'Very High (0.9-1.0)'
        WHEN intent_confidence_score >= 0.7 THEN 'High (0.7-0.9)'
        WHEN intent_confidence_score >= 0.5 THEN 'Medium (0.5-0.7)'
        WHEN intent_confidence_score >= 0.3 THEN 'Low (0.3-0.5)'
        ELSE 'Very Low (0.0-0.3)'
    END AS confidence_bucket,
    COUNT(*) AS turn_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS percentage
FROM {DFCX_TRANSCRIPT_TABLE}
WHERE session_start_time >= TIMESTAMP('{{{{start_ts_raw}}}}')
  AND session_start_time <= TIMESTAMP('{{{{end_ts}}}}')
  AND intent_confidence_score IS NOT NULL
GROUP BY confidence_bucket
ORDER BY MIN(intent_confidence_score) DESC
"""

DF_FALLBACK_ANALYSIS = f"""
WITH fallback_sessions AS (
    SELECT DISTINCT session_id
    FROM {DFCX_TRANSCRIPT_TABLE}
    WHERE session_start_time >= TIMESTAMP('{{{{start_ts_raw}}}}')
      AND session_start_time <= TIMESTAMP('{{{{end_ts}}}}')
      AND (intent_display_name LIKE '%fallback%' 
           OR intent_display_name LIKE '%no-match%'
           OR intent_confidence_score < 0.3)
)
SELECT
    COUNT(DISTINCT fs.session_id) AS fallback_sessions,
    COUNT(t.position) AS fallback_turns,
    ROUND(COUNT(DISTINCT fs.session_id) * 100.0 / 
          NULLIF((SELECT COUNT(DISTINCT session_id) 
                  FROM {DFCX_TRANSCRIPT_TABLE} 
                  WHERE session_start_time >= TIMESTAMP('{{{{start_ts_raw}}}}')
                    AND session_start_time <= TIMESTAMP('{{{{end_ts}}}}')), 0), 2) AS fallback_session_rate,
    ARRAY_AGG(t.user_utterance IGNORE NULLS LIMIT 10) AS sample_unresolved_utterances
FROM fallback_sessions fs
LEFT JOIN {DFCX_TRANSCRIPT_TABLE} t
  ON fs.session_id = t.session_id
  AND t.session_start_time >= TIMESTAMP('{{{{start_ts_raw}}}}')
  AND t.session_start_time <= TIMESTAMP('{{{{end_ts}}}}')
  AND (t.intent_display_name LIKE '%fallback%' OR t.intent_confidence_score < 0.3)
"""

DF_FLOW_TRAVERSAL = f"""
SELECT
    flow_display_name,
    page_display_name,
    COUNT(DISTINCT session_id) AS session_count,
    COUNT(*) AS turn_count,
    ROUND(AVG(position), 2) AS avg_turn_depth
FROM {DFCX_TRANSCRIPT_TABLE}
WHERE session_start_time >= TIMESTAMP('{{{{start_ts_raw}}}}')
  AND session_start_time <= TIMESTAMP('{{{{end_ts}}}}')
  AND flow_display_name IS NOT NULL
  AND page_display_name IS NOT NULL
GROUP BY flow_display_name, page_display_name
ORDER BY session_count DESC
LIMIT 20
"""

DF_SESSION_REPLAY = f"""
SELECT
    position AS turn_number,
    request_time,
    user_utterance,
    intent_display_name,
    intent_confidence_score,
    page_display_name,
    flow_display_name,
    agent_response,
    TO_JSON_STRING(webhooks) AS webhook_info,
    session_parameters,
    event,
    match_type,
    channel
FROM {DFCX_TRANSCRIPT_TABLE}
WHERE session_id = '{{{{session_id}}}}'
  AND session_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {{{{days}}}} DAY)
ORDER BY position
LIMIT 500
"""

DF_EXECUTION_COMPLEXITY = f"""
SELECT
    session_id,
    COUNT(*) AS turn_count,
    ARRAY_AGG(DISTINCT flow_display_name IGNORE NULLS) AS flows_visited,
    COUNTIF(intent_display_name LIKE '%fallback%') AS fallback_count
FROM {DFCX_TRANSCRIPT_TABLE}
WHERE session_start_time >= TIMESTAMP('{{{{start_ts_raw}}}}')
  AND session_start_time <= TIMESTAMP('{{{{end_ts}}}}')
GROUP BY session_id
HAVING turn_count >= {{{{min_turns}}}}
ORDER BY turn_count DESC
LIMIT 50
"""

DF_VOICE_LATENCY = f"""
SELECT
    TIMESTAMP_TRUNC(request_time, MINUTE) AS time_bucket,
    ROUND(AVG(input_audio_ms), 2) AS avg_input_latency_ms,
    ROUND(AVG(output_audio_ms), 2) AS avg_output_latency_ms,
    ROUND(MAX(output_audio_ms), 2) AS max_output_latency_ms,
    COUNT(*) AS turn_count
FROM {DFCX_TRANSCRIPT_TABLE}
WHERE session_start_time >= TIMESTAMP('{{{{start_ts_raw}}}}')
  AND session_start_time <= TIMESTAMP('{{{{end_ts}}}}')
  AND channel = 'TELEPHONY'
  AND (input_audio_ms IS NOT NULL OR output_audio_ms IS NOT NULL)
GROUP BY time_bucket
ORDER BY time_bucket
"""

DF_RESPONSE_ANALYSIS = f"""
SELECT
    page_display_name,
    agent_response,
    COUNT(*) AS response_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(PARTITION BY page_display_name), 2) AS page_percentage
FROM {DFCX_TRANSCRIPT_TABLE}
WHERE session_start_time >= TIMESTAMP('{{{{start_ts_raw}}}}')
  AND session_start_time <= TIMESTAMP('{{{{end_ts}}}}')
  AND agent_response IS NOT NULL
  AND LENGTH(agent_response) > 0
GROUP BY page_display_name, agent_response
QUALIFY ROW_NUMBER() OVER(PARTITION BY page_display_name ORDER BY COUNT(*) DESC) <= 5
ORDER BY page_display_name, response_count DESC
LIMIT 30
"""

DF_EVENT_ANALYSIS = f"""
SELECT
    event,
    page_display_name,
    flow_display_name,
    COUNT(*) AS event_count,
    COUNT(DISTINCT session_id) AS session_count
FROM {DFCX_TRANSCRIPT_TABLE}
WHERE session_start_time >= TIMESTAMP('{{{{start_ts_raw}}}}')
  AND session_start_time <= TIMESTAMP('{{{{end_ts}}}}')
  AND event IS NOT NULL
  AND event != ''
GROUP BY event, page_display_name, flow_display_name
ORDER BY event_count DESC
LIMIT 50
"""

DF_FAILED_SESSIONS_EXPORT = f"""
WITH session_summary AS (
    SELECT
        session_id,
        MIN(session_start_time) AS session_start,
        COUNT(*) AS turn_count,
        COUNTIF(intent_display_name LIKE '%fallback%') AS fallback_count,
        MAX(CASE WHEN intent_display_name LIKE '%fallback%' THEN 1 ELSE 0 END) AS ended_in_fallback
    FROM {DFCX_TRANSCRIPT_TABLE}
    WHERE session_start_time >= TIMESTAMP('{{{{start_ts_raw}}}}')
      AND session_start_time <= TIMESTAMP('{{{{end_ts}}}}')
    GROUP BY session_id
)
SELECT
    session_id,
    session_start,
    turn_count,
    fallback_count,
    ended_in_fallback
FROM session_summary
WHERE fallback_count > 0 OR turn_count > 30
ORDER BY fallback_count DESC, turn_count DESC
LIMIT {{{{limit}}}}
"""

DF_CONVERSATION_SUMMARY = f"""
SELECT
    session_id,
    TIMESTAMP_DIFF(MAX(request_time), MIN(request_time), SECOND) AS duration_seconds,
    COUNT(*) AS total_turns,
    ARRAY_AGG(DISTINCT flow_display_name IGNORE NULLS) AS flows_visited,
    COUNTIF(intent_display_name LIKE '%fallback%') AS fallback_count,
    ANY_VALUE(channel) AS channel
FROM {DFCX_TRANSCRIPT_TABLE}
WHERE session_id = '{{{{session_id}}}}'
  AND session_start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {{{{days}}}} DAY)
GROUP BY session_id
"""