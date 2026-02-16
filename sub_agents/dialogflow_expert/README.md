# Dialogflow CX Expert Sub-Agent

**Version:** 2.0.0  
**Status:** Production Ready  
**Last Updated:** February 16, 2026

A production-grade Dialogflow CX specialist agent for operational analytics, configuration auditing, and conversation intelligence within a multi-agent GCP operations platform.

---

## 🎯 Overview

The Dialogflow Expert provides comprehensive monitoring and troubleshooting capabilities for Dialogflow CX agents through:

- **Configuration Auditing**: Agent discovery, intent inspection, webhook mapping
- **Real-time Analytics**: Session metrics, backend performance, failure analysis
- **Conversation Intelligence**: Turn-by-turn transcripts, NLU quality analysis, flow traversal
- **Session Forensics**: Deep-dive investigation with BigQuery-backed analytics

---

## 🏗️ Architecture

This sub-agent is organized into **two main sections**:

1. **Section 1: REST API Tools** (6 tools) - All Dialogflow CX API-based discovery and configuration
2. **Section 2: BigQuery Analytics Tools & Supporting Content** (26 tools) - All BigQuery-based metrics, session analytics, conversation intelligence, plus workflows and best practices

### Component Structure

```
sub_agents/dialogflow_expert/
├── agent.py           # Agent definition with system instructions
├── tools.py           # 32 total tools (6 REST API + 26 BigQuery)
├── queries.py         # BigQuery SQL templates
├── config.py          # Caching layer (5min TTL)
└── README.md          # This file
```

### Data Sources

| Section | Data Source | Tables | Purpose |
|---------|-------------|--------|----------|
| Section 1 | Dialogflow CX API | N/A | Agent, intent, webhook configuration |
| Section 2 | BigQuery | `alerting_monitoring.dialogflow_metrics` | Real-time operational analytics |
| Section 2 | BigQuery | `dfcx_analytics.dfcx_session_metadata` | CCAIP integration, caller info, outcomes |
| Section 2 | BigQuery | `dfcx_analytics.dfcx_transcript` | Conversation replay, NLU analysis |

---

# SECTION 1: REST API TOOLS - DISCOVERY & CONFIGURATION (6 TOOLS)

## Overview

All REST API tools use Dialogflow CX API for:
- Agent discovery and configuration
- Intent listing and inspection
- Webhook configuration

**Data Sources:** Dialogflow CX API only  
**Total Tools:** 6  
**Response Time:** Sub-second to 2 seconds (with caching)

---

## 1.1 Agent Discovery & Configuration - 3 Tools

### Purpose
Discover and inspect Dialogflow CX agents across locations.

### Agent Discovery

#### `list_dialogflow_agents(location)`
List Dialogflow agents in a specific location.

**Parameters:**
- `location` - Optional location (default: project default)
  - Supported: us, global, us-central1, us-east1, europe-west1, asia-southeast1

**Returns:**
- Agent count
- Agent names, IDs, resource names
- Default languages
- Time zones

**Use Cases:**
- "List all Dialogflow agents"
- "Show me agents in the us region"
- "Which Dialogflow agents are in us-central1?"

**Error Handling:**
- `PERMISSION_DENIED` - Missing Dialogflow API Reader role
- `API has not been used` - Dialogflow CX API not enabled
- `NOT_FOUND` / `UNIMPLEMENTED` - Invalid location

---

### Agent Configuration

#### `get_agent_configuration(agent_id, location)`
Get detailed configuration for a Dialogflow agent (no cache).

**Parameters:**
- `agent_id` - Agent display name or full resource name
- `location` - Optional location (default: project default)

**Returns:**
- Display name, resource name, agent ID
- Default language, supported languages
- Time zone
- Description, avatar URI
- Stackdriver logging enabled
- Spell correction enabled
- Query time (EST)

**Use Cases:**
- "Show me configuration for XA Agent"
- "Get details for DR-agent"
- "What is the time zone for RobTest agent?"

---

#### `get_agent_configuration_cached(agent_id, location)`
Get agent configuration with caching (5min TTL). Faster for repeated queries.

**Parameters:**
- `agent_id` - Agent display name or full resource name
- `location` - Optional location (default: project default)

**Cache Benefits:**
- 5-minute cache TTL
- ~85% cache hit ratio for repeated queries
- Reduces API calls and latency

