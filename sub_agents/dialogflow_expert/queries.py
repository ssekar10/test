# sub_agents/dialogflow_expert/queries.py

DIALOGFLOW_METRICS_TABLE = "`dxp-cloud-ivr-prod-751497.alerting_monitoring.dialogflow_metrics`"

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
