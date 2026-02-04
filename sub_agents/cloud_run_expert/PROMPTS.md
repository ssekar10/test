# Cloud Run Expert Prompt Library

This file provides example prompts for end users interacting with the Cloud Run expert via the master agent. Replace placeholders like `my-service` and `region-1` with actual names in your environment.[file:1]

---

## 1. Service Discovery & Configuration

**Goals:** Understand what services exist and how they are configured.

Example prompts:

- “List all Cloud Run services in `region-1`.”
- “List all Cloud Run services in `region-2` and show their basic configuration.”
- “Show the full configuration for the `my-service` Cloud Run service in `region-1`.”
- “For `my-service` in `region-1`, what are the min instances, max instances, and concurrency settings?”
- “Which Cloud Run services in `region-1` have low max instances or very high concurrency values?”

---

## 2. Resource Utilization (CPU, Memory, Instances)

**Goals:** Check whether services are under‑ or over‑utilized and how they are scaling.

Example prompts:

- “Show CPU and memory utilization for `my-service` in `region-1` over the last 1 hour.”
- “Is `my-service` in `region-2` CPU‑bound or memory‑bound over the last 4 hours?”
- “How many instances did `my-service` use in `region-1` in the last 2 hours, and what is its configured max instances?”
- “For all Cloud Run services in `region-1`, show average CPU utilization over the last 1 hour.”

---

## 3. Performance Triage – ‘Service is slow’

**Goals:** Quickly determine whether the problem is with the Cloud Run service itself or downstream dependencies.

Example prompts:

- “The `my-service` Cloud Run service in `region-1` is slow. Check if the issue is with the service or a downstream dependency.”
- “Investigate performance issues for `my-service` in `region-2` over the last hour.”
- “Is `my-service` in `region-1` hitting resource limits or scaling caps?”
- “For `my-service` in `region-1`, correlate CPU, memory, request rate, and latency over the last 2 hours and tell me where the bottleneck is.”

Expected behavior:

- The agent uses fast Monitoring‑based metrics (`get_all_utilization_metrics`, `get_request_rate_and_latency_summary`) to inspect:
  - CPU and memory utilization
  - Instance count vs max instances
  - Request volume and p95 latency
- If the service appears healthy with low utilization and stable instances, the agent suggests investigating downstream services, databases, or APIs.[file:1]

---

## 4. Request Counts & Latency (Fast, Monitoring‑Based)

**Goals:** Get total requests, request rate, and p95 latency over a time window, without expensive log scans.

Example prompts:

- “Total number of requests for `my-service` in `region-1` for the last 3 hours.”
- “What is the average request rate and p95 latency for `my-service` in `region-2` over the last 6 hours?”
- “Compare request rate and p95 latency for `my-service` between `region-1` and `region-2` for the last 2 hours.”
- “Show total requests and p95 latency for all Cloud Run services in `region-1` for the last 1 hour.”

Expected behavior:

- The agent uses Monitoring‑based tools, such as `get_request_rate_and_latency_summary`, to compute:
  - `total_requests`
  - `avg_requests_per_minute`
  - `max_requests_per_minute`
  - p95 latency statistics (current, average, min, max).[file:1]
- These responses are optimized for windows up to at least 6 hours and do not use Cloud Logging.[file:1]

---

## 5. Exact Request Counts from Logs (Slow, Forensic)

**Goals:** Obtain precise, log‑level request counts, usually for audits or incident analysis.

Example prompts:

- “From Cloud Logging, give me the exact number of requests for `my-service` in `region-1` for the last 1 hour, broken down by status code.”
- “Using logs, get exact request counts and error counts for `my-service` in `region-2` over the last 2 hours.”
- “Perform a forensic analysis of request volume and failures for `my-service` in `region-1` for the last 30 minutes using Cloud Logging only.”
- “Use logs to compute exact 2xx, 4xx, and 5xx counts for `my-service` in `region-1` for the last 90 minutes.”

Expected behavior:

- The agent warns that log‑based analysis may be slow and may be limited by log entry caps (for example, 100,000 entries per chunk).
- It then uses log‑based tools (`get_exact_request_counts`, `get_exact_request_counts_from_logs`) to return:
  - Total requests
  - Status‑code breakdowns
  - Notes if results are partial due to caps.[file:1]

---

## 6. Multi‑Service & Multi‑Region Views

**Goals:** Understand behavior across multiple services and regions.

Example prompts:

- “Summarize CPU utilization and request volume for all Cloud Run services in `region-1` for the last 1 hour.”
- “Which Cloud Run services are receiving the most traffic in `region-2` over the last 6 hours?”
- “For all services in `region-1` and `region-2`, show which ones have the highest p95 latency in the last 2 hours.”
- “Identify any services in `region-1` that are consistently near their max instances over the last 3 hours.”

Expected behavior:

- The agent uses multi‑service/multi‑region Monitoring queries (`query_all_services_metrics_summary`, `get_all_utilization_metrics` in loops, etc.) and returns aggregated views, highlighting outliers and potential problem services.[file:1]

---

## 7. Best Practices for Prompting

- Be explicit about:
  - Service name(s)
  - Region(s)
  - Time window (for example, “last 3 hours”, “last 24 hours”)
- For most operational questions, let the agent use **fast Monitoring‑based tools**.
- Reserve **log‑based exact counts** for cases where you explicitly need forensic accuracy from Cloud Logging and can tolerate longer response times.
- Ask for explanations: instead of only “how many?”, consider:
  - “Explain whether this service is resource‑constrained or waiting on downstream dependencies.”
  - “Summarize the key performance findings and recommended next steps.”

---