**Use Cases:**
- Same as `get_agent_configuration` but faster for repeated queries
- Automatically used by agent when appropriate

---

## 1.2 Intent Management - 2 Tools

### Purpose
List and inspect intents for Dialogflow CX agents.

#### `list_intents(agent_id, location)`
List all intents for an agent (cached 5min).

**Parameters:**
- `agent_id` - Agent display name or full resource name
- `location` - Optional location (default: project default)

**Returns:**
- Intent count
- Intent IDs, display names, resource names
- Training phrase counts
- Parameter lists
- Query time (EST)

**Use Cases:**
- "List all intents for XA Agent"
- "Show me intents in DR-agent"
- "How many intents does RobTest have?"

---

#### `get_intent_details(agent_id, intent_id, location)`
Get detailed information for a single intent including training phrases.

**Parameters:**
- `agent_id` - Agent display name or full resource name
- `intent_id` - Intent display name or ID
- `location` - Optional location (default: project default)

**Returns:**
- Intent ID, display name, resource name
- Full list of training phrases
- Training phrase count
- Parameter definitions (entity types, is_list, redact)
- Parameter count
- Labels
- Query time (EST)

**Use Cases:**
- "Show me training phrases for the 'order-status' intent"
- "Get details for 'troubleshoot.internet' intent in XA Agent"
- "What parameters does the 'billing' intent have?"

---

## 1.3 Webhook Configuration - 1 Tool

### Purpose
List and inspect webhook configurations for Dialogflow CX agents.

#### `list_webhooks(agent_id, location)`
List configured webhooks for an agent (cached 5min).

**Parameters:**
- `agent_id` - Agent display name or full resource name
- `location` - Optional location (default: project default)

**Returns:**
- Webhook count
- Webhook IDs, display names, resource names
- URI (Generic Web Service)
- Timeout settings (seconds)
- Request headers (if configured)
- Service Directory config (if applicable)
- Disabled status
- Query time (EST)
- Note: "For webhook performance metrics, if webhook is Cloud Run-based, use the Cloud Run specialist."

**Use Cases:**
- "What webhooks does XA Agent have?"
- "Show webhook configuration for DR-agent"
- "Which webhooks are configured for RobTest?"

**Delegation:**
- For webhook **infrastructure metrics** (CPU, memory, instance count, latency p95, error rates), delegate to Cloud Run specialist
- This tool provides **configuration only** (URI, timeout, headers)

---

## Section 1 Summary

**Total Tools: 6**
- 3 tools: Agent discovery & configuration
- 2 tools: Intent management
- 1 tool: Webhook configuration

**Data Source:** Dialogflow CX API only  
**Use Cases:** Service discovery, configuration audits, intent inspection, webhook mapping  
**Performance:** Fast (sub-second to 2 seconds with caching)

---

# SECTION 2: BIGQUERY ANALYTICS TOOLS & SUPPORTING CONTENT (26 TOOLS)

## Overview

Section 2 contains all BigQuery-based analytics tools for:
- Operational metrics (session counts, response times, failures)
- Session metadata (CCAIP data, outcomes, caller information)
- Conversation transcripts (turn-by-turn, NLU quality, flow traversal)

Plus workflows, best practices, and troubleshooting guidelines.

**Data Sources:** BigQuery only  
**Location:** us-central1 (hardcoded)  
**Total Tools:** 26

---

## 2.1 Session Metrics (alerting_monitoring.dialogflow_metrics) - 10 Tools

### Purpose
Real-time operational metrics from Cloud Monitoring, aggregated into BigQuery for historical analysis.

### Traffic Analytics

#### `df_unique_sessions(hours, bucket_minutes)`
Unique vs total sessions over time.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)
- `bucket_minutes` - Aggregation bucket (default 15)

**Returns:**
- Timeseries with unique_sessions, total_sessions per bucket
- EST timestamps

**Use Cases:**
- "Show me unique sessions in the last 3 hours"
- "How many Dialogflow sessions in the last hour?"

---

### Performance Metrics

#### `df_overall_response_times(hours)`
Average Dialogflow response time per minute.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Timeseries: avg_response_time_seconds per minute
- EST timestamps

**Use Cases:**
- "What is the average Dialogflow response time?"
- "Show me DF response times for the last 2 hours"

---

### Status & Failures

