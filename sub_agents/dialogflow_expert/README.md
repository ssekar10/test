# Dialogflow Expert Sub-Agent

Expert AI agent for monitoring, analyzing, and troubleshooting Google Cloud Dialogflow CX (DFCX) conversational AI systems.

## Overview

This sub-agent provides comprehensive analytics and operational intelligence for Dialogflow CX deployments by querying BigQuery tables containing session metadata, conversation logs, and system metrics.

### Key Capabilities

- Real-time Session Monitoring: Track active conversations, session outcomes, and deflection rates
- Performance Analytics: Analyze session duration, turn counts, and channel distribution
- Intent Analysis: Identify top intents, conversation patterns, and user behavior trends
- CCAIP Integration: Monitor Contact Center AI Platform menu selections and call routing
- Historical Analysis: Query up to 7 days of session data with flexible time windows
- Detailed Session Investigation: Retrieve complete metadata for specific session IDs

## Architecture

dialogflow_expert/
├── README.md           # This file
├── PROMPTS.md          # Test prompts and usage examples
├── agent.py            # Sub-agent definition and system instructions
├── tools.py            # Tool implementations (6 session metadata tools)
└── queries.py          # BigQuery SQL queries

## Tools

### Session Metadata Tools (dfcx_session_metadata table)

| Tool | Purpose | Time Window | Key Parameters |
|------|---------|-------------|----------------|
| df_search_sessions | Search and filter sessions | 1-168 hours | agent_id, channel, outcome, limit |
| df_get_session_details | Get complete session data | 1-168 hours | session_id (required) |
| df_session_analytics | Aggregated statistics | 1-168 hours | Returns totals, averages, time-series |
| df_session_by_channel | Channel breakdown | 1-168 hours | Returns per-channel metrics |
| df_session_by_outcome | Outcome distribution | 1-168 hours | Groups by heuristic_outcome |
| df_session_top_intents | Top 20 intents | 1-168 hours | Ranked by session count |

### Legacy Tools (for reference)

- df_get_dialogflow_status: Session counts and error rates
- df_backend_failures: 5xx backend errors
- df_backend_alerts: Threshold-based alerting
- Additional tools documented in system instructions

## Data Sources

### Primary Table: dfcx_session_metadata

Partition Key: session_start_time (required for all queries)

Key Fields:
- Session Info: session_id, start/end timestamps, duration, number_of_turns
- Routing: channel (voice/web/app), agent_id, location, project_id
- Outcomes: heuristic_outcome, has_deflection, has_wrapup, has_end_session
- CCAIP: ccaip_selected_menu_id/name, queue_id, call_id, deflection status
- Caller Info: ani, caller_ani, dnis, caller_dnis, sip_term
- Transfer Data: transfer_type_type, module, subtype, exttype
- Segmentation: division, market, region, service_type
- Parameters: final_session_parameters (JSON), final_language_code, head_intent

## Usage Examples

### Basic Session Search
Show me the last 50 sessions in the past 1 hour

### Filtered Search
Find phone channel sessions with deflection outcome in the last 2 hours

### Session Details
What are the complete details for session 065GQ2DnR9-Teu0AAWc1_sV_A?

### Analytics
What are the session analytics for the last 3 hours?
Show me session breakdown by channel for the last hour
What are the top intents in the past 2 hours?

See PROMPTS.md for comprehensive test scenarios.

## Configuration

### BigQuery Requirements

1. Project ID: dxp-cloud-ivr-prod-751497
2. Dataset: dfcx_analytics
3. Service Account: Must have bigquery.jobs.create and bigquery.data.viewer permissions
4. Partition Filtering: All queries MUST include session_start_time filter for performance

### Time Windows

- Default: 24 hours
- Maximum: 168 hours (7 days)
- Timezone: All timestamps converted to EST (America/New_York)

## Technical Details

### Query Performance Optimization

- Partition Elimination: Required WHERE clause on session_start_time
- Index Usage: Queries leverage session_id and timestamp indexes
- Row Limits: Default 50 rows, max 100 to prevent timeouts
- Async Execution: All BigQuery queries run asynchronously with retry logic

### Error Handling

- Partition Errors: Automatically suggest adding time filter
- Session Not Found: Recommends increasing time window up to 7 days
- Timeout: Reduces query complexity or limits result set
- Permission Denied: Reports missing BigQuery IAM roles

## Development

### Adding New Tools

1. Define SQL query in queries.py with partition filter
2. Implement method in DialogflowTools class in tools.py
3. Create ADK wrapper function
4. Update agent.py system instructions with tool description
5. Add test prompts to PROMPTS.md

### Testing

Run test suite with:
python -m pytest tests/test_dialogflow_tools.py

Manual testing via prompts in PROMPTS.md

## Limitations

- Time Range: Maximum 7 days of historical data
- Result Size: Limited to 100 sessions per query
- Partition Dependency: Cannot query without time filter
- Real-time Lag: Data ingestion delay ~1-2 minutes
- CCAIP Fields: May be null for non-telephony sessions

## Troubleshooting

### "Cannot query without partition elimination"
Solution: All queries require session_start_time filter. Ensure hours parameter is passed.

### "Session not found"
Solution: Increase time window (up to 168 hours). Check session_id spelling.

### "Permission denied on BigQuery"
Solution: Verify service account has roles/bigquery.jobUser and roles/bigquery.dataViewer.

### Slow query performance
Solution: Reduce time window, add more filters (agent_id, channel), or decrease limit.

## References

- BigQuery Best Practices: https://cloud.google.com/bigquery/docs/best-practices
- Dialogflow CX Documentation: https://cloud.google.com/dialogflow/cx/docs
- CCAIP Integration Guide: https://cloud.google.com/contact-center/docs

## Changelog

### v1.0.0 (2026-02-05)
- Added 6 session metadata tools
- Partition filter support for all queries
- EST timezone conversion
- CCAIP field integration
- Comprehensive error handling

## Contributing

When adding new features:
1. Update SQL in queries.py with partition filter
2. Document tool in this README and agent.py
3. Add test prompts to PROMPTS.md
4. Test with various time windows and filters
5. Update changelog

## License

Internal use only. See parent project for license details.
