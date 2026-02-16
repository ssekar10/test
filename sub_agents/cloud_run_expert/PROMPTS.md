# Cloud Run Expert Prompt Library

This file provides example prompts for end users interacting with the Cloud Run expert via the master agent. Replace placeholders like `my-service` and `region-1` with actual names in your environment.

---

## Architecture Overview

This sub-agent is organized into **two main sections**:

1. **Section 1: REST API & Monitoring API Tools** - Service discovery, configuration retrieval, and real-time metrics via APIs
2. **Section 2: Analytics & Supporting Content** - Log-based forensics, workflows, and best practices

---

# SECTION 1: REST API & MONITORING API PROMPTS

## Overview

Section 1 prompts cover API-based tools for:
- **REST API**: Service discovery and configuration
- **Monitoring API**: Real-time metrics (CPU, memory, requests, latency)

These prompts generate fast responses (seconds) and are ideal for operational queries.

---

## 1.1 REST API Prompts - Service Discovery & Configuration

### List Services

**Goals:** Understand what services exist and where they are deployed.

Example prompts:

- "List all Cloud Run services in `region-1`."
- "List all Cloud Run services in `region-2` and show their basic configuration."
- "Show me all Cloud Run services with label env:production."
- "Which Cloud Run services exist in the project?"

**Expected behavior:**
- Agent uses `list_services` (Cloud Asset API)
- Returns service names, locations, labels, state
- Fast response (seconds)

---

### Get Service Configuration

**Goals:** Retrieve detailed configuration for specific services.

Example prompts:

- "Show the full configuration for the `my-service` Cloud Run service in `region-1`."
- "For `my-service` in `region-1`, what are the min instances, max instances, and concurrency settings?"
- "Which image is `my-service` running in `region-2`?"
- "What are the environment variables for `my-service`?"

**Expected behavior:**
- Agent uses `get_service_details` or `get_service_details_fast` (Cloud Run API)
- Returns:
  - Service URL, ingress
  - Latest revision
  - Scaling: min/max instances
  - Container: image, CPU, memory, env vars
  - Created/updated timestamps (EST)

---

### Configuration Comparison

**Goals:** Compare configuration across regions or services.

Example prompts:

- "Compare scaling settings for `my-service` in `region-1` vs `region-2`."
- "Show `my-service` configuration across all regions."
- "Which Cloud Run services in `region-1` have low max instances or very high concurrency values?"

**Expected behavior:**
- Agent uses `get_service_all_regions` for multi-region queries
- Presents comparison in table format
- Highlights differences

---

## 1.2 Monitoring API Prompts - Real-Time Metrics

### Resource Utilization (CPU, Memory, Instances)

**Goals:** Check whether services are under- or over-utilized and how they are scaling.

Example prompts:

- "Show CPU and memory utilization for `my-service` in `region-1` over the last 1 hour."
- "Is `my-service` in `region-2` CPU-bound or memory-bound over the last 4 hours?"
- "How many instances did `my-service` use in `region-1` in the last 2 hours, and what is its configured max instances?"
- "For all Cloud Run services in `region-1`, show average CPU utilization over the last 1 hour."

**Expected behavior:**
- Agent uses `get_resource_utilization` or `get_all_utilization_metrics`
- Returns CPU/memory percentages (current, avg, max, min)
- Compares instance count to configured max instances

---

### Performance Triage – 'Service is slow'

**Goals:** Quickly determine whether the problem is with the Cloud Run service itself or downstream dependencies.

Example prompts:

- "The `my-service` Cloud Run service in `region-1` is slow. Check if the issue is with the service or a downstream dependency."
- "Investigate performance issues for `my-service` in `region-2` over the last hour."
- "Is `my-service` in `region-1` hitting resource limits or scaling caps?"
- "For `my-service` in `region-1`, correlate CPU, memory, request rate, and latency over the last 2 hours and tell me where the bottleneck is."

Expected behavior:

- The agent uses fast Monitoring API metrics (`get_all_utilization_metrics`, `get_request_rate_and_latency_summary`) to inspect:
  - CPU and memory utilization
  - Instance count vs max instances
  - Request volume and p95 latency
- If the service appears healthy with low utilization and stable instances, the agent suggests investigating downstream services, databases, or APIs.

---

### Request Counts & Latency (Fast, Monitoring API)

**Goals:** Get total requests, request rate, and p95 latency over a time window, without expensive log scans.

Example prompts:

- "Total number of requests for `my-service` in `region-1` for the last 3 hours."
- "What is the average request rate and p95 latency for `my-service` in `region-2` over the last 6 hours?"
- "Compare request rate and p95 latency for `my-service` between `region-1` and `region-2` for the last 2 hours."
- "Show total requests and p95 latency for all Cloud Run services in `region-1` for the last 1 hour."

Expected behavior:

- The agent uses Monitoring API tools, such as `get_request_rate_and_latency_summary`, to compute:
  - `total_requests`
  - `avg_requests_per_minute`
  - `max_requests_per_minute`
  - p95 latency statistics (current, average, min, max).
- These responses are optimized for windows up to at least 6 hours and do not use Cloud Logging.

---

### Multi-Service & Multi-Region Views

**Goals:** Understand behavior across multiple services and regions.

Example prompts:

- "Summarize CPU utilization and request volume for all Cloud Run services in `region-1` for the last 1 hour."
- "Which Cloud Run services are receiving the most traffic in `region-2` over the last 6 hours?"
- "For all services in `region-1` and `region-2`, show which ones have the highest p95 latency in the last 2 hours."
- "Identify any services in `region-1` that are consistently near their max instances over the last 3 hours."

Expected behavior:

- The agent uses multi-service/multi-region Monitoring API queries (`query_all_services_metrics_summary`, `get_all_utilization_metrics` in loops, etc.) and returns aggregated views, highlighting outliers and potential problem services.

---

## Section 1 Summary

**REST API Prompts:**
- Service discovery and listing
- Configuration retrieval and comparison
- Multi-region queries

**Monitoring API Prompts:**
- Real-time metrics (CPU, memory, instances)
- Request counts and latency (p95)
- Performance triage workflows

**Key Characteristics:**
- Fast response times (seconds)
- API-based (not log scanning)
- Ideal for operational queries (1-6 hour windows)

---

# SECTION 2: ANALYTICS & SUPPORTING CONTENT

## Overview

Section 2 covers log-based forensic analysis, workflows, best practices, and troubleshooting guidelines.

---

## 2.1 Forensic Analysis (Cloud Logging)

### Exact Request Counts from Logs (Slow, Forensic)

**Goals:** Obtain precise, log-level request counts, usually for audits or incident analysis.

Example prompts:

- "From Cloud Logging, give me the exact number of requests for `my-service` in `region-1` for the last 1 hour, broken down by status code."
- "Using logs, get exact request counts and error counts for `my-service` in `region-2` over the last 2 hours."
- "Perform a forensic analysis of request volume and failures for `my-service` in `region-1` for the last 30 minutes using Cloud Logging only."
- "Use logs to compute exact 2xx, 4xx, and 5xx counts for `my-service` in `region-1` for the last 90 minutes."

Expected behavior:

- The agent warns that log-based analysis may be slow and may be limited by log entry caps (e.g., 100,000 entries per chunk).
- It then uses log-based tools (`get_exact_request_counts`, `get_exact_request_counts_from_logs`) to return:
  - Total requests
  - Status-code breakdowns (2xx, 4xx, 5xx)
  - Notes if results are partial due to caps.

**Important:**
- For windows >24 hours, chunking is automatic
- Expect slower response times (minutes)
- Reserve for cases requiring exact accuracy

---

## 2.2 Best Practices for Prompting

### Be Explicit About:

- **Service name(s)** - Use exact names
- **Region(s)** - Specify regions (e.g., us-central1, us-east1)
- **Time window** - "last 3 hours", "last 24 hours"
- **Intent** - REST API vs Monitoring API vs Log-based query

### Section 1 Keywords:

**REST API:**
- "list", "show config", "configuration", "settings"
- "scaling", "instances", "image", "env vars"
- "discover", "what services"

**Monitoring API:**
- "CPU", "memory", "utilization", "slow", "latency"
- "requests", "traffic", "p95", "performance"

### Section 2 Keywords:

- "exact counts", "from logs", "forensic"
- "status code breakdown", "2xx/4xx/5xx"

---

## 2.3 API vs Log-Based Queries

### When Agent Uses API Tools (Section 1):

"List services" → `list_services` (Cloud Asset API)  
"Show config" → `get_service_details` (Cloud Run API)  
"Service X is slow" → `get_all_utilization_metrics` (Monitoring API)  
"Request count" → `get_request_rate_and_latency_summary` (Monitoring API)

### When Agent Uses Log-Based Tools (Section 2):

"Exact counts from logs" → `get_exact_request_counts` (Cloud Logging)

---

## 2.4 Performance Guidelines

