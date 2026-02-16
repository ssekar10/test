# Cloud Run Expert Sub‑Agent

The Cloud Run expert is a read‑only sub‑agent focused on observing, diagnosing, and explaining Cloud Run services in a GCP project. It uses Cloud Monitoring, Cloud Logging, and Cloud Run service configuration to support SRE and developer workflows.

---

## Architecture Overview

This sub-agent is organized into **two main sections**:

1. **Section 1: REST API & Monitoring API Tools** - Service discovery, configuration retrieval, and real-time metrics via APIs
2. **Section 2: Analytics & Supporting Content** - Log-based forensics, workflows, and best practices

---

# SECTION 1: REST API & MONITORING API TOOLS

## Overview

Section 1 contains all API-based tools that provide fast, real-time access to:
- **Cloud Run API**: Service discovery and configuration
- **Cloud Asset API**: Multi-service inventory
- **Cloud Monitoring API**: Real-time metrics (CPU, memory, requests, latency)

These tools are optimized for operational queries and provide sub-second to few-second response times.

---

## 1.1 REST API Tools - Service Discovery & Configuration

### Purpose
Discover and retrieve configuration for Cloud Run services using Cloud Asset API and Cloud Run API.

### Service Discovery (Cloud Asset API)

#### `list_services`
List all Cloud Run services in the project.

**Parameters:**
- `region` - Optional region filter
- `label_filter` - Optional label filter (e.g., "env:prod")

**Returns:**
- Total service count
- Per-service info:
  - name, location, full_name
  - display_name, labels, state

**Use Cases:**
- "List all Cloud Run services"
- "Show services in us-central1"
- "List services with label env:production"

---

### Service Configuration (Cloud Run API)

#### `get_service_details`
Get detailed configuration for a specific Cloud Run service.

**Parameters:**
- `service_name` - Service name
- `region` - Region

**Returns:**
- Service URL, ingress settings
- Latest revision name
- Scaling: min_instances, max_instances
- Containers:
  - Image URI
  - CPU limit, memory limit
  - Environment variables
- Created/updated timestamps (EST)

**Use Cases:**
- "Show config for service X"
- "What are the scaling settings for service Y?"
- "Which image is service Z running?"

---

#### `get_service_details_fast`
Get service configuration with caching (5min TTL). Faster for repeated queries of the same service.

**Parameters:**
- `service_name` - Service name
- `region` - Region (default: us-central1)

**Cache Benefits:**
- 5-minute cache TTL
- ~85% cache hit ratio for repeated queries
- Reduces API calls and latency

---

#### `get_service_all_regions`
Get service configuration from all common regions in parallel. Much faster than sequential queries.

**Parameters:**
- `service_name` - Service name

**Returns:**
- Configurations from multiple regions
- Only includes regions where service exists

**Common Regions:**
- us-central1, us-east1, us-west1
- europe-west1, asia-southeast1

**Use Cases:**
- "Show service X config across all regions"
- "Is service Y deployed in multiple regions?"

---

### Configuration Caching

The sub-agent implements a caching layer (config.py) for performance:

**Cache Settings:**
- TTL: 5 minutes
- Functions: `get_cached_config()`, `set_cached_config()`
- Cache keys: `{service_name}_{region}`

**Cache Benefits:**
- Reduces API latency for repeated queries
- Prevents rate limiting
- Improves user experience

---

## 1.2 Monitoring API Tools - Real-Time Metrics

### Purpose
Fast metrics using Cloud Monitoring API for operational queries:
- Request count over a time window
- Request rate (per minute / per second)
- Latency percentiles (e.g., p95) from distribution metrics
- CPU utilization (percentage)
- Memory utilization (percentage)
- Instance count over time

### Key Functions

#### `get_metrics_summary`
Query metrics from Cloud Monitoring (fast, approximate).

**Parameters:**
- `metric_type` - "request_count" or "instance_count"
- `region` - Optional region filter
- `hours` - Time window (default 1)
- `limit` - Max services to return (default 100)