#### `df_overall_status_success_failure(hours)`
Success vs failure session counts over time.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Success timeseries (unique_sessions)
- Failure timeseries (unique_sessions)
- Failure rate percentage

**Alert Threshold:** >10% failure rate

**Use Cases:**
- "What is the overall status of Dialogflow calls?"
- "Show me success vs failure sessions, last 3 hours"

---

#### `df_failures_by_failure_reason(hours)`
Failures broken down by failure_reason.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Total failures timeseries
- Failures by reason (webhook_timeout, backend_error, etc.)
- Top 3-5 failure reasons

**Use Cases:**
- "Show me failure reasons for the last 2 hours"
- "Why are Dialogflow calls failing?"

---

### Backend Analytics

#### `df_backend_call_volume(hours)`
Backend call volume (total, by URI, normalized).

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Total backend calls timeseries
- Calls by backend URI
- Normalized backend URIs (removes path/query params)

**Use Cases:**
- "Show me backend call volume, last 3 hours"
- "Backend traffic breakdown by URI"

---

#### `df_call_volume_by_flow(hours)`
Backend call volume grouped by flow_name.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Timeseries of calls per flow
- Top flows by volume

**Use Cases:**
- "Which flows are getting the most traffic?"
- "Backend calls grouped by flow name, last 2 hours"

---

#### `df_backend_response_times(hours)`
Backend response times by backend URI (excludes modem health check).

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Average latency (ms) by backend URI
- Timeseries (per minute)

**Use Cases:**
- "Show me backend response times, last 3 hours"
- "Which backend is the slowest?"

---

#### `df_backend_modem_health_response_times(hours)`
Backend response times for modem health check calls only.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Overall backend response times
- Modem health check specific response times
- Unit: milliseconds

**Use Cases:**
- "Show me modem health check backend response times"

---

### Backend Failures

#### `df_backend_failures_by_http_code(hours)`
Backend failures grouped by HTTP status code.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Total failures timeseries
- Failures by HTTP code (503, 500, 429, etc.)
- Average latency per HTTP code

**Common HTTP Codes:**
- `503` - Service Unavailable (downstream capacity)
- `500` - Internal Server Error (backend crash)
- `429` - Rate Limit Exceeded
- `404` - Not Found (bad endpoint)

**Use Cases:**
- "Show me backend failures by HTTP code, last 6 hours"
- "503 vs 500 failures breakdown"

---

#### `df_backend_failures_by_backend_uri(hours)`
Backend failures grouped by normalized backend URI.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Total failures timeseries
- Failures by normalized backend URL
- Failure reasons (webhook_timeout, backend_error)
- HTTP codes

**Use Cases:**
- "Show me backend failures by URI, last 6 hours"
- "Which backends are failing the most?"

---

## 2.2 Session Metadata Analytics (dfcx_analytics.dfcx_session_metadata) - 6 Tools

### Purpose
Session-level summaries with CCAIP integration, caller information, and heuristic outcomes.

### Session Search & Details

#### `df_get_session_details(session_id, hours)`
Get detailed information for a specific Dialogflow session.

**Parameters:**
- `session_id` - The session ID to search for
- `hours` - Search window (default 24, max 168/7 days)

**Returns (30+ fields):**
- Session start/end times, duration
- Channel (TELEPHONY, WEB, APP)
- Agent ID
- Number of turns
- Head intent (first intent matched)
- Heuristic outcome (deflect, wrapup, incomplete)
- CCAIP data (selected menu, service type, division, market)
- Caller info (ANI, transfer module, callback requested)
- Session parameters (JSON)

**Use Cases:**
- "Show me details for session abc-123-xyz"
- "Get full info for session abc-123-xyz"

**Error Handling:**
- If session not found: "Session not found in the last X hours. Try increasing time window (up to 168 hours/7 days)."

---

#### `df_search_sessions(hours, agent_id, channel, outcome, limit)`
Search for Dialogflow sessions with optional filters.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-24)
- `agent_id` - Optional filter by specific agent
- `channel` - Optional filter: TELEPHONY, WEB, APP
- `outcome` - Optional filter: deflect, wrapup, incomplete
- `limit` - Max results (default 50)

**Returns:**
- Session count
- Session list (session_id, timestamps, duration, channel, turns, intent, outcome)
- Filter summary

**Use Cases:**
- "Show me sessions in the last hour"
- "Find phone sessions in the past 3 hours"
- "Show me deflected sessions from the last 2 hours"