### Fast Queries (Seconds) - Section 1
- List services (Cloud Asset API)
- Get service configuration (Cloud Run API, cached)
- Monitoring API metrics (1-6 hour windows)

### Slower Queries (Minutes) - Section 2
- Exact log counts (especially >2 hours)
- Multi-service utilization (10+ services)
- Large time windows (24+ hours with logs)

---

## 2.5 Common Workflows

### Workflow 1: Performance Triage

```
Step 1: "Service X is slow in region-1" 
→ get_all_utilization_metrics (CPU, memory, instances)

Step 2: "Show request rate and latency for service X"
→ get_request_rate_and_latency_summary (traffic + p95)

Step 3: "Show config for service X"
→ get_service_details (max instances, concurrency)

Step 4: Diagnosis
→ "Service is CPU-bound, increase CPU allocation"
→ "Service hitting max instances, increase max_instances"
→ "Service healthy, investigate downstream dependencies"
```

---

### Workflow 2: Traffic Analysis

```
Step 1: "Which services have the most traffic?"
→ query_all_services_metrics_summary (request_count)

Step 2: "Show p95 latency for top 5 services"
→ get_request_rate_and_latency_summary (for each)

Step 3 (if issues found): "Exact request counts from logs for service X"
→ get_exact_request_counts (2xx/4xx/5xx breakdown)
```

---

### Workflow 3: Configuration Audit

```
Step 1: "List all Cloud Run services"
→ list_services

Step 2: "Show config for service X, Y, Z"
→ get_service_details (for each)

Step 3: "Which services have max_instances < 10?"
→ Agent filters results and presents list
```

---

## 2.6 Limitations and Usage Guidelines

### Log-Based Queries (Section 2.1)

**When to use:**
- You need **exact, log-level counts** for audits or incident postmortems
- You must break down traffic by status code (2xx/4xx/5xx) with maximum precision
- You are investigating a small to moderate time window with manageable traffic volume

**How to use them:**
- Phrase prompts explicitly:
  - "Using logs, give me the exact request counts for `my-service` in `region-1` for the last 60 minutes, broken down by status code."
- Mention "exact counts from logs" or "forensic analysis"

**Known constraints:**
- **Performance:** Log scans can take **minutes** for busy services or multi-hour windows
- **Data completeness:** If log volume exceeds per-chunk limit, results may be partial
- **Scalability:** Wide windows (multiple hours) + high traffic = not efficient for repeated use

**Guardrails:**
- Use **shorter time windows** (15–60 minutes) when possible
- If query hits log limits or is slow, narrow the window or switch to Monitoring API
- Treat log-based tools as **opt-in** and **slow**

---

### API-Based Queries (Section 1)

**When to use:**
- You need **fast answers** about services, configuration, or metrics
- You are troubleshooting current or recent issues (up to 6 hours)
- You want to compare services or regions quickly

**Why use APIs instead of logs:**
- **Performance:** Significantly faster than scanning raw logs
- **Scalability:** Scales well for multi-hour windows and high-traffic services
- **Clarity:** Directly exposes configuration, utilization, rates, and percentiles

**Data characteristics:**
- REST API: Authoritative configuration data
- Monitoring API: Aggregated metrics (may be approximate)
- For operational decision-making, this is usually sufficient

**Guardrails:**
- Default to API tools for:
  - "What services exist?"
  - "Show me config/settings"
  - "Is the service healthy?"
  - "Is it CPU- or memory-bound?"
  - "What are traffic patterns?"

---

## 2.7 Summary Table

| Query Type | Section | Tool Example | Data Source | Speed | Use Case |
|------------|---------|--------------|-------------|-------|----------|
| List services | 1.1 | `list_services` | Cloud Asset API | Fast | Discovery |
| Service config | 1.1 | `get_service_details` | Cloud Run API | Fast | Configuration audit |
| Multi-region config | 1.1 | `get_service_all_regions` | Cloud Run API | Fast | Cross-region comparison |
| CPU/Memory utilization | 1.2 | `get_resource_utilization` | Monitoring API | Fast | Performance triage |
| Request rate + latency | 1.2 | `get_request_rate_and_latency_summary` | Monitoring API | Fast | Traffic analysis |
| Exact log counts | 2.1 | `get_exact_request_counts` | Cloud Logging | Slow | Forensic audit |

---

## 2.8 Ask for Explanations

Instead of only "how many?", consider:

- "Explain whether this service is resource-constrained or waiting on downstream dependencies."
- "Summarize the key performance findings and recommended next steps."
- "Is this service healthy? What should I investigate?"

---
