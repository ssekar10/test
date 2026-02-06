# Dialogflow Expert Sub-Agent Test Prompts

Comprehensive test suite for validating session metadata tools and analytics capabilities.

## Quick Start Tests

Basic functionality check - Run these first to verify agent is working:

Show me the last 10 sessions in the past 1 hour
What are the session analytics for the last hour?
Show me session breakdown by channel for the last hour

## 1. Session Search (df_search_sessions)

### Basic Search

Show me the last 50 sessions in the past 1 hour
Search for sessions in the last 2 hours
Find the most recent 30 sessions
List the last 100 sessions from the past 6 hours

### Custom Limits

Show me the last 10 sessions in the past hour
Find 25 sessions from the last 3 hours
Get 5 most recent sessions

## 2. Session Details (df_get_session_details)

### Get Specific Session

What are the complete details for session [paste session_id from previous search]?
Get session details for 065GQ2DnR9-Teu0AAWc1_sV_A
Show me full details for session xyz-abc-123 in the last 2 hours

### Extended Time Windows

Find session details for [session_id] in the last 48 hours
Get session [session_id] from the last 7 days

### Error Cases

Get session details for fake-session-id-12345

## 3. Filter by Channel

### Voice/Phone Channel

Show me sessions on the phone channel in the last hour
Search for voice channel sessions in the past 2 hours
Find telephony sessions from the last 3 hours

### Web Channel

List web channel sessions in the past hour
Show me website sessions from the last 2 hours

### App/Mobile Channel

Find app channel sessions in the last hour
Show mobile sessions from the past 3 hours

## 4. Filter by Agent

Show sessions for agent_id 680ec6e9-b5b5-44d9-a3ec-5c186ad3438b in the last hour
Search sessions for agent abc-123 in the past 2 hours
Find sessions handled by agent [agent_id] in the last 6 hours

## 5. Filter by Outcome

### Successful Outcomes

Show me sessions with successful outcome in the last hour
Find completed sessions in the past 2 hours

### Deflections

Show me sessions with deflection outcome in the last hour
Find deflected sessions in the past 3 hours
How many sessions had deflections in the last 2 hours?

### Failures

Search for failed sessions in the last hour
Show me incomplete sessions from the past 2 hours

### Transfers

List sessions filtered by transfer outcome in the past hour
Show transferred sessions in the last 3 hours

### No CCAIP Data

Find sessions with no_ccaip_data outcome in the last hour

## 6. Session Analytics (df_session_analytics)

### Basic Analytics

What are the session analytics for the last hour?
Show me session statistics for the past 2 hours
Give me aggregated session metrics for the last 3 hours

### Performance Analysis

Analyze session performance over the last hour
What's the average session duration in the past 2 hours?
How many sessions ended with deflection in the last hour?

### Time-Series Analysis

Show me session volume trend by minute for the last hour
What's the session analytics time series for the past 3 hours?

## 7. Channel Breakdown (df_session_by_channel)

Show me session breakdown by channel for the last hour
What channels are being used in the past 2 hours?
Break down sessions by channel for the last 3 hours
Which channels have the most sessions in the past 6 hours?
Compare channel performance for the last hour

## 8. Outcome Distribution (df_session_by_outcome)

What are the session outcomes in the last hour?
Show me outcome distribution for the past 2 hours
Break down sessions by heuristic outcome for the last 3 hours
What outcomes do sessions have in the past hour?
What's the deflection rate in the last 2 hours?

## 9. Top Intents (df_session_top_intents)

What are the top intents by session count in the last hour?
Show me the most common intents from the past 2 hours
Which intents are triggered most in the last 3 hours?
List the top 20 intents by session volume for the past hour
What are the top 10 intents in the last 6 hours?

## 10. Combined Filters (Advanced)

### Channel + Outcome

Show me phone channel sessions with deflection outcome in the last 2 hours
Find web sessions with successful outcome in the past hour
Search for voice channel failures in the last 3 hours

### Agent + Channel

Find sessions for agent abc-123 on the web channel in the past hour
Show me phone sessions for agent 680ec6e9-b5b5-44d9-a3ec-5c186ad3438b in the last 2 hours

### Agent + Outcome + Channel

Search for successful sessions on the telephony channel in the last 3 hours, limit 25
Find deflected phone sessions for agent xyz in the past hour

## 11. Comparative Analysis

### Time Comparisons

Compare session analytics between the last hour and the previous hour
Show me session breakdown by channel for 1 hour vs 3 hours
What are the top intents in the last hour vs the last 6 hours?

### Metric Comparisons

Compare deflection rates across all channels in the last 2 hours
Which channel has the highest average session duration in the past 3 hours?

## 12. Troubleshooting Scenarios

### Session Issues

Show me sessions with incomplete status in the last hour
Find sessions that didn't end normally in the past 2 hours
Which sessions had errors in the last 3 hours?

### CCAIP Issues

Show me sessions with CCAIP deflection in the last hour
Which CCAIP menus were selected most in the past 2 hours?
Find sessions with CCAIP queue issues in the last hour

## 13. Business Intelligence Queries

What's the average session duration by channel in the last 3 hours?
How many sessions had deflections vs regular completions in the past hour?
What's the deflection rate by channel for the last 2 hours?
Which outcomes have the highest average turns in the past 6 hours?

## 14. CCAIP-Specific Queries

Show me sessions with CCAIP menu selections in the last hour
Which CCAIP menus were selected most in the past 3 hours?
Find sessions with CCAIP deflection in the last 2 hours
What are the top CCAIP queue IDs in the past hour?

## 15. Multi-Step Workflows

Step 1: Show me the last 10 sessions in the past hour
Step 2: [Pick a session_id from results]
Step 3: Get full details for session [session_id]
Step 4: What was the head intent and outcome for that session?

Step 1: What are the top intents in the last hour?
Step 2: [Pick top intent]
Step 3: Show me sessions with that intent in the past hour

## 16. Performance Testing

Show me 100 sessions in the last 6 hours
Search for sessions with all filters applied: agent [id], channel phone, outcome success, limit 50, for the past 3 hours

## 17. Edge Cases and Validation

Search for sessions with limit 5 in the past hour
Find sessions in the last 24 hours
Show me sessions with no filters applied for the past 30 minutes
Get session details for a non-existent session ID: fake-session-123

## 18. Real-World Business Queries

How many phone sessions deflected to live agents in the last hour?
What's the average conversation length for successful vs failed sessions in the past 2 hours?
Which market/division has the most sessions in the last 3 hours?
Show me sessions that transferred to a specific module in the past hour

## Expected Results Guide

For df_search_sessions: Returns session_id, timestamps, duration, channel, agent_id, turns, intent, outcome, market, division

For df_get_session_details: Returns all 30+ fields including CCAIP data, caller info, transfer details, parameters

For df_session_analytics: Returns total_sessions, avg_duration, avg_turns, deflection_count, wrapup_count, incomplete_sessions, timeseries

For df_session_by_channel: Returns channel, session_count, avg_duration, avg_turns, deflection_count

For df_session_by_outcome: Returns heuristic_outcome, session_count, avg_turns, deflection_count

For df_session_top_intents: Returns head_intent, session_count, avg_turns (top 20)

## Validation Checklist

After testing, verify:
- All 6 new tools work without errors
- Time windows are respected (1h, 2h, 3h, 6h)
- Filters work (agent_id, channel, outcome)
- Limit parameter works (default 50, custom values)
- Session details show all fields including JSON parameters
- Aggregated stats match time-series data
- Timestamps are in EST and properly formatted
- Empty results return graceful messages
- Invalid session_id returns "not found" message