---

### Aggregated Analytics

#### `df_session_analytics(hours)`
Get aggregated session analytics over time.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Total sessions
- Average duration (seconds)
- Average turns per session
- Deflection count & rate (%)
- Wrapup count
- Incomplete session count
- Timeseries (per minute)

**Alert Thresholds:**
- Deflection rate: >70% = good
- Incomplete rate: >15% = investigate

**Use Cases:**
- "Show me session analytics for the last hour"
- "How many sessions deflected in the past 2 hours?"

---

#### `df_session_by_channel(hours)`
Get session breakdown by channel.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Channel (TELEPHONY, WEB, APP)
- Session count per channel
- Average duration & turns per channel
- Deflection count per channel

**Use Cases:**
- "Show me session breakdown by channel"
- "How many phone vs web sessions in the last hour?"

---

#### `df_session_by_outcome(hours)`
Get session breakdown by heuristic outcome.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Outcome (deflect, wrapup, incomplete)
- Session count per outcome
- Average turns per outcome
- Deflection count

**Use Cases:**
- "Show me session breakdown by outcome"
- "How many deflected vs wrapped up sessions?"

---

#### `df_session_top_intents(hours)`
Get top 20 intents by session count.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Top 20 intents (by session count)
- Session count per intent
- Average turns per intent

**Use Cases:**
- "What are the top intents in the last hour?"
- "Show me most used intents, last 3 hours"

---

## 2.3 Conversation Transcript Analytics (dfcx_analytics.dfcx_transcript) - 10 Tools 🆕

### Purpose
Turn-by-turn conversation analysis for NLU quality, flow traversal, and session forensics.

### NLU Quality

#### `df_intent_confidence_distribution(hours)`
Intent confidence score distribution.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Confidence buckets:
  - 🟢 High (0.9-1.0)
  - 🟡 Medium (0.7-0.9)
  - 🟠 Low (0.5-0.7)
  - 🔴 Very Low (<0.5)
- Turn count & percentage per bucket

**Alert Threshold:** >20% in Low/Very Low = NLU degraded

**Use Cases:**
- "How is our bot performing?"
- "Show me intent confidence distribution"
- "Are users getting good intent matches?"

---

#### `df_fallback_analysis(hours)`
Fallback tracking and deflection analysis.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Fallback session count
- Fallback session rate (%)
- Fallback turn count
- Sample unresolved utterances (up to 10)

**Alert Threshold:** >10% fallback rate = coverage gaps

**Use Cases:**
- "How many users are hitting fallback?"
- "What's our deflection rate?"
- "Show me fallback analysis, last 2 hours"

---

### Flow & Journey Analytics

#### `df_flow_traversal(hours)`
Flow and page traversal heatmap.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Top 20 flow/page combinations
- Session count per page
- Turn count (total visits)
- Average turn depth (when page is reached)

**Use Cases:**
- "Which flows are users going through?"
- "Show me page traffic"
- "Popular conversation paths, last 3 hours"

---

#### `df_execution_complexity(hours, min_turns)`
High turn count sessions (potential loops).

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)
- `min_turns` - Threshold (default 20)

**Returns:**
- Session ID
- Turn count
- Flows visited
- Fallback count

**Alert Threshold:** >40 turns = potential conversation loop

**Use Cases:**
- "Show me sessions with too many turns"
- "Find looping conversations"

---

#### `df_event_analysis(hours)`
Event triggers by page/flow.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Top 50 events
- Event name
- Page where triggered
- Flow where triggered
- Event count, session count

**Use Cases:**
- "What events are being triggered?"
- "Show me custom events by page"

---

### Session Deep-Dive

#### `df_session_replay(session_id, days, max_turns)`
Turn-by-turn conversation transcript. ⚡

**Parameters:**
- `session_id` - Session to replay
- `days` - Search window (default 7, max 7)
- `max_turns` - Limit turns to prevent token overflow (default 50)

**Returns (turn-by-turn):**
- Turn number (position)
- User utterance
- Intent matched (display name, confidence score)
- Entities extracted
- Flow → Page navigation
- Agent response
- Webhooks called (JSON)
- Session parameters (JSON state)
- Events triggered
- Match type (INTENT, EVENT, NO_MATCH)
- Channel (TELEPHONY, WEB, APP)

