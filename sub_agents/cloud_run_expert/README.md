# Cloud Run Expert Sub‑Agent

The Cloud Run expert is a read‑only sub‑agent focused on observing, diagnosing, and explaining Cloud Run services in a GCP project. It uses Cloud Monitoring, Cloud Logging, and Cloud Run service configuration to support SRE and developer workflows.[file:1]

---

## Features

### Service discovery and configuration

- List Cloud Run services in a region.
- Fetch detailed configuration for a single service, including:
  - Min/max instances
  - Concurrency
  - CPU/memory allocation
  - Traffic splits and revisions
- Cache configuration for short periods to improve performance.[file:1]

Key functions (tools):

- `list_services`
- `get_service_details_*`
- Config caching helpers in `config.py`.[file:1]

---

### Metrics summary (Cloud Monitoring)

Fast metrics using Cloud Monitoring:

- Request count over a time window.
- Request rate (per minute / per second).
- Latency percentiles (e.g., p95) from distribution metrics.
- CPU utilization (percentage).
- Memory utilization (percentage).
- Instance count over time.[file:1]

Key functions:

- `get_metrics_summary`
- `query_all_services_metrics_summary`
- `get_resource_utilization`
- `get_request_rate_and_latency_summary` (fast request counts + p95 latency).[file:1]

These functions are optimized for windows up to at least 6 hours and do not scan logs.[file:1]

---

### Utilization and scaling analysis

The sub‑agent can:

- Compute actual CPU and memory utilization for a service using percentile‑aligned distribution metrics.
- Correlate utilization with instance count and configured max instances.
- Identify whether a service is:
  - Under‑utilized
  - CPU‑bound or memory‑bound
  - Potentially scale‑limited by configuration (max instances, concurrency).[file:1]

Key function:

- `get_all_utilization_metrics(service_name, region, hours)`.[file:1]

---

### Performance triage (“Service is slow”)

When a user reports that a service is slow, the agent:

1. **Symptom check (fast)**  
   Calls `get_all_utilization_metrics(service_name, region, 1)` to inspect CPU, memory, instance count, and config for the last hour.[file:1]

2. **Traffic check (fast)**  
   Uses Monitoring‑based tools (for example `get_request_rate_and_latency_summary`) to understand request volume and latency without scanning logs.[file:1]

3. **Scaling check**  
   Compares current/peak instance count to configured max instances and considers concurrency settings.[file:1]

4. **Correlation and diagnosis**  
   Determines whether the service itself is overloaded or likely waiting on downstream dependencies.[file:1]

5. **Recommendations**  
   Suggests concrete next steps, such as updating max instances, adjusting concurrency, or investigating downstream services/databases.[file:1]

By default, this workflow does not use log‑based exact counting unless explicitly requested.[file:1]

---

### Exact request counts (Cloud Logging, forensic)

For deep, forensic analysis, the agent can:

- Scan Cloud Logging for request entries over a time window.
- Count:
  - Total requests
  - 2xx (successful)
  - 4xx (client error)
  - 5xx (server error) requests.[file:1]

Key functions:

- `get_exact_request_counts`
- `get_exact_request_counts_from_logs`.[file:1]

These are intentionally treated as slower tools, used only when the user requests “exact counts from logs” or similar wording.[file:1]

---

### Multi‑region and multi‑service views

The agent supports:

- Parallel queries across regions.
- Aggregated or per‑service metric summaries across multiple services.
- Chunked log queries over longer windows (up to several days), with rate limiting and entry caps.[file:1]

This enables higher‑level views such as “top services by traffic” or “services with highest latency per region”.[file:1]

---

## Known Limitations

### Monitoring vs logging

- Monitoring‑based tools are:
  - Fast
  - Suitable for up to 6‑hour windows (and beyond, with more aggregation)
  - Slightly approximate due to aggregation/sampling.[file:1]

- Logging‑based tools are:
  - Slow for high‑traffic services or multi‑hour windows
  - Bound by a maximum entries per chunk limit (for example 100,000 log entries), which can produce partial results.[file:1]

The system instructions prefer Monitoring for “how many requests in the last N hours?” and use Logging only when explicitly requested.[file:1]

---

### Time windows and retention

- Larger windows (24h, 7d) may be more aggregated in Monitoring.
- Logging may not cover all requests for very high‑volume services if log entry caps are reached.
- Internally, timestamps and query windows are handled in UTC; user‑visible times can be presented in a consistent local timezone (for example EST).[file:1]

---

### Read‑only behavior

The Cloud Run expert is strictly read‑only:

- It does not deploy, modify, or delete services.
- It does not change configuration or scaling parameters.

All outputs are descriptive and advisory.[file:1]

---

## Prompt Usage (Summary)

For a detailed prompt library, see [`PROMPTS.md`](./PROMPTS.md).

Common patterns:

- Discovery: “List services”, “Show config for a service”.
- Utilization: “CPU/memory usage for a service”.
- Performance: “Service X is slow – investigate”.
- Traffic & latency: “Total requests and p95 latency over last 3/6 hours”.
- Forensic: “Exact request counts from logs with status code breakdown”.[file:1]

---

---

