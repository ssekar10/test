# Dialogflow Expert: User Prompt Guide

**Version:** 2.1.0  
**Last Updated:** February 16, 2026

A comprehensive guide for interacting with the Dialogflow CX Expert sub-agent. Use natural language queries - the agent will automatically select the appropriate tools.

---

## 🎯 Quick Reference

| Task | Example Prompt | Tool Used | Section |
|------|----------------|-----------|---------|
| List agents | "Show me all Dialogflow agents" | `list_dialogflow_agents` | REST API |
| Agent config | "Get configuration for XA Agent" | `get_agent_details_fast` | REST API |
| Intent list | "List all intents for DR-agent" | `list_intents` | REST API |
| Webhooks | "What webhooks does XA Agent have?" | `list_webhooks` | REST API |
| Traffic | "Show unique sessions in last 3 hours" | `df_unique_sessions` | Monitoring |
| Failures | "Backend failures by HTTP code, last 6 hours" | `df_backend_failures_by_http_code` | Monitoring |
| NLU quality | "How is our bot performing?" | `df_intent_confidence_distribution` | Monitoring |
| Session replay | "Show full conversation for session abc-123" | `df_session_replay` | Monitoring |

---

# SECTION 1: REST API TOOLS - DISCOVERY & CONFIGURATION (6 TOOLS)

This section covers all Dialogflow CX API-based tools for agent discovery, intent inspection, and webhook configuration.

---

## 1.1 Agent Discovery & Configuration

### List All Agents

```
"List all Dialogflow agents"
"Show me agents in the us region"
"Which Dialogflow agents are in us-central1?"
```

**Response includes:**
- Agent count
- Agent names and IDs
- Default languages
- Time zones

---

### Get Agent Configuration

```
"Show me configuration for XA Agent"
"Get details for DR-agent"
"What is the time zone for RobTest agent?"
"Is spell correction enabled for XA Agent?"
```

**Response includes:**
- Display name, languages, time zone
- Logging settings
- Spell correction status
- Supported features

**Note:** Use `get_agent_details_fast` for speed (cached 5 min). If you need fresh data:
```
"Get fresh configuration for XA Agent"
"Show me updated details for DR-agent"
```

---

## 1.2 Intent Management

### List Intents

```
"List all intents for XA Agent"
"Show me intents in DR-agent"
"How many intents does RobTest have?"
```

**Response includes:**
- Intent count
- Intent names and IDs
- Training phrase counts
- Parameter lists

---

### Get Intent Details

```
"Show me training phrases for the 'order-status' intent"
"Get details for 'troubleshoot.internet' intent in XA Agent"
"What parameters does the 'billing' intent have?"
```

**Response includes:**
- Full list of training phrases
- Parameter definitions (entity types, is_list, redact)
- Labels

---

## 1.3 Webhook Configuration

### List Webhooks

```
"What webhooks does XA Agent have?"
"Show webhook configuration for DR-agent"
"Which webhooks are configured for RobTest?"
```

**Response includes:**
- Webhook count
- Webhook names, URIs
- Timeout settings
- Request headers (if configured)

**For webhook performance metrics** (latency, errors), delegate to Cloud Run specialist.

---

# SECTION 2: MONITORING & ANALYTICS TOOLS (26 TOOLS)

This section covers all BigQuery-based monitoring, analytics, and conversation intelligence tools.

---

## 2.1 Session Traffic & Performance

### Unique Sessions

```
"Show me unique sessions in the last hour"
"How many Dialogflow sessions in the last 3 hours?"
"Total vs unique sessions, last 6 hours"
```

**Response includes:**
- Timeseries (15-minute buckets by default)
- Total sessions vs unique sessions
- EST timestamps

---

### Overall Response Times

```
"What is the average Dialogflow response time?"
"Show me DF response times for the last 2 hours"
"How fast is Dialogflow responding?"
```

**Response includes:**
- Timeseries (per minute)
- Average response time in seconds
- EST timestamps

---

### Success vs Failure Status

```
"What is the overall status of Dialogflow calls?"
"Show me success vs failure sessions, last 3 hours"
"How many Dialogflow failures in the last hour?"
```

**Response includes:**
- Success session count (timeseries)
- Failure session count (timeseries)
- Failure rate percentage

**Alert threshold:** >10% failure rate

---

### Failures by Reason

```
"Show me failure reasons for the last 2 hours"
"Why are Dialogflow calls failing?"
"Breakdown of failures by reason"
```

**Response includes:**
- Total failure count (timeseries)
- Failures grouped by reason (webhook_timeout, backend_error, etc.)
- Top 3-5 failure reasons