**Use Cases:**
- "Show me the full conversation for session abc-123-xyz"
- "Replay conversation for session abc-123-xyz"
- "What happened in session abc-123-xyz?"

---

#### `df_conversation_summary(session_id, days)`
Quick session statistics.

**Parameters:**
- `session_id` - Session ID
- `days` - Search window (default 7, max 7)

**Returns:**
- Duration (seconds)
- Total turns
- Flows visited (array)
- Unique intents (count)
- Fallback count
- Channel (TELEPHONY, WEB, APP)
- Language (if available)

**Use Cases:**
- "Give me a summary for session abc-123-xyz"
- "Quick stats for session abc-123-xyz"

---

#### `df_failed_sessions_export(hours, limit)`
Batch failed session export.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)
- `limit` - Max sessions (default 50, max 100)

**Criteria:**
- Fallback count >0 OR
- Turn count >30

**Returns:**
- Session ID
- Session start time
- Turn count
- Fallback count
- Ended in fallback (boolean)

**Use Cases:**
- "Show me all failed conversations in the last 2 hours"
- "Export sessions with fallback"

---

### Voice & Telephony

#### `df_voice_latency(hours)`
Voice channel latency analysis (TELEPHONY only).

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Timeseries (per minute)
- Average input audio latency (ms)
- Average output audio latency (ms)
- Max output latency (ms)
- Turn count

**Alert Threshold:** >1000ms avg output latency  
**Target:** <800ms

**Use Cases:**
- "Are there delays in our voice bot?"
- "Check telephony latency"

---

### Response Analysis

#### `df_response_analysis(hours)`
Top agent responses by page.

**Parameters:**
- `hours` - Time window (default 1, recommend 1-6)

**Returns:**
- Top 30 agent responses
- Page where response is used
- Response count
- Page-level percentage

**Alert Threshold:** Single response >15% = consider varying phrasing

**Use Cases:**
- "What are the most common bot responses?"
- "Are we saying the same things too often?"

---

## Section 2 Summary

**Total Tools: 26**
- 10 tools: Session metrics (dialogflow_metrics table)
- 6 tools: Session metadata (dfcx_session_metadata table)
- 10 tools: Conversation transcripts (dfcx_transcript table)

**Data Source:** BigQuery only  
**Location:** us-central1 (hardcoded)  
**Use Cases:** Performance monitoring, failure analysis, conversation intelligence, session forensics

---

## 2.4 Performance Features

### Caching Layer (config.py)
- **5-minute TTL** for agent configs, intents, webhooks (Section 1 tools only)
- **Cache hit ratio**: ~85% for repeated queries
- **Functions**: `get_cached_config()`, `set_cached_config()`, `clear_all_caches()`

### Rate Limiting
- **100ms** minimum interval between API requests
- **Exponential backoff** on 429 errors (initial 1s, max 60s)
- **Max retries**: 5 attempts with automatic retry
- **Applies to:** Both Section 1 (API) and Section 2 (BigQuery)

### BigQuery Optimizations
- **Parameterized queries** (prevent SQL injection)
- **60-second timeout** (prevents agent hangs)
- **Location-aware clients**: Single us-central1 client for both datasets
- **JSON-safe conversion**: Auto-converts datetime/date objects to ISO strings
- **Applies to:** Section 2 tools only (BigQuery Analytics)

### Time Window Limits
- **Session Metadata**: Max 168 hours (7 days)
- **Transcript Analytics**: Max 168 hours (7 days)
- **Metrics Table**: Recommend 1-6 hours for performance

---

## 2.5 Integration with Master Agent

### Delegation from Master Agent

The Dialogflow Expert is invoked for:
- Dialogflow-specific queries (agents, intents, webhooks, sessions)
- Conversation analytics (transcripts, NLU quality, flow traversal)
- Backend failure analysis (delegated from Cloud Run for DF-side metrics)

### Delegation to Cloud Run Expert

For webhook infrastructure metrics (CPU, memory, instance count), delegate to Cloud Run specialist:
- "For detailed webhook performance (latency p95, error rate trends, infrastructure), use Cloud Run specialist"

---

## 2.6 Error Handling

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `PERMISSION_DENIED` | Missing IAM roles | Add `Dialogflow API Reader` + `BigQuery Data Viewer` |
| `API has not been used` | API not enabled | Enable Dialogflow CX API in Console |
| `NOT_FOUND` / `UNIMPLEMENTED` | Invalid location | Verify location ID (us, global, us-central1) |
| `BigQuery timeout` | Query >60s | Reduce time window (1h instead of 6h) |
| `Session not found` | Outside time window | Increase search window (up to 168h) |