**Use Cases:**
- "Show request counts for all services in the last hour"
- "Which services have the most traffic?"

---

#### `query_all_services_metrics_summary`
Internal method called by `get_metrics_summary`.

**Returns:**
- For `request_count`: total_requests, avg/max requests_per_sec
- For `instance_count`: avg_instances, max_instances

---

#### `get_resource_utilization`
Get actual CPU and memory utilization for a specific Cloud Run service.

**Parameters:**
- `service_name` - Service name
- `region` - Region (e.g., us-central1)
- `hours` - Time window (default 1)

**Returns:**
- CPU utilization: current, average, max, min (%)
- Memory utilization: current, average, max, min (%)
- Datapoints count per metric

**Use Cases:**
- "Is service X CPU-bound or memory-bound?"
- "Show CPU/memory usage for service Y"

---

#### `get_all_utilization_metrics`
Comprehensive utilization metrics for a Cloud Run service including:
- CPU utilization (current, avg, max, min)
- Memory utilization (current, avg, max, min)
- Instance count (avg, max)
- Configuration limits (CPU, memory, scaling)

**Parameters:**
- `service_name` - Service name
- `region` - Region
- `hours` - Time window (default 1)

**This provides a complete view of service resource usage and capacity.**

**Use Cases:**
- "Service X is slow - investigate"
- "Is service Y hitting scaling limits?"
- "Show complete resource profile for service Z"

---

#### `get_request_rate_and_latency_summary`
Fast request counts + latency (p95) from Cloud Monitoring (no log scanning).

**Parameters:**
- `service_name` - Optional service filter
- `region` - Optional region filter
- `hours` - Time window (default 6)

**Returns:**
- Total requests
- Avg/max requests per minute
- Latency p95: current_ms, average_ms, max_ms, min_ms
- Datapoints count

**Optimized for windows up to at least 6 hours.**

**Use Cases:**
- "Total requests and p95 latency for service X, last 3 hours"
- "What's the request rate for all services?"

---

## Section 1 Summary

**REST API Tools:**
- Service discovery via Cloud Asset API
- Configuration retrieval via Cloud Run API
- Caching layer for performance
- Multi-region parallel queries

**Monitoring API Tools:**
- Real-time metrics from Cloud Monitoring
- CPU, memory, instance utilization
- Request counts and latency (p95)
- Fast operational queries (seconds)

**Key Characteristics:**
- API-based (not log scanning)
- Fast response times (sub-second to few seconds)
- Ideal for real-time monitoring and troubleshooting
- Suitable for 1-6 hour time windows

---

# SECTION 2: ANALYTICS & SUPPORTING CONTENT

## Overview

Section 2 contains log-based forensic analysis, performance workflows, and operational best practices.

---

## 2.1 Forensic Analysis (Cloud Logging)

### Purpose
Exact, log-level request counts for audits and incident analysis. Slower but 100% accurate.

### Key Functions

#### `get_exact_request_counts`
Get EXACT request counts from Cloud Logging (100% accurate). Supports large time windows up to 7 days (168 hours) with automatic chunking.

**Parameters:**
- `region` - Optional region filter
- `hours` - Time window (default 1, max 168)
- `limit` - Max services to return (default 100)

**Returns:**
- Total log entries analyzed
- Per-service breakdown:
  - total_requests
  - status_2xx, status_4xx, status_5xx counts

**Chunking for Large Windows:**
- Automatically splits queries >24 hours into 6-hour chunks
- Rate-limited to prevent quota exhaustion
- Shows progress: "Processing chunk 3/7"

**Use Cases:**
- "Using logs, get exact request counts for service X, last 2 hours"
- "Exact 2xx/4xx/5xx breakdown from Cloud Logging"
- "Forensic analysis of request volume"

**Performance:**
- Small windows (1-2 hours): seconds to minutes
- Large windows (24+ hours): minutes (with chunking)

---

## 2.2 Performance Triage Workflow

### "Service is slow" Investigation

When a user reports that a service is slow, the agent follows this workflow:

1. **Symptom check (fast)**  
   Calls `get_all_utilization_metrics(service_name, region, 1)` to inspect CPU, memory, instance count, and config for the last hour.

2. **Traffic check (fast)**  
   Uses Monitoring-based tools (e.g., `get_request_rate_and_latency_summary`) to understand request volume and latency without scanning logs.

3. **Scaling check**  
   Compares current/peak instance count to configured max instances and considers concurrency settings.

4. **Correlation and diagnosis**  
   Determines whether the service itself is overloaded or likely waiting on downstream dependencies.

5. **Recommendations**  
   Suggests concrete next steps, such as updating max instances, adjusting concurrency, or investigating downstream services/databases.

**By default, this workflow does not use log-based exact counting unless explicitly requested.**

---

## 2.3 Monitoring vs Logging: When to Use Each

### Use Monitoring API Tools (Section 1) When:
- You need **fast answers** (seconds)
- You're troubleshooting current or recent performance issues (up to 6 hours)
- You want to compare services or regions quickly
- Approximate metrics are sufficient for operational decision-making

### Use Logging-Based Tools (Section 2) When:
- You need **exact, log-level counts** for audits or postmortems
- You must break down traffic by status code (2xx/4xx/5xx) with maximum precision
- You accept longer runtimes (minutes) in exchange for accuracy

### Performance Comparison

| Aspect | API-based tools (Section 1) | Log-based tools (Section 2) |
|--------|------------------------------|------------------------------|
| Data source | Cloud Monitoring API + Cloud Run API | Cloud Logging |
| Typical use cases | Health checks, performance triage, trends | Forensic audits, strict exact counts |
| Accuracy | Aggregated / approximate | Per-entry, exact per log record |
| Latency / speed | Fast (seconds) | Slow (can be minutes for large windows) |
| Scalability (high traffic) | High – designed for aggregation | Limited – bounded by per-chunk log entry limits |
| Time window suitability | Up to at least 6 hours (often longer) | Shorter, focused windows recommended |
| Risk of partial data | Low (aggregation-based) | Higher – chunk limits can truncate log coverage |

---

## 2.4 Multi-Region and Multi-Service Views

The agent supports:
- Parallel queries across regions
- Aggregated or per-service metric summaries across multiple services
- Chunked log queries over longer windows (up to several days), with rate limiting and entry caps

This enables higher-level views such as "top services by traffic" or "services with highest latency per region".

---

## 2.5 Read-Only Behavior

The Cloud Run expert is strictly read-only:
- It does not deploy, modify, or delete services
- It does not change configuration or scaling parameters

All outputs are descriptive and advisory.

---

## 2.6 Time Windows and Retention

- Larger windows (24h, 7d) may be more aggregated in Monitoring
- Logging may not cover all requests for very high-volume services if log entry caps are reached
- Internally, timestamps and query windows are handled in UTC; user-visible times are presented in EST

---

## 2.7 Prompt Usage (Summary)

For a detailed prompt library, see [`PROMPTS.md`](./PROMPTS.md).

Common patterns:

**Section 1: REST API & Monitoring API**
- Discovery: "List services", "Show services in region X"
- Configuration: "Show config for service X", "What are the scaling settings?"
- Utilization: "CPU/memory usage for a service"
- Performance: "Service X is slow – investigate"
- Traffic & latency: "Total requests and p95 latency over last 3/6 hours"

**Section 2: Analytics & Forensics**
- Forensic: "Exact request counts from logs with status code breakdown"

---

## 2.8 Known Limitations

### Monitoring API vs Logging

- Monitoring API tools (Section 1) are:
  - Fast
  - Suitable for up to 6-hour windows (and beyond, with more aggregation)
  - Slightly approximate due to aggregation/sampling

- Logging-based tools (Section 2) are:
  - Slow for high-traffic services or multi-hour windows
  - Bound by a maximum entries per chunk limit (e.g., 100,000 log entries), which can produce partial results

The system instructions prefer Monitoring API for "how many requests in the last N hours?" and use Logging only when explicitly requested.

---