---

## 2.2 Backend Performance & Failures

### Backend Call Volume

```
"Show me backend call volume, last 3 hours"
"How many backend calls in the last hour?"
"Backend traffic breakdown by URI"
```

**Response includes:**
- Total backend calls (timeseries)
- Calls by backend URI (timeseries)
- Normalized backend URIs (removes path/query params)

---

### Call Volume by Flow

```
"Show me call volume by Dialogflow flow"
"Which flows are getting the most traffic?"
"Backend calls grouped by flow name, last 2 hours"
```

**Response includes:**
- Timeseries of calls per flow
- Top flows by volume

---

### Backend Response Times

```
"Show me backend response times, last 3 hours"
"Which backend is the slowest?"
"Average backend latency per URI"
```

**Response includes:**
- Average latency (ms) by backend URI
- Timeseries (per minute)
- Excludes modem health check by default

**Modem health check variant:**
```
"Show me modem health check backend response times"
```

---

### Backend Failures by HTTP Code

```
"Show me backend failures by HTTP code, last 6 hours"
"Which HTTP errors are occurring?"
"503 vs 500 failures breakdown"
```

**Response includes:**
- Total failure count (timeseries)
- Failures by HTTP code (503, 500, 429, etc.)
- Average latency per HTTP code

**Common HTTP codes:**
- `503` - Service Unavailable (downstream capacity)
- `500` - Internal Server Error (backend crash)
- `429` - Rate Limit Exceeded
- `404` - Not Found (bad endpoint)

---

### Backend Failures by URI

```
"Show me backend failures by URI, last 6 hours"
"Which backends are failing the most?"
"Failures grouped by normalized backend URL"
```

**Response includes:**
- Total failures (timeseries)
- Failures by normalized backend URL
- Failure reasons (webhook_timeout, backend_error)
- HTTP codes

---

## 2.3 Session Metadata & Search

### Get Session Details

```
"Show me details for session abc-123-xyz"
"Get full info for session abc-123-xyz"
"What happened in session abc-123-xyz?" (searches last 24 hours)
```

**Optional: Specify search window (up to 7 days):**
```
"Get session abc-123-xyz from the last 48 hours"
"Search for session abc-123-xyz in the past week"
```

**Response includes (30+ fields):**
- Session start/end times, duration
- Channel (TELEPHONY, WEB, APP)
- Agent ID
- Number of turns
- Head intent (first intent matched)
- Heuristic outcome (deflect, wrapup, incomplete)
- CCAIP data (selected menu, service type, division, market)
- Caller info (ANI, transfer module, callback requested)
- Session parameters (JSON)

**Error handling:**
- If session not found: "Session not found in the last X hours. Try increasing time window."

---

### Search Sessions

```
"Show me sessions in the last hour"
"Find phone sessions in the past 3 hours"
"Show me deflected sessions from the last 2 hours"
```

**With filters:**
```
"Search for sessions with agent [agent-id], channel phone, outcome deflect, limit 50, last 3 hours"
"Show me web sessions that wrapped up, last hour"
"Find incomplete sessions for agent XA, last 6 hours"
```

**Filters:**
- `agent_id` - Filter by specific agent
- `channel` - TELEPHONY, WEB, APP
- `outcome` - deflect, wrapup, incomplete
- `limit` - Max results (default 50)

**Response includes:**
- Session count
- Session list (session_id, timestamps, duration, channel, turns, intent, outcome)
- Filter summary

---

### Session Analytics

```
"Show me session analytics for the last hour"
"Aggregated session stats, last 3 hours"
"How many sessions deflected in the past 2 hours?"
```

**Response includes:**
- Total sessions
- Average duration (seconds)
- Average turns per session
- Deflection count & rate (%)
- Wrapup count
- Incomplete session count
- Timeseries (per minute)

**Alert thresholds:**
- Deflection rate: >70% = good
- Incomplete rate: >15% = investigate

---

### Sessions by Channel

```
"Show me session breakdown by channel"
"How many phone vs web sessions in the last hour?"
"Channel distribution, last 3 hours"
```

**Response includes:**
- Channel (TELEPHONY, WEB, APP)
- Session count per channel
- Average duration & turns per channel
- Deflection count per channel

---

### Sessions by Outcome

```
"Show me session breakdown by outcome"
"How many deflected vs wrapped up sessions?"
"Outcome distribution, last 2 hours"
```

**Response includes:**
- Outcome (deflect, wrapup, incomplete)
- Session count per outcome
- Average turns per outcome
- Deflection count

---

### Top Intents