### Graceful Degradation
- Returns structured error JSON with `error`, `error_details`, `tool` fields
- Suggests corrective actions in `note` field
- No stack traces exposed to end user

---

## 2.7 Environment Variables

Required in `env/.env.dev`:

```bash
# GCP Project
GCP_PROJECT_ID=dxp-cloud-ivr-prod-751497
GOOGLE_CLOUD_PROJECT=dxp-cloud-ivr-prod-751497

# Dialogflow Location
GOOGLE_CLOUD_LOCATION=us-east4
LOCATION=us-east4

# BigQuery Location (hardcoded in tools.py)
# Both datasets are in us-central1
```

---

## 2.8 Testing & Validation

### Test Scenarios Covered

**Section 1: REST API Tools**
1. Agent Discovery: List agents in us, global, us-central1
2. Intent Inspection: List intents, get training phrases
3. Webhook Configuration: List webhooks with timeout/URI settings

**Section 2: BigQuery Analytics**
1. Session Metrics: Unique sessions, response times, status success/failure
2. Session Metadata: Session search, details, analytics by channel/outcome
3. Transcript Analytics: Confidence distribution, fallback analysis, session replay
4. Performance: 100-session queries, 6-hour time windows
5. Edge Cases: Non-existent sessions, empty results

### Expected Response Times
- **Cached queries (Section 1)**: <100ms
- **Fresh config (Section 1)**: 500-1500ms
- **BigQuery 1h window (Section 2)**: 2-5s
- **BigQuery 6h window (Section 2)**: 5-15s
- **Session replay (Section 2)**: 3-8s (50 turns)

---

## 2.9 Version History

### v2.0.0 (Feb 16, 2026) - Current
- ✅ Reorganized README into Section 1 (REST API - 6 tools) and Section 2 (BigQuery Analytics - 26 tools)
- ✅ Added 10 conversation transcript analytics tools
- ✅ Added 6 session metadata tools
- ✅ Integrated master_agent utils (rate limiter, retry, response manager)
- ✅ Hardcoded BigQuery location to us-central1 for both datasets
- ✅ Added `max_turns` parameter to session replay (default 50)
- ✅ Added `days` parameter to session search (max 7 days)
- ✅ Enhanced error messages with corrective actions

### v1.0.0 (Feb 3, 2026)
- Initial production release
- 10 BigQuery metrics tools
- Agent/intent/webhook discovery
- Caching layer with 5min TTL

---

## 2.10 Dependencies

```python
google-cloud-dialogflowcx>=1.27.0  # Section 1 (REST API)
google-cloud-bigquery>=3.11.0      # Section 2 (BigQuery Analytics)
google-cloud-monitoring>=2.15.0    # Future use
google-auth>=2.23.0               # Both sections
python-dotenv>=1.0.0              # Configuration
```

---

## 2.11 Contributing

### Adding New Tools

**For Section 1 (REST API):**
1. **Add method** to `DialogflowTools` class in `tools.py` (no SQL needed)
2. **Add ADK wrapper** at bottom of `tools.py`
3. **Register tool** in `create_dialogflow_agent()` in `agent.py`
4. **Update system instructions** with usage pattern
5. **Update README Section 1** with tool documentation
6. **Add caching** if appropriate (see `config.py`)
7. **Test** with sample queries

**For Section 2 (BigQuery Analytics):**
1. **Define SQL query** in `queries.py`
2. **Add method** to `DialogflowTools` class in `tools.py`
3. **Add ADK wrapper** at bottom of `tools.py`
4. **Register tool** in `create_dialogflow_agent()` in `agent.py`
5. **Update system instructions** with usage pattern
6. **Update README Section 2** with tool documentation
7. **Test** with sample queries

---

## 2.12 Support

For issues or questions:
- Check error messages in response JSON (`error`, `note` fields)
- Verify IAM permissions (Dialogflow API Reader, BigQuery Data Viewer)
- Confirm API enablement (Dialogflow CX, BigQuery)
- Review time window limits (max 168 hours for session/transcript queries)

---

## 📄 License

Internal use only - Accenture GCP Ops Intelligent Assistant  
Project: dxp-cloud-ivr-prod-751497