## Limitations and Usage Guidelines

This section describes how and when to use log‑based vs metrics‑based queries, and what to expect from each approach.[file:1]

### 1. Log‑Based Queries

Log‑based tools (for example, `get_exact_request_counts`, `get_exact_request_counts_from_logs`) operate directly on application and access logs.

**When to use:**

- You need **exact, log‑level counts** for a time window (for example, audits or incident postmortems).  
- You must break down traffic by status code (2xx/4xx/5xx) with maximum precision.  
- You are investigating a small to moderate time window with manageable traffic volume.[file:1]

**How to use them:**

- Phrase prompts explicitly, for example:
  - “Using logs, give me the exact request counts for `my-service` in `region-1` for the last 60 minutes, broken down by status code.”
- Mention that you want “exact counts from logs” or “forensic analysis” so the agent chooses log‑based tools instead of metrics.[file:1]

**Known constraints:**

- **Performance:**  
  - Log scans can take **minutes** for busy services or multi‑hour windows.  
  - Each chunk is limited to a maximum number of log entries (for example, 100,000 entries), and scanning is done page‑by‑page.[file:1]
- **Data completeness:**  
  - If log volume exceeds the per‑chunk limit, the tool may only process the first chunk and annotate results with a note such as “max entries limit reached”, meaning the totals are **partial**.[file:1]
- **Scalability:**  
  - Wide windows (multiple hours) combined with high traffic are not efficient for repeated use.  
  - Avoid asking for large windows (for example, 24 hours) of exact log counts in normal workflows; reserve this for targeted forensic queries.[file:1]

**Guardrails / best practices:**

- Use **shorter time windows** (for example, 15–60 minutes) for log‑based analysis when possible.  
- If a query hits log limits or is slow, narrow the window or switch to metrics‑based summaries.  
- Treat log‑based tools as **opt‑in** and **slow**, and only use them when you truly need log‑level accuracy.[file:1]

---

### 2. Metrics‑Based Signals (Monitoring)

Metrics‑based tools (for example, `get_metrics_summary`, `get_all_utilization_metrics`, `get_request_rate_and_latency_summary`) use Cloud Monitoring time‑series data.

**When to use:**

- You need **fast answers** about:
  - Request counts and rates.  
  - Latency (p95, etc.).  
  - CPU and memory utilization.  
  - Instance count and scaling behavior.  
- You are troubleshooting current or recent performance issues (up to at least the last 6 hours).  
- You want to compare services or regions quickly.[file:1]

**Why use metrics instead of logs:**

- **Performance:**  
  - Metrics queries are designed for aggregation and are significantly **faster** than scanning raw logs.  
  - They scale well for multi‑hour windows and high‑traffic services.[file:1]
- **Scalability:**  
  - Aggregations over long windows (for example, 6 hours) are efficient and do not hit log entry limits.  
- **Clarity:**  
  - Metrics directly expose utilization, rates, and percentiles, making it easier to diagnose resource or scaling issues.[file:1]

**Data characteristics and completeness:**

- Metrics are **aggregated** and may be subject to sampling or roll‑ups, so values are approximate rather than exact per‑request counts.  
- For operational decision‑making (for example, “Is this service overloaded?”), this approximation is usually sufficient and preferred.  
- For strict audits where every request must be counted exactly, prefer log‑based tools with the constraints noted above.[file:1]

**Guardrails / best practices:**

- For prompts like “How many requests in the last N hours?” or “What is p95 latency over the last 6 hours?”, default to metrics‑based wording and let the agent use Monitoring.  
- Use metrics for:
  - “Is the service healthy?”  
  - “Is it CPU‑ or memory‑bound?”  
  - “Is it hitting max instances or concurrency limits?”  
  - “What are the traffic patterns over the last few hours?”[file:1]
- Only override this and ask for logs when you explicitly need exact counts.[file:1]

---

### 3. Performance, Scalability, and Data Completeness Summary

| Aspect                     | Metrics‑based tools                          | Log‑based tools                                  |
|----------------------------|----------------------------------------------|--------------------------------------------------|
| Data source                | Cloud Monitoring                             | Cloud Logging                                    |
| Typical use cases          | Health checks, performance triage, trends    | Forensic audits, strict exact counts             |
| Accuracy                   | Aggregated / approximate                     | Per‑entry, exact per log record                  |
| Latency / speed            | Fast (seconds)                               | Slow (can be minutes for large windows)          |
| Scalability (high traffic) | High – designed for aggregation              | Limited – bounded by per‑chunk log entry limits  |
| Time window suitability    | Up to at least 6 hours (often longer)        | Shorter, focused windows recommended             |
| Risk of partial data       | Low (aggregation‑based)                      | Higher – chunk limits can truncate log coverage  |

**User guidelines:**

- Use metrics‑based prompts by default for operational questions and performance triage.  
- Use log‑based prompts selectively, with explicit wording, when you accept longer runtimes and possible limits in exchange for log‑level precision.  
- When interpreting results:
  - Treat Monitoring results as **high‑confidence trends and indicators**.  
  - Treat Logging results as **precise but potentially partial**, especially when you see notes about entry limits or truncated ranges.[file:1]

---