```
"What are the top intents in the last hour?"
"Show me most used intents, last 3 hours"
"Top 20 intents by session count"
```

**Response includes:**
- Top 20 intents (by session count)
- Session count per intent
- Average turns per intent

---

## 2.4 Conversation Transcript Analytics

### Intent Confidence Distribution

```
"How is our bot performing?"
"Show me intent confidence distribution"
"Are users getting good intent matches?"
```

**Response includes:**
- Confidence buckets:
  - 🟢 High (0.9-1.0)
  - 🟡 Medium (0.7-0.9)
  - 🟠 Low (0.5-0.7)
  - 🔴 Very Low (<0.5)
- Turn count & percentage per bucket

**Alert threshold:** >20% in Low/Very Low = NLU degraded

**Use case:** Identify weak NLU, intents needing better training

---

### Fallback Analysis

```
"How many users are hitting fallback?"
"What's our deflection rate?"
"Show me fallback analysis, last 2 hours"
```

**Response includes:**
- Fallback session count
- Fallback session rate (%)
- Fallback turn count
- Sample unresolved utterances (up to 10)

**Alert threshold:** >10% fallback rate = coverage gaps

**Use case:** Measure bot effectiveness, identify what users are saying that isn't understood

---

### Flow Traversal Heatmap

```
"Which flows are users going through?"
"Show me page traffic"
"Popular conversation paths, last 3 hours"
```

**Response includes:**
- Top 20 flow/page combinations
- Session count per page
- Turn count (total visits)
- Average turn depth (when page is reached)

**Use case:** Identify popular paths vs abandoned flows, entry pages vs deep pages

---

### Session Replay (Full Transcript)

```
"Show me the full conversation for session abc-123-xyz"
"Replay conversation for session abc-123-xyz"
"What happened in session abc-123-xyz?" (full transcript)
"Show me transcript for session abc-123-xyz"
"Give me conversation details for session abc-123-xyz"
```

**Response includes (turn-by-turn):**
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

**Parameters:**
- `days` - Search window (default 7, max 7)
- `max_turns` - Limit turns to prevent token overflow (default 50)

**Use case:** Forensic troubleshooting for escalated issues, understand exact conversation flow

---

### Conversation Summary (Quick Stats)

```
"Give me a summary for session abc-123-xyz"
"Quick stats for session abc-123-xyz"
"Overview of session abc-123-xyz"
```

**Response includes:**
- Duration (seconds)
- Total turns
- Flows visited (array)
- Unique intents (count)
- Fallback count
- Channel (TELEPHONY, WEB, APP)
- Language (if available)

**Use case:** Fast triage before requesting full transcript

---

### Execution Complexity (High Turn Sessions)

```
"Show me sessions with too many turns"
"Find looping conversations"
"Complex sessions, last 3 hours"
```

**Parameters:**
- `min_turns` - Threshold (default 20)

**Response includes:**
- Session ID
- Turn count
- Flows visited
- Fallback count

**Alert threshold:** >40 turns = potential conversation loop

**Use case:** Detect overly complex paths, conversation loops

---

### Voice Latency

```
"Are there delays in our voice bot?"
"Check telephony latency"
"Voice channel latency, last 2 hours"
```

**Response includes (TELEPHONY channel only):**
- Timeseries (per minute)
- Average input audio latency (ms)
- Average output audio latency (ms)
- Max output latency (ms)
- Turn count

**Alert threshold:** >1000ms avg output latency  
**Target:** <800ms

**Use case:** Diagnose slow telephony responses (TTS, webhook delays)

---

### Response Analysis

```
"What are the most common bot responses?"
"Are we saying the same things too often?"
"Show me response frequency, last hour"
```

**Response includes:**
- Top 30 agent responses
- Page where response is used
- Response count
- Page-level percentage

**Alert threshold:** Single response >15% = consider varying phrasing

**Use case:** Audit reply consistency, identify repetitive responses

---

### Event Analysis

```
"What events are being triggered?"
"Show me custom events by page"
"Event triggers, last 3 hours"
```

**Response includes:**
- Top 50 events
- Event name
- Page where triggered
- Flow where triggered
- Event count
- Session count

**Use case:** Debug custom event logic, validate event-based flow transitions

---

### Failed Sessions Export

```
"Show me all failed conversations in the last 2 hours"
"Export sessions with fallback"
"Find problematic sessions, last 6 hours"
```

**Criteria:**
- Fallback count >0 OR
- Turn count >30

**Parameters:**
- `limit` - Max sessions (default 50, max 100)

**Response includes:**
- Session ID
- Session start time
- Turn count
- Fallback count
- Ended in fallback (boolean)

**Use case:** Batch analysis of failed conversations, prioritize sessions for investigation

---

# SECTION 3: WORKFLOWS & BEST PRACTICES

---

## 3.1 Multi-Step Workflows

### Workflow 1: Investigate High Failure Rate

```
Step 1: "What is the overall status of Dialogflow, last 3 hours?"
→ Identifies failure rate

Step 2: "Show me failures by reason, last 3 hours"
→ Identifies top failure reason (e.g., webhook_timeout)

Step 3: "Backend failures by HTTP code, last 3 hours"
→ Identifies HTTP error codes

Step 4: "Backend failures by URI, last 3 hours"
→ Identifies specific failing backend

Step 5: Delegate to Cloud Run specialist: "Show me performance for [backend-url]"
```

---

### Workflow 2: NLU Quality Audit

```
Step 1: "How is our bot performing?"
→ Shows intent confidence distribution

Step 2 (if low confidence detected): "Show me fallback analysis"
→ Identifies sample unresolved utterances

Step 3: "List intents for XA Agent"
→ Identifies which intents exist

Step 4: "Get training phrases for [intent-name]"
→ Reviews training data for weak intent

Step 5: Add training phrases in Dialogflow Console
```

---

### Workflow 3: Session Forensics

```
Step 1: "Give me a summary for session abc-123-xyz"
→ Quick stats (duration, turns, fallback count)

Step 2 (if fallback_count >0): "Show me full conversation for session abc-123-xyz"
→ Turn-by-turn transcript

Step 3: Analyze transcript for:
  - Low confidence intents (<0.7)
  - Missing entities
  - Webhook failures
  - Conversation loops (same page visited 3+ times)
```

---

### Workflow 4: Backend Performance Investigation

```
Step 1: "Show me backend response times, last 3 hours"
→ Identifies slowest backend

Step 2: "Backend failures by URI, last 3 hours"
→ Correlates latency with failures

Step 3: Delegate to Cloud Run: "Show me resource utilization for [backend-service]"
→ Checks if backend is CPU/memory constrained

Step 4: Delegate to Cloud Run: "Show me logs for [backend-service], last hour"
→ Identifies error patterns
```

---

## 3.2 Time Window Best Practices

### Recommended Time Windows

| Query Type | Recommended Window | Max Window |
|------------|-------------------|------------|
| Real-time monitoring | 1 hour | 6 hours |
| Failure investigation | 3 hours | 6 hours |
| Session search | 1 hour | 7 days |
| Session details | 24 hours | 7 days |
| Transcript analytics | 1-3 hours | 7 days |

### Performance Tips

- **Start with 1 hour** for fastest results
- **Increase to 3-6 hours** for trend analysis
- **Use 24 hours** for session search (better hit rate)
- **Avoid >6 hours** for metrics queries (slow, risk timeout)

---

## 3.3 Context & Location Handling

### Location Inference

The agent remembers location from previous queries:

```
User: "List agents in us region"
→ Agent: [Lists agents in "us"]

User: "Show me intents for XA Agent" (no location specified)
→ Agent: [Uses "us" from previous query]

User: "Get configuration for DR-agent"
→ Agent: [Still uses "us"]
```

To reset location:
```
"List agents in us-central1"
→ Switches to us-central1 for subsequent queries
```

---

### Multi-Location Queries

```
"List agents in us and us-central1"

Agent response:
"I'll query one location at a time for optimal performance."
→ Queries "us" first
→ Then queries "us-central1"
→ Presents combined results
```

---

## 3.4 Error Messages & Troubleshooting

### Common Errors

#### Permission Denied
```
Error: "PERMISSION_DENIED"
Solution: Ensure service account has:
  - Dialogflow API Reader (for agent queries)
  - BigQuery Data Viewer + BigQuery Job User (for analytics)
```

#### API Not Enabled
```
Error: "API has not been used in project"
Solution: Enable Dialogflow CX API at:
  https://console.cloud.google.com/apis/library/dialogflow.googleapis.com
```

#### Session Not Found
```
Error: "Session not found in the last 24 hours"
Solution: Increase search window:
  "Get session abc-123-xyz from the last 7 days"
```

#### BigQuery Timeout
```
Error: "Query timed out after 60 seconds"
Solution:
  1. Reduce time window (1 hour instead of 6)
  2. Use aggregated queries instead of timeseries
  3. Query during off-peak hours
```

---

## 3.5 Advanced Prompts

### Comparative Analysis

```
"Compare backend latency between billing-api and customer-data for the last 3 hours"
"Show me deflection rate by channel, last 6 hours"
"Which flow has the highest fallback rate?"
```

---

### Threshold-Based Alerts

```
"Are there any backends with >500ms latency in the last hour?"
"Show me sessions with >30 turns, last 3 hours"
"Which intents have confidence <0.7 in the last hour?"
```

---

### Business-Focused Queries

```
"How many phone sessions deflected to live agents in the last hour?"
"What's the average conversation length for successful vs failed sessions?"
"Which market/division has the most sessions?"
"Show me sessions that transferred to [module-name]"
```

---

## 3.6 Output Format Guidelines

### BigQuery Results

The agent **summarizes** BigQuery data, never dumps raw JSON:

**Good response:**
```
"In the last hour, Dialogflow handled 10,992 successful sessions and 757 failures (6.4% failure rate). Top failure reason: webhook_timeout (41%). Backend latency averaged 245ms, with billing-api slowest at 890ms."
```

**Bad response:**
```
"Here are the results: [dumps 50 rows of JSON]"
```

---

### Timestamps

All timestamps are in **EST timezone**:
```
Query time: 2026-02-16 05:30:00 PM EST
Time range: 2026-02-16 04:30:00 PM EST → 05:30:00 PM EST
```

---

### Tables

Comparative data is presented in **Markdown tables**:

```
| Backend URL | Calls | Avg Latency | Failures |
|-------------|-------|-------------|----------|
| billing-api.com | 1,245 | 890ms | 23 |
| customer-data.net | 3,421 | 145ms | 2 |
```

---

## 3.7 Testing & Validation Checklist

After updates, test with these prompts:

### Section 1: REST API Tools
- [ ] "List all Dialogflow agents"
- [ ] "Get configuration for XA Agent"
- [ ] "List intents for XA Agent"
- [ ] "Show me webhooks for XA Agent"

### Section 2: Monitoring Tools - Session Metrics
- [ ] "Unique sessions in the last hour"
- [ ] "Overall response times, last 3 hours"
- [ ] "Success vs failure, last hour"
- [ ] "Backend failures by HTTP code, last 6 hours"

### Section 2: Monitoring Tools - Session Metadata
- [ ] "Get session details for [session-id]"
- [ ] "Search for phone sessions, last hour"
- [ ] "Session analytics, last 3 hours"
- [ ] "Top intents, last hour"

### Section 2: Monitoring Tools - Transcript Analytics
- [ ] "How is our bot performing?"
- [ ] "Show me fallback analysis"
- [ ] "Show full conversation for session [session-id]"
- [ ] "Give me a summary for session [session-id]"
- [ ] "Voice latency, last 2 hours"

### Edge Cases
- [ ] "Get session details for fake-session-123" (should return "not found")
- [ ] "Show me sessions from the last 24 hours" (max time window)
- [ ] "List agents in invalid-location" (should return error)

---

## 3.8 Delegation Rules

### When to Use Dialogflow Expert

- Agent/intent/webhook configuration (Section 1: REST API)
- Session traffic & metrics (Section 2: Monitoring)
- Backend failures (Dialogflow-side) (Section 2: Monitoring)
- Conversation transcripts & NLU quality (Section 2: Monitoring)
- Flow traversal & event analysis (Section 2: Monitoring)

### When to Delegate to Cloud Run Expert

- Webhook infrastructure metrics (CPU, memory, instance count)
- Cloud Run service performance (request latency p95, error rates)
- Infrastructure troubleshooting (scaling, cold starts)

**Example delegation:**
```
User: "Is the billing-api webhook slow?"

Dialogflow Expert:
"The billing-api webhook has an average backend response time of 890ms (DF-side measurement). For detailed infrastructure metrics (CPU, memory, instance scaling), use the Cloud Run specialist."
```

---

## 📚 Additional Resources

- **Architecture Diagram**: See README.md § Architecture
- **Tool Reference**: See README.md § Section 1 (REST API) and Section 2 (Monitoring)
- **Error Handling**: See README.md § Error Handling
- **Environment Setup**: See README.md § Environment Variables

---

## 🔄 Document Version

- **Version:** 2.1.0
- **Last Updated:** February 16, 2026
- **Changelog:**
  - ✅ Reorganized to Section 1 (REST API - 6 tools) and Section 2 (Monitoring - 26 tools)
  - ✅ Updated Quick Reference table with section indicators
  - ✅ Moved workflows and best practices to Section 3
  - ✅ All REST API prompts now in Section 1
  - ✅ All Monitoring/Analytics prompts now in Section 2
