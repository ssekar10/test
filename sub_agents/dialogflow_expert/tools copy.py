"""Dialogflow CX tools for discovery, configuration, and analytics."""

import os
import json
import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from google.auth import default
from google.cloud import monitoring_v3
from google.cloud import bigquery
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../master_agent'))
from utils import bigquery_rate_limiter, async_with_retry, response_manager


# Dialogflow CX client with fallback
try:
    from google.cloud import dialogflowcx_v3 as dialogflow_cx
    from google.api_core import client_options as client_options_lib
    from google.api_core import exceptions
    DIALOGFLOW_CX_AVAILABLE = True
except ImportError:
    DIALOGFLOW_CX_AVAILABLE = False
    print("[DialogflowTools] WARNING: google-cloud-dialogflow-cx not installed")

from . import config
from . import queries

# Load environment variables from env/.env.dev (same pattern as Cloud Run expert)
env_file = os.path.join(os.getcwd(), "env", ".env.dev")
if os.path.exists(env_file):
    load_dotenv(dotenv_path=env_file, override=True)
    print(f"[INFO] Loaded environment from: {env_file}")
else:
    print(f"[WARNING] Environment file not found: {env_file}")

# Timezone constant
EST_TZ = ZoneInfo("America/New_York")

# Rate limiting & retry configuration
MAX_RETRIES = 5
INITIAL_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 60.0     # seconds


@dataclass
class RateLimiter:
    """Simple rate limiter with exponential backoff."""
    request_count: int = 0
    last_request_time: float = time.time()
    backoff_time: float = 0.0

    async def wait_if_needed(self) -> None:
        if self.backoff_time > 0:
            print(f"[RATE_LIMIT] Backing off for {self.backoff_time:.2f}s")
            await asyncio.sleep(self.backoff_time)
            self.backoff_time = 0.0

        elapsed = time.time() - self.last_request_time
        if elapsed < 0.1:  # 100ms minimum between requests
            await asyncio.sleep(0.1 - elapsed)
        self.last_request_time = time.time()
        self.request_count += 1

    def set_backoff(self, attempt: int) -> None:
        self.backoff_time = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)


class DialogflowTools:
    """Toolset for Dialogflow CX operations with scale & resilience."""

    def __init__(self, project_id: Optional[str] = None):
        credentials, default_project = default()

        self.project_id = (
            project_id
            or os.getenv("GCP_PROJECT_ID")
            or os.getenv("GOOGLE_CLOUD_PROJECT")
            or default_project
        )
        self.location = (
            os.getenv("GOOGLE_CLOUD_LOCATION")
            or os.getenv("LOCATION")
            or config.get_default_location()
        )
        print(f"[DialogflowTools] Using project={self.project_id}, default_location={self.location}")

        self.rate_limiter = RateLimiter()
        self.credentials = credentials

        # Monitoring client (kept for future use if needed)
        self.monitoring_client = monitoring_v3.MetricServiceClient()

        # ========================================
        # BIGQUERY CLIENT - SINGLE LOCATION
        # ========================================
        # Both alerting_monitoring and dfcx_analytics datasets are in us-central1
        self.bq_client = bigquery.Client(
            project=self.project_id, 
            location="us-central1"
        )
        
        # For backward compatibility
        self._bq_clients = {
            "us-central1": self.bq_client,
        }
        
        print(f"[DialogflowTools] BigQuery client initialized for us-central1")
        print(f"  - alerting_monitoring dataset ✓")
        print(f"  - dfcx_analytics dataset ✓")
        
    # ---------- Time helpers ----------

    def _get_current_est_time(self) -> datetime:
        return datetime.now(EST_TZ)

    def _to_est_string(self, dt: datetime) -> str:
        if dt is None:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        est_dt = dt.astimezone(EST_TZ)
        return est_dt.strftime("%Y-%m-%d %I:%M:%S %p EST")

    def _get_time_window_bounds(self, hours: int) -> Dict[str, str]:
        """Return ISO strings for BigQuery TIMESTAMP() function."""
        now_est = self._get_current_est_time()
        # Ensure we look back from NOW
        start_est = now_est - timedelta(hours=hours)
        
        # Convert to UTC for BigQuery comparison
        now_utc = now_est.astimezone(ZoneInfo("UTC"))
        start_utc = start_est.astimezone(ZoneInfo("UTC"))
        
        # Format as YYYY-MM-DD HH:MM:SS (BigQuery friendly)
        return {
            "start_ts_raw": start_utc.strftime("%Y-%m-%d %H:%M:%S"),
            "end_ts": now_utc.strftime("%Y-%m-%d %H:%M:%S"),
        }

    # ---------- Client helpers ----------

    def _get_regional_client(self, location: str, client_class):
        """Create a regional Dialogflow CX client with proper endpoint."""
        if not DIALOGFLOW_CX_AVAILABLE:
            return None
        try:
            if location in ("global", "", None):
                return client_class(credentials=self.credentials)
            api_endpoint = f"{location}-dialogflow.googleapis.com"
            client_options = client_options_lib.ClientOptions(api_endpoint=api_endpoint)
            return client_class(credentials=self.credentials, client_options=client_options)
        except Exception as e:
            print(f"[DialogflowTools] ERROR creating regional client for {location}: {e}")
            return None

    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff on rate limit errors."""
        for attempt in range(MAX_RETRIES):
            try:
                await self.rate_limiter.wait_if_needed()
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                return func(*args, **kwargs)
            except exceptions.ResourceExhausted as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                self.rate_limiter.set_backoff(attempt)
                print(f"[RETRY] Rate limit hit, attempt {attempt + 1}/{MAX_RETRIES}")
            except Exception as e:
                msg = str(e).lower()
                if "429" in msg or "quota" in msg or "resource_exhausted" in msg:
                    if attempt == MAX_RETRIES - 1:
                        raise
                    self.rate_limiter.set_backoff(attempt)
                    print(f"[RETRY] Quota error, attempt {attempt + 1}/{MAX_RETRIES}")
                else:
                    raise

    async def _run_bq_query(
        self, 
        sql: str, 
        params: Optional[Dict[str, Any]] = None,
        location: str = "us-central1"  # ← NEW: Location parameter with default
    ) -> List[Dict[str, Any]]:
        """Execute a parameterized BigQuery query with rate limiting and retries."""
        await bigquery_rate_limiter.acquire()
        try:
            job_config = bigquery.QueryJobConfig()
            bq_params: List[bigquery.ScalarQueryParameter] = []
            if params:
                for name, value in params.items():
                    if isinstance(value, int):
                        bq_params.append(bigquery.ScalarQueryParameter(name, "INT64", value))
                    elif isinstance(value, float):
                        bq_params.append(bigquery.ScalarQueryParameter(name, "FLOAT64", value))
                    elif isinstance(value, bool):
                        bq_params.append(bigquery.ScalarQueryParameter(name, "BOOL", value))
                    else:
                        bq_params.append(bigquery.ScalarQueryParameter(name, "STRING", str(value)))
                job_config.query_parameters = bq_params


            async def _run():
                # ← NEW: Select appropriate client based on location
                client = self._bq_clients.get(location, self.bq_client)
                
                query_job = client.query(sql, job_config=job_config)  # ← CHANGED: Use location-specific client
                result = query_job.result()
                rows: List[Dict[str, Any]] = []
                for row in result:
                    row_dict = dict(row)
                    # Robust JSON-safe conversion for every field
                    for key, val in row_dict.items():
                        # Convert datetime/date/time objects to ISO strings
                        if hasattr(val, 'isoformat'):
                            row_dict[key] = val.isoformat()
                        # Ensure any non-standard types are strings
                        elif not isinstance(val, (str, int, float, bool, type(None), list, dict)):
                            row_dict[key] = str(val)
                    rows.append(row_dict)
                return rows


            rows = await self._retry_with_backoff(_run)
            return rows
        except Exception as e:
            # Enhanced error message with location context
            print(f"[DialogflowTools] BQ Execution Error (location={location}): {str(e)}")
            raise


    # ---------- Session Metadata Queries (dfcx_session_metadata) ----------

    async def df_get_session_details(self, session_id: str, hours: int = 24) -> str:
        """Get detailed information for a specific Dialogflow session.
        
        Args:
            session_id: The session ID to search for
            hours: Time window to search (default 24 hours, max 168 hours/7 days)
        """
        try:
            bounds = self._get_time_window_bounds(hours)
            sql = queries.DF_SESSION_DETAILS
            params = {
                "session_id": session_id,
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"]
            }
            rows = await self._run_bq_query(sql, params)
            
            if not rows:
                return json.dumps({
                    "session_id": session_id,
                    "search_window_hours": hours,
                    "error": "Session not found",
                    "note": f"Session '{session_id}' not found in the last {hours} hours. Try increasing the time window (up to 168 hours/7 days) or check if the session_id is correct."
                }, indent=2)
            
            session = rows[0]
            now_est = self._get_current_est_time()
            
            return json.dumps({
                "source": "dfcx_analytics.dfcx_session_metadata",
                "search_window_hours": hours,
                "session": session,
                "query_time_est": self._to_est_string(now_est)
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({
                "error": str(e),
                "trace": traceback.format_exc(),
                "tool": "df_get_session_details"
            }, indent=2)        


    async def df_search_sessions(
        self,
        hours: int = 1,
        agent_id: Optional[str] = None,
        channel: Optional[str] = None,
        outcome: Optional[str] = None,
        limit: int = 50
    ) -> str:
        """Search for Dialogflow sessions with optional filters."""
        try:
            bounds = self._get_time_window_bounds(hours)
            
            # Build dynamic SQL with proper WHERE clauses
            base_sql = f"""
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
            FROM {queries.DFCX_SESSION_METADATA_TABLE}
            WHERE session_start_time BETWEEN TIMESTAMP(@start_ts_raw) AND TIMESTAMP(@end_ts)
            """
            
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"],
                "limit": limit
            }
            
            # Add optional filters
            if agent_id:
                base_sql += "  AND agent_id = @agent_id\n"
                params["agent_id"] = agent_id
            
            if channel:
                base_sql += "  AND channel = @channel\n"
                params["channel"] = channel
            
            if outcome:
                base_sql += "  AND heuristic_outcome = @outcome\n"
                params["outcome"] = outcome
            
            base_sql += "ORDER BY session_start_time DESC\nLIMIT @limit"
            
            rows = await self._run_bq_query(base_sql, params)
            now_est = self._get_current_est_time()
            
            return json.dumps({
                "source": "dfcx_analytics.dfcx_session_metadata",
                "window_hours": hours,
                "filters": {
                    "agent_id": agent_id,
                    "channel": channel,
                    "outcome": outcome,
                    "limit": limit
                },
                "session_count": len(rows),
                "sessions": rows,
                "query_time_est": self._to_est_string(now_est)
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({
                "error": str(e),
                "trace": traceback.format_exc(),
                "tool": "df_search_sessions"
            }, indent=2)


    async def df_session_analytics(self, hours: int = 1) -> str:
        """Get aggregated session analytics over time."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql = queries.DF_SESSION_ANALYTICS
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"]
            }
            rows = await self._run_bq_query(sql, params)
            
            # Calculate totals
            total_sessions = sum(r.get("total_sessions", 0) for r in rows)
            total_deflections = sum(r.get("deflection_count", 0) for r in rows)
            total_wrapups = sum(r.get("wrapup_count", 0) for r in rows)
            total_incomplete = sum(r.get("incomplete_sessions", 0) for r in rows)
            
            now_est = self._get_current_est_time()
            
            return json.dumps({
                "source": "dfcx_analytics.dfcx_session_metadata",
                "window_hours": hours,
                "summary": {
                    "total_sessions": total_sessions,
                    "deflection_count": total_deflections,
                    "deflection_rate_percent": round(100 * total_deflections / total_sessions, 2) if total_sessions > 0 else 0,
                    "wrapup_count": total_wrapups,
                    "incomplete_sessions": total_incomplete
                },
                "timeseries": rows,
                "query_time_est": self._to_est_string(now_est)
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({
                "error": str(e),
                "trace": traceback.format_exc(),
                "tool": "df_session_analytics"
            }, indent=2)

    async def df_session_by_channel(self, hours: int = 1) -> str:
        """Get session breakdown by channel."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql = queries.DF_SESSION_BY_CHANNEL
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"]
            }
            rows = await self._run_bq_query(sql, params)
            now_est = self._get_current_est_time()
            
            return json.dumps({
                "source": "dfcx_analytics.dfcx_session_metadata",
                "window_hours": hours,
                "channels": rows,
                "query_time_est": self._to_est_string(now_est)
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({
                "error": str(e),
                "trace": traceback.format_exc(),
                "tool": "df_session_by_channel"
            }, indent=2)

    async def df_session_by_outcome(self, hours: int = 1) -> str:
        """Get session breakdown by heuristic outcome."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql = queries.DF_SESSION_BY_OUTCOME
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"]
            }
            rows = await self._run_bq_query(sql, params)
            now_est = self._get_current_est_time()
            
            return json.dumps({
                "source": "dfcx_analytics.dfcx_session_metadata",
                "window_hours": hours,
                "outcomes": rows,
                "query_time_est": self._to_est_string(now_est)
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({
                "error": str(e),
                "trace": traceback.format_exc(),
                "tool": "df_session_by_outcome"
            }, indent=2)

    async def df_session_top_intents(self, hours: int = 1) -> str:
        """Get top 20 intents by session count."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql = queries.DF_SESSION_TOP_INTENTS
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"]
            }
            rows = await self._run_bq_query(sql, params)
            now_est = self._get_current_est_time()
            
            return json.dumps({
                "source": "dfcx_analytics.dfcx_session_metadata",
                "window_hours": hours,
                "top_intents": rows,
                "query_time_est": self._to_est_string(now_est)
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({
                "error": str(e),
                "trace": traceback.format_exc(),
                "tool": "df_session_top_intents"
            }, indent=2)




    # ---------- Agent discovery & configuration ----------

    async def list_dialogflow_agents(self, location: Optional[str] = None) -> str:
        """List Dialogflow agents in a specific location."""
        try:
            if not DIALOGFLOW_CX_AVAILABLE:
                return json.dumps(
                    {
                        "error": "Dialogflow CX client not available. Install: google-cloud-dialogflow-cx",
                        "project_id": self.project_id,
                        "tool": "list_dialogflow_agents",
                    },
                    indent=2,
                )
            location = location or self.location
            parent = f"projects/{self.project_id}/locations/{location}"
            print(f"[DialogflowTools] Listing Dialogflow agents in location={location}, project={self.project_id}")
            try:
                agents_client = self._get_regional_client(location, dialogflow_cx.AgentsClient)
                if not agents_client:
                    return json.dumps(
                        {
                            "error": "Failed to create regional client",
                            "location": location,
                            "project_id": self.project_id,
                        },
                        indent=2,
                    )
                agents_result = await self._retry_with_backoff(agents_client.list_agents, parent=parent)
                agent_list: List[Dict[str, Any]] = []
                for agent in agents_result:
                    agent_list.append(
                        {
                            "name": agent.display_name,
                            "id": agent.name.split("/")[-1],
                            "resource_name": agent.name,
                            "default_language": agent.default_language_code,
                            "time_zone": agent.time_zone,
                        }
                    )
                return json.dumps(
                    {
                        "project_id": self.project_id,
                        "location": location,
                        "agent_count": len(agent_list),
                        "agents": agent_list,
                        "query_time_est": self._to_est_string(self._get_current_est_time()),
                    },
                    indent=2,
                )
            except Exception as e:
                import traceback
                error_msg = str(e)
                print(f"[DialogflowTools] ERROR listing agents in {parent}: {error_msg}\n{traceback.format_exc()}")
                if "PERMISSION_DENIED" in error_msg:
                    note = "Permission denied. Ensure the service account has Dialogflow API Reader/Admin role."
                elif "NOT_FOUND" in error_msg or "UNIMPLEMENTED" in error_msg:
                    note = f"Location '{location}' may not support Dialogflow CX or has no agents."
                elif "API has not been used" in error_msg or "FAILED_PRECONDITION" in error_msg:
                    note = "Dialogflow CX API is not enabled. Enable it in the Cloud Console."
                else:
                    note = "Failed to list agents. Check API enablement and IAM permissions."
                return json.dumps(
                    {
                        "project_id": self.project_id,
                        "location": location,
                        "error": error_msg,
                        "note": note,
                    },
                    indent=2,
                )
        except Exception as e:
            import traceback
            return json.dumps(
                {"error": str(e), "error_details": traceback.format_exc(), "tool": "list_dialogflow_agents"},
                indent=2,
            )

    async def get_agent_configuration(
        self,
        agent_id: str,
        location: Optional[str] = None,
    ) -> str:
        """Get detailed configuration for a Dialogflow agent (no cache)."""
        try:
            if not DIALOGFLOW_CX_AVAILABLE:
                return json.dumps(
                    {"error": "Dialogflow CX client not available.", "agent_id": agent_id},
                    indent=2,
                )
            location = location or self.location

            # Parse agent_id (display name or full resource)
            if "/" in agent_id and agent_id.startswith("projects/"):
                parts = agent_id.split("/")
                location = parts[3] if len(parts) >= 6 else location
                agent_name = agent_id
            else:
                # search by display name
                print(f"[DEBUG] Searching for agent '{agent_id}' in location '{location}'")
                agents_client = self._get_regional_client(location, dialogflow_cx.AgentsClient)
                agent_name = None
                if agents_client:
                    try:
                        parent = f"projects/{self.project_id}/locations/{location}"
                        agents_result = await self._retry_with_backoff(agents_client.list_agents, parent=parent)
                        candidate = None
                        aid_lower = agent_id.lower()
                        for a in agents_result:
                            if a.display_name.lower() == aid_lower:
                                candidate = a
                                break
                        if not candidate:
                            for a in agents_result:
                                if aid_lower in a.display_name.lower():
                                    candidate = a
                                    break
                        if not candidate:
                            return json.dumps(
                                {
                                    "agent_id": agent_id,
                                    "location": location,
                                    "error": f"Agent '{agent_id}' not found in location '{location}'",
                                },
                                indent=2,
                            )
                        agent_name = candidate.name
                        print(f"[DEBUG] Found agent: {candidate.display_name}")
                    except Exception as list_err:
                        print(f"[WARN] Could not list agents: {list_err}")
                        agent_name = f"projects/{self.project_id}/locations/{location}/agents/{agent_id}"
                else:
                    agent_name = f"projects/{self.project_id}/locations/{location}/agents/{agent_id}"

            agents_client = self._get_regional_client(location, dialogflow_cx.AgentsClient)
            if not agents_client:
                return json.dumps(
                    {"agent_id": agent_id, "error": f"Could not create client for location {location}"},
                    indent=2,
                )
            agent = await self._retry_with_backoff(agents_client.get_agent, name=agent_name)
            cfg = {
                "agent_id": agent.name.split("/")[-1],
                "display_name": agent.display_name,
                "location": location,
                "resource_name": agent.name,
                "default_language": agent.default_language_code,
                "supported_languages": list(agent.supported_language_codes) if agent.supported_language_codes else [],
                "time_zone": agent.time_zone,
                "description": agent.description or "",
                "avatar_uri": agent.avatar_uri or "",
                "enable_stackdriver_logging": agent.enable_stackdriver_logging,
                "enable_spell_correction": agent.enable_spell_correction,
                "query_time_est": self._to_est_string(self._get_current_est_time()),
            }
            return json.dumps(cfg, indent=2)
        except Exception as e:
            import traceback
            return json.dumps(
                {
                    "error": str(e),
                    "error_details": traceback.format_exc(),
                    "tool": "get_agent_configuration",
                },
                indent=2,
            )

    async def get_agent_configuration_cached(
        self,
        agent_id: str,
        location: Optional[str] = None,
    ) -> str:
        """Get agent configuration with caching (5min TTL)."""
        location = location or self.location
        cache_key = f"{agent_id}_{location}"
        cached = config.get_cached_config(cache_key)
        if cached:
            print(f"[CACHE HIT] Using cached config for {agent_id} in {location}")
            return cached
        print(f"[CACHE MISS] Fetching config for {agent_id} in {location}")
        cfg = await self.get_agent_configuration(agent_id, location)
        config.set_cached_config(cache_key, cfg)
        return cfg

    # ---------- Intents ----------

    async def list_intents(self, agent_id: str, location: Optional[str] = None) -> str:
        """List all intents for an agent (cached 5min)."""
        try:
            if not DIALOGFLOW_CX_AVAILABLE:
                return json.dumps(
                    {"error": "Dialogflow CX client not available.", "agent_id": agent_id},
                    indent=2,
                )
            location = location or self.location
            cache_key = f"{agent_id}_{location}_intents"
            cached = config.get_cached_intents(cache_key)
            if cached:
                print(f"[CACHE HIT] Using cached intents for {agent_id}")
                return cached

            if "/" in agent_id and agent_id.startswith("projects/"):
                parts = agent_id.split("/")
                location = parts[3] if len(parts) >= 6 else location
                agent_name = agent_id
            else:
                agent_name = f"projects/{self.project_id}/locations/{location}/agents/{agent_id}"

            intents_client = self._get_regional_client(location, dialogflow_cx.IntentsClient)
            if not intents_client:
                return json.dumps(
                    {"agent_id": agent_id, "error": f"Could not create client for location {location}"},
                    indent=2,
                )
            intents_result = await self._retry_with_backoff(intents_client.list_intents, parent=agent_name)
            intent_list: List[Dict[str, Any]] = []
            for intent in intents_result:
                intent_list.append(
                    {
                        "intent_id": intent.name.split("/")[-1],
                        "display_name": intent.display_name,
                        "training_phrase_count": len(intent.training_phrases),
                        "parameters": [p.id for p in intent.parameters] if intent.parameters else [],
                        "resource_name": intent.name,
                    }
                )
            result = json.dumps(
                {
                    "agent_id": agent_id,
                    "location": location,
                    "intent_count": len(intent_list),
                    "intents": intent_list,
                    "query_time_est": self._to_est_string(self._get_current_est_time()),
                },
                indent=2,
            )
            config.set_cached_intents(cache_key, result)
            return result
        except Exception as e:
            import traceback
            return json.dumps(
                {"error": str(e), "error_details": traceback.format_exc(), "tool": "list_intents"},
                indent=2,
            )

    async def get_intent_details(
        self,
        agent_id: str,
        intent_id: str,
        location: Optional[str] = None,
    ) -> str:
        """Get detailed information for a single intent including training phrases."""
        try:
            if not DIALOGFLOW_CX_AVAILABLE:
                return json.dumps(
                    {"error": "Dialogflow CX client not available.", "agent_id": agent_id, "intent_id": intent_id},
                    indent=2,
                )
            location = location or self.location

            # Resolve agent_name
            if "/" in agent_id and agent_id.startswith("projects/"):
                parts = agent_id.split("/")
                location = parts[3] if len(parts) >= 6 else location
                agent_name = agent_id
            else:
                # Try find agent by display name
                agents_client = self._get_regional_client(location, dialogflow_cx.AgentsClient)
                agent_name = None
                if agents_client:
                    try:
                        parent = f"projects/{self.project_id}/locations/{location}"
                        agents_result = await self._retry_with_backoff(agents_client.list_agents, parent=parent)
                        aid_lower = agent_id.lower()
                        candidate = None
                        for a in agents_result:
                            if a.display_name.lower() == aid_lower:
                                candidate = a
                                break
                        if not candidate:
                            for a in agents_result:
                                if aid_lower in a.display_name.lower():
                                    candidate = a
                                    break
                        if candidate:
                            agent_name = candidate.name
                            print(f"[DEBUG] Found agent for intent details: {candidate.display_name}")
                        else:
                            agent_name = f"projects/{self.project_id}/locations/{location}/agents/{agent_id}"
                    except Exception as list_err:
                        print(f"[WARN] Could not list agents: {list_err}")
                        agent_name = f"projects/{self.project_id}/locations/{location}/agents/{agent_id}"
                else:
                    agent_name = f"projects/{self.project_id}/locations/{location}/agents/{agent_id}"

            intents_client = self._get_regional_client(location, dialogflow_cx.IntentsClient)
            if not intents_client:
                return json.dumps(
                    {"agent_id": agent_id, "intent_id": intent_id, "error": f"Could not create client for location {location}"},
                    indent=2,
                )

            # Resolve intent_name (display_name or ID)
            if "/" in intent_id and "intents/" in intent_id:
                intent_name = intent_id
            else:
                # Search by display name
                print(f"[DEBUG] Searching for intent '{intent_id}'")
                intents_result = await self._retry_with_backoff(intents_client.list_intents, parent=agent_name)
                iid_lower = intent_id.lower()
                candidate_intent = None
                for it in intents_result:
                    if it.display_name.lower() == iid_lower:
                        candidate_intent = it
                        break
                if not candidate_intent:
                    for it in intents_result:
                        if iid_lower in it.display_name.lower():
                            candidate_intent = it
                            break
                if not candidate_intent:
                    return json.dumps(
                        {
                            "agent_id": agent_id,
                            "intent_id": intent_id,
                            "location": location,
                            "error": f"Intent '{intent_id}' not found",
                        },
                        indent=2,
                    )
                intent_name = candidate_intent.name
                print(f"[DEBUG] Found intent: {candidate_intent.display_name}")

            intent = await self._retry_with_backoff(intents_client.get_intent, name=intent_name)
            training_phrases: List[str] = []
            for phrase in intent.training_phrases:
                phrase_text = " ".join([part.text for part in phrase.parts])
                training_phrases.append(phrase_text)

            parameters: List[Dict[str, Any]] = []
            if intent.parameters:
                for param in intent.parameters:
                    info = {
                        "id": param.id,
                        "entity_type": param.entity_type,
                        "is_list": param.is_list,
                    }
                    if hasattr(param, "redact"):
                        info["redact"] = param.redact
                    parameters.append(info)

            labels = dict(intent.labels) if getattr(intent, "labels", None) else {}

            result = {
                "agent_id": agent_id,
                "location": location,
                "intent": {
                    "intent_id": intent.name.split("/")[-1],
                    "display_name": intent.display_name,
                    "training_phrases": training_phrases,
                    "training_phrase_count": len(training_phrases),
                    "parameters": parameters,
                    "parameter_count": len(parameters),
                    "labels": labels,
                    "resource_name": intent.name,
                },
                "query_time_est": self._to_est_string(self._get_current_est_time()),
            }
            return json.dumps(result, indent=2)
        except Exception as e:
            import traceback
            return json.dumps(
                {"error": str(e), "error_details": traceback.format_exc(), "tool": "get_intent_details"},
                indent=2,
            )

    # ---------- Webhooks ----------

    async def list_webhooks(self, agent_id: str, location: Optional[str] = None) -> str:
        """List configured webhooks for an agent (cached 5min)."""
        try:
            if not DIALOGFLOW_CX_AVAILABLE:
                return json.dumps(
                    {"error": "Dialogflow CX client not available.", "agent_id": agent_id},
                    indent=2,
                )
            location = location or self.location
            cache_key = f"{agent_id}_{location}_webhooks"
            cached = config.get_cached_webhooks(cache_key)
            if cached:
                print(f"[CACHE HIT] Using cached webhooks for {agent_id}")
                return cached

            if "/" in agent_id and agent_id.startswith("projects/"):
                parts = agent_id.split("/")
                location = parts[3] if len(parts) >= 6 else location
                agent_name = agent_id
            else:
                agent_name = f"projects/{self.project_id}/locations/{location}/agents/{agent_id}"

            webhooks_client = self._get_regional_client(location, dialogflow_cx.WebhooksClient)
            if not webhooks_client:
                return json.dumps(
                    {"agent_id": agent_id, "error": f"Could not create client for location {location}"},
                    indent=2,
                )

            webhooks_result = await self._retry_with_backoff(webhooks_client.list_webhooks, parent=agent_name)
            webhook_list: List[Dict[str, Any]] = []
            for webhook in webhooks_result:
                cfg: Dict[str, Any] = {
                    "webhook_id": webhook.name.split("/")[-1],
                    "display_name": webhook.display_name,
                    "resource_name": webhook.name,
                }
                if hasattr(webhook, "disabled"):
                    cfg["disabled"] = webhook.disabled
                # Generic Web Service
                if hasattr(webhook, "generic_web_service") and webhook.generic_web_service:
                    gws = webhook.generic_web_service
                    cfg["uri"] = getattr(gws, "uri", "N/A")
                    # timeout
                    timeout_seconds = 30
                    if hasattr(gws, "request_timeout") and gws.request_timeout:
                        try:
                            timeout_seconds = getattr(gws.request_timeout, "seconds", 30)
                        except Exception as timeout_error:
                            print(f"[WARN] Could not parse timeout for {webhook.display_name}: {timeout_error}")
                    cfg["timeout_seconds"] = timeout_seconds
                    if getattr(gws, "request_headers", None):
                        cfg["request_headers"] = dict(gws.request_headers)
                    if getattr(gws, "allowed_ca_certs", None):
                        cfg["has_ca_certs"] = True
                # Service Directory
                elif hasattr(webhook, "service_directory") and webhook.service_directory:
                    sd = webhook.service_directory
                    cfg["service_directory"] = {
                        "service": getattr(sd, "service", "N/A"),
                    }
                webhook_list.append(cfg)

            result = json.dumps(
                {
                    "agent_id": agent_id,
                    "location": location,
                    "webhook_count": len(webhook_list),
                    "webhooks": webhook_list,
                    "query_time_est": self._to_est_string(self._get_current_est_time()),
                    "note": (
                        "For webhook performance metrics, if webhook is Cloud Run-based, "
                        "use the Cloud Run specialist to analyze request counts, latency, and errors."
                    ),
                },
                indent=2,
            )
            config.set_cached_webhooks(cache_key, result)
            return result
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[ERROR] Failed to list webhooks: {error_details}")
            return json.dumps(
                {
                    "error": str(e),
                    "error_details": error_details,
                    "tool": "list_webhooks",
                    "agent_id": agent_id,
                },
                indent=2,
            )

    # ---------- BigQuery metrics tools (alerting_monitoring.dialogflow_metrics) ----------

    async def df_unique_sessions(
        self,
        hours: int = 1,
        bucket_minutes: int = 15,
    ) -> str:
        """Unique DF call sessions and total sessions over time."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql = queries.DF_UNIQUE_SESSIONS
            params = {
                "bucket_seconds": bucket_minutes * 60,
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"],
            }
            rows = await self._run_bq_query(sql, params)
            now_est = self._get_current_est_time()
            return json.dumps(
                {
                    "source": "alerting_monitoring.dialogflow_metrics",
                    "window_hours": hours,
                    "bucket_minutes": bucket_minutes,
                    "time_range_end_est": self._to_est_string(now_est),
                    "points": rows,
                },
                indent=2,
            )
        except Exception as e:
            import traceback
            return json.dumps(
                {"error": str(e), "error_details": traceback.format_exc(), "tool": "df_unique_sessions"},
                indent=2,
            )

    async def df_overall_response_times(
        self,
        hours: int = 1,
    ) -> str:
        """Average overall DF response time per minute."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql = queries.DF_OVERALL_RESPONSE_TIMES
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"],
            }
            rows = await self._run_bq_query(sql, params)
            now_est = self._get_current_est_time()
            return json.dumps(
                {
                    "source": "alerting_monitoring.dialogflow_metrics",
                    "window_hours": hours,
                    "time_range_end_est": self._to_est_string(now_est),
                    "points": rows,
                    "unit": "seconds",
                },
                indent=2,
            )
        except Exception as e:
            import traceback
            return json.dumps(
                {"error": str(e), "error_details": traceback.format_exc(), "tool": "df_overall_response_times"},
                indent=2,
            )

    async def df_overall_status_success_failure(
        self,
        hours: int = 1,
    ) -> str:
        """Unique success vs failure sessions over time."""
        try:
            bounds = self._get_time_window_bounds(hours)
            base_sql = queries.DF_OVERALL_STATUS
            params_fail = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"],
                "status": "failure",
            }
            params_success = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"],
                "status": "success",
            }
            failures = await self._run_bq_query(base_sql, params_fail)
            successes = await self._run_bq_query(base_sql, params_success)
            now_est = self._get_current_est_time()
            return json.dumps(
                {
                    "source": "alerting_monitoring.dialogflow_metrics",
                    "window_hours": hours,
                    "time_range_end_est": self._to_est_string(now_est),
                    "failures": failures,
                    "successes": successes,
                },
                indent=2,
            )
        except Exception as e:
            import traceback
            return json.dumps(
                {
                    "error": str(e),
                    "error_details": traceback.format_exc(),
                    "tool": "df_overall_status_success_failure",
                },
                indent=2,
            )

    async def df_failures_by_failure_reason(
        self,
        hours: int = 1,
    ) -> str:
        """Failures over time, broken down by failure_reason."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql_total = queries.DF_FAILURES_TOTAL
            sql_by_reason = queries.DF_FAILURES_BY_REASON
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"],
            }
            totals = await self._run_bq_query(sql_total, params)
            by_reason = await self._run_bq_query(sql_by_reason, params)
            now_est = self._get_current_est_time()
            return json.dumps(
                {
                    "source": "alerting_monitoring.dialogflow_metrics",
                    "window_hours": hours,
                    "time_range_end_est": self._to_est_string(now_est),
                    "totals": totals,
                    "by_failure_reason": by_reason,
                },
                indent=2,
            )
        except Exception as e:
            import traceback
            return json.dumps(
                {"error": str(e), "error_details": traceback.format_exc(), "tool": "df_failures_by_failure_reason"},
                indent=2,
            )

    async def df_backend_call_volume(
        self,
        hours: int = 1,
    ) -> str:
        """Backend call volume overall, by backend URI, and normalized URI."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql_total = queries.DF_BACKEND_TOTAL
            sql_by_backend = queries.DF_BACKEND_BY_URI
            sql_normalized = queries.DF_BACKEND_BY_URI_NORMALIZED
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"],
            }
            totals = await self._run_bq_query(sql_total, params)
            by_backend = await self._run_bq_query(sql_by_backend, params)
            normalized = await self._run_bq_query(sql_normalized, params)
            now_est = self._get_current_est_time()
            return json.dumps(
                {
                    "source": "alerting_monitoring.dialogflow_metrics",
                    "window_hours": hours,
                    "time_range_end_est": self._to_est_string(now_est),
                    "totals": totals,
                    "by_backend_uri": by_backend,
                    "by_normalized_backend": normalized,
                },
                indent=2,
            )
        except Exception as e:
            import traceback
            return json.dumps(
                {"error": str(e), "error_details": traceback.format_exc(), "tool": "df_backend_call_volume"},
                indent=2,
            )

    async def df_call_volume_by_flow(
        self,
        hours: int = 1,
    ) -> str:
        """Backend call volume grouped by flow_name."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql = queries.DF_CALL_VOLUME_BY_FLOW
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"],
            }
            rows = await self._run_bq_query(sql, params)
            now_est = self._get_current_est_time()
            return json.dumps(
                {
                    "source": "alerting_monitoring.dialogflow_metrics",
                    "window_hours": hours,
                    "time_range_end_est": self._to_est_string(now_est),
                    "by_flow_name": rows,
                },
                indent=2,
            )
        except Exception as e:
            import traceback
            return json.dumps(
                {"error": str(e), "error_details": traceback.format_exc(), "tool": "df_call_volume_by_flow"},
                indent=2,
            )

    async def df_backend_response_times(
        self,
        hours: int = 1,
    ) -> str:
        """Backend response times (excluding modem health check) by backend URI."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql = queries.DF_BACKEND_RESPONSE_TIMES
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"],
            }
            rows = await self._run_bq_query(sql, params)
            now_est = self._get_current_est_time()
            return json.dumps(
                {
                    "source": "alerting_monitoring.dialogflow_metrics",
                    "window_hours": hours,
                    "time_range_end_est": self._to_est_string(now_est),
                    "points": rows,
                    "unit": "ms",
                },
                indent=2,
            )
        except Exception as e:
            import traceback
            return json.dumps(
                {"error": str(e), "error_details": traceback.format_exc(), "tool": "df_backend_response_times"},
                indent=2,
            )

    async def df_backend_modem_health_response_times(
        self,
        hours: int = 1,
    ) -> str:
        """Backend response times for modem health check calls."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql_overall = queries.DF_BACKEND_RESPONSE_TIMES_OVERALL
            sql_modem = queries.DF_BACKEND_RESPONSE_TIMES_MODEM
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"],
            }
            overall = await self._run_bq_query(sql_overall, params)
            modem_only = await self._run_bq_query(sql_modem, params)
            now_est = self._get_current_est_time()
            return json.dumps(
                {
                    "source": "alerting_monitoring.dialogflow_metrics",
                    "window_hours": hours,
                    "time_range_end_est": self._to_est_string(now_est),
                    "overall": overall,
                    "modem_health_only": modem_only,
                    "unit": "ms",
                },
                indent=2,
            )
        except Exception as e:
            import traceback
            return json.dumps(
                {
                    "error": str(e),
                    "error_details": traceback.format_exc(),
                    "tool": "df_backend_modem_health_response_times",
                },
                indent=2,
            )

    async def df_backend_failures_by_http_code(
        self,
        hours: int = 1,
    ) -> str:
        """Backend failures grouped by HTTP status code."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql_total = queries.DF_BACKEND_FAILURES_HTTP_TOTAL
            sql_by_code = queries.DF_BACKEND_FAILURES_HTTP_BY_CODE
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"],
            }
            totals = await self._run_bq_query(sql_total, params)
            by_code = await self._run_bq_query(sql_by_code, params)
            now_est = self._get_current_est_time()
            return json.dumps(
                {
                    "source": "alerting_monitoring.dialogflow_metrics",
                    "window_hours": hours,
                    "time_range_end_est": self._to_est_string(now_est),
                    "totals": totals,
                    "by_http_code": by_code,
                },
                indent=2,
            )
        except Exception as e:
            import traceback
            return json.dumps(
                {
                    "error": str(e),
                    "error_details": traceback.format_exc(),
                    "tool": "df_backend_failures_by_http_code",
                },
                indent=2,
            )

    async def df_backend_failures_by_backend_uri(
        self,
        hours: int = 1,
    ) -> str:
        """Backend failures grouped by normalized backend URI and failure reason."""
        try:
            bounds = self._get_time_window_bounds(hours)
            sql_total = queries.DF_BACKEND_FAILURES_URI_TOTAL
            sql_by_uri = queries.DF_BACKEND_FAILURES_URI_BY_URL
            params = {
                "start_ts_raw": bounds["start_ts_raw"],
                "end_ts": bounds["end_ts"],
            }
            totals = await self._run_bq_query(sql_total, params)
            by_uri = await self._run_bq_query(sql_by_uri, params)
            now_est = self._get_current_est_time()
            return json.dumps(
                {
                    "source": "alerting_monitoring.dialogflow_metrics",
                    "window_hours": hours,
                    "time_range_end_est": self._to_est_string(now_est),
                    "totals": totals,
                    "by_backend_uri": by_uri,
                },
                indent=2,
            )
        except Exception as e:
            import traceback
            return json.dumps(
                {
                    "error": str(e),
                    "error_details": traceback.format_exc(),
                    "tool": "df_backend_failures_by_backend_uri",
                },
                indent=2,
            )

        # ========================================
    # CONVERSATION TRANSCRIPT ANALYTICS
    # (Optimized with 7-day default)
    # ========================================

    def _get_time_window_bounds_days(self, hours: int) -> dict:
        """Convert hours to time bounds, capped at 7 days for transcript queries."""
        now_est = self._get_current_est_time()
        # Cap at 7 days (168 hours) for performance
        capped_hours = min(hours, 168)
        start_est = now_est - timedelta(hours=capped_hours)
        
        now_utc = now_est.astimezone(ZoneInfo("UTC"))
        start_utc = start_est.astimezone(ZoneInfo("UTC"))
        
        return {
            "start_ts_raw": start_utc.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"),
            "end_ts": now_utc.replace(tzinfo=None).strftime("%Y-%m-%d %H:%M:%S"),
        }

    async def df_intent_confidence_distribution(self, hours: int = 24) -> str:
        """Intent matching confidence distribution. Default: last 24 hours."""
        try:
            bounds = self._get_time_window_bounds_days(hours)
            rows = await self._run_bq_query(
                queries.DF_INTENT_CONFIDENCE_DISTRIBUTION,
                params={
                    "start_ts_raw": bounds["start_ts_raw"],
                    "end_ts": bounds["end_ts"]
                },
                location="us-central1"
            )
            now_est = self._get_current_est_time()
            return json.dumps({
                "window_hours": min(hours, 168),
                "query_time_est": self._to_est_string(now_est),
                "confidence_distribution": rows
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({"error": str(e), "trace": traceback.format_exc()}, indent=2)

    async def df_fallback_analysis(self, hours: int = 24) -> str:
        """Deflection and fallback tracking. Default: last 24 hours."""
        try:
            bounds = self._get_time_window_bounds_days(hours)
            rows = await self._run_bq_query(
                queries.DF_FALLBACK_ANALYSIS,
                params={
                    "start_ts_raw": bounds["start_ts_raw"],
                    "end_ts": bounds["end_ts"]
                },
                location="us-central1"
            )
            now_est = self._get_current_est_time()
            result = rows[0] if rows else {}
            return json.dumps({
                "window_hours": min(hours, 168),
                "query_time_est": self._to_est_string(now_est),
                "fallback_sessions": result.get("fallback_sessions", 0),
                "fallback_turns": result.get("fallback_turns", 0),
                "fallback_session_rate_percent": result.get("fallback_session_rate", 0),
                "sample_unresolved_utterances": result.get("sample_unresolved_utterances", [])
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({"error": str(e), "trace": traceback.format_exc()}, indent=2)

    async def df_flow_traversal(self, hours: int = 24) -> str:
        """Flow and page traversal heatmap. Default: last 24 hours."""
        try:
            bounds = self._get_time_window_bounds_days(hours)
            rows = await self._run_bq_query(
                queries.DF_FLOW_TRAVERSAL,
                params={
                    "start_ts_raw": bounds["start_ts_raw"],
                    "end_ts": bounds["end_ts"]
                },
                location="us-central1"
            )
            now_est = self._get_current_est_time()
            return json.dumps({
                "window_hours": min(hours, 168),
                "query_time_est": self._to_est_string(now_est),
                "flow_page_visits": rows
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({"error": str(e), "trace": traceback.format_exc()}, indent=2)

    async def df_session_replay(self, session_id: str, days: int = 7) -> str:
        """Complete turn-by-turn conversation transcript. Default: search last 7 days."""
        try:
            query_with_params = queries.DF_SESSION_REPLAY.replace("{{session_id}}", session_id).replace("{{days}}", str(days))
            rows = await self._run_bq_query(
                query_with_params,
                params=None,
                location="us-central1"
            )
            now_est = self._get_current_est_time()
            
            if not rows:
                return json.dumps({
                    "session_id": session_id,
                    "error": "Session not found",
                    "note": f"No session found in the last {days} days. Try increasing the search window.",
                    "query_time_est": self._to_est_string(now_est)
                }, indent=2)
            
            return json.dumps({
                "session_id": session_id,
                "searched_last_days": days,
                "query_time_est": self._to_est_string(now_est),
                "total_turns": len(rows),
                "transcript": rows
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({"error": str(e), "trace": traceback.format_exc()}, indent=2)

    async def df_execution_complexity(self, hours: int = 24, min_turns: int = 20) -> str:
        """Sessions with high conversation turn counts. Default: last 24 hours."""
        try:
            bounds = self._get_time_window_bounds_days(hours)
            rows = await self._run_bq_query(
                queries.DF_EXECUTION_COMPLEXITY,
                params={
                    "start_ts_raw": bounds["start_ts_raw"],
                    "end_ts": bounds["end_ts"],
                    "min_turns": min_turns
                },
                location="us-central1"
            )
            now_est = self._get_current_est_time()
            return json.dumps({
                "window_hours": min(hours, 168),
                "min_turns_threshold": min_turns,
                "query_time_est": self._to_est_string(now_est),
                "complex_sessions": rows
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({"error": str(e), "trace": traceback.format_exc()}, indent=2)

    async def df_voice_latency(self, hours: int = 24) -> str:
        """Voice channel input/output audio latency analysis. Default: last 24 hours."""
        try:
            bounds = self._get_time_window_bounds_days(hours)
            rows = await self._run_bq_query(
                queries.DF_VOICE_LATENCY,
                params={
                    "start_ts_raw": bounds["start_ts_raw"],
                    "end_ts": bounds["end_ts"]
                },
                location="us-central1"
            )
            now_est = self._get_current_est_time()
            return json.dumps({
                "window_hours": min(hours, 168),
                "query_time_est": self._to_est_string(now_est),
                "voice_latency_timeseries": rows
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({"error": str(e), "trace": traceback.format_exc()}, indent=2)

    async def df_response_analysis(self, hours: int = 24) -> str:
        """Most common agent responses by page. Default: last 24 hours."""
        try:
            bounds = self._get_time_window_bounds_days(hours)
            rows = await self._run_bq_query(
                queries.DF_RESPONSE_ANALYSIS,
                params={
                    "start_ts_raw": bounds["start_ts_raw"],
                    "end_ts": bounds["end_ts"]
                },
                location="us-central1"
            )
            now_est = self._get_current_est_time()
            return json.dumps({
                "window_hours": min(hours, 168),
                "query_time_est": self._to_est_string(now_est),
                "top_responses": rows
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({"error": str(e), "trace": traceback.format_exc()}, indent=2)

    async def df_event_analysis(self, hours: int = 24) -> str:
        """Event triggers by page and flow. Default: last 24 hours."""
        try:
            bounds = self._get_time_window_bounds_days(hours)
            rows = await self._run_bq_query(
                queries.DF_EVENT_ANALYSIS,
                params={
                    "start_ts_raw": bounds["start_ts_raw"],
                    "end_ts": bounds["end_ts"]
                },
                location="us-central1"
            )
            now_est = self._get_current_est_time()
            return json.dumps({
                "window_hours": min(hours, 168),
                "query_time_est": self._to_est_string(now_est),
                "event_triggers": rows
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({"error": str(e), "trace": traceback.format_exc()}, indent=2)

    async def df_failed_sessions_export(self, hours: int = 24, limit: int = 50) -> str:
        """Export sessions that ended in fallback or had issues. Default: last 24 hours."""
        try:
            bounds = self._get_time_window_bounds_days(hours)
            rows = await self._run_bq_query(
                queries.DF_FAILED_SESSIONS_EXPORT,
                params={
                    "start_ts_raw": bounds["start_ts_raw"],
                    "end_ts": bounds["end_ts"],
                    "limit": limit
                },
                location="us-central1"
            )
            now_est = self._get_current_est_time()
            return json.dumps({
                "window_hours": min(hours, 168),
                "query_time_est": self._to_est_string(now_est),
                "failed_sessions_count": len(rows),
                "failed_sessions": rows
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({"error": str(e), "trace": traceback.format_exc()}, indent=2)

    async def df_conversation_summary(self, session_id: str, days: int = 7) -> str:
        """Quick conversation statistics for a session. Default: search last 7 days."""
        try:
            query_with_params = queries.DF_CONVERSATION_SUMMARY.replace("{{session_id}}", session_id).replace("{{days}}", str(days))
            rows = await self._run_bq_query(
                query_with_params,
                params=None,
                location="us-central1"
            )
            now_est = self._get_current_est_time()
            result = rows[0] if rows else {}
            
            if not result:
                return json.dumps({
                    "session_id": session_id,
                    "error": "Session not found",
                    "note": f"No session found in the last {days} days.",
                    "query_time_est": self._to_est_string(now_est)
                }, indent=2)
            
            return json.dumps({
                "session_id": session_id,
                "searched_last_days": days,
                "query_time_est": self._to_est_string(now_est),
                "summary": result
            }, indent=2)
        except Exception as e:
            import traceback
            return json.dumps({"error": str(e), "trace": traceback.format_exc()}, indent=2)


# ---------- ADK wrappers ----------

async def list_dialogflow_agents(location: Optional[str] = None) -> str:
    tools = DialogflowTools()
    return await tools.list_dialogflow_agents(location)


async def get_agent_details(agent_id: str, location: Optional[str] = None) -> str:
    tools = DialogflowTools()
    return await tools.get_agent_configuration(agent_id, location)


async def get_agent_details_fast(agent_id: str, location: Optional[str] = None) -> str:
    tools = DialogflowTools()
    return await tools.get_agent_configuration_cached(agent_id, location)


async def list_intents(agent_id: str, location: Optional[str] = None) -> str:
    tools = DialogflowTools()
    return await tools.list_intents(agent_id, location)


async def get_intent_details(agent_id: str, intent_id: str, location: Optional[str] = None) -> str:
    tools = DialogflowTools()
    return await tools.get_intent_details(agent_id, intent_id, location)


async def list_webhooks(agent_id: str, location: Optional[str] = None) -> str:
    tools = DialogflowTools()
    return await tools.list_webhooks(agent_id, location)


async def df_unique_sessions(
    hours: int = 1,
    bucket_minutes: int = 15,
) -> str:
    tools = DialogflowTools()
    return await tools.df_unique_sessions(hours, bucket_minutes)


async def df_overall_response_times(
    hours: int = 1,
) -> str:
    tools = DialogflowTools()
    return await tools.df_overall_response_times(hours)


async def df_overall_status_success_failure(
    hours: int = 1,
) -> str:
    tools = DialogflowTools()
    return await tools.df_overall_status_success_failure(hours)


async def df_failures_by_failure_reason(
    hours: int = 1,
) -> str:
    tools = DialogflowTools()
    return await tools.df_failures_by_failure_reason(hours)


async def df_backend_call_volume(
    hours: int = 1,
) -> str:
    tools = DialogflowTools()
    return await tools.df_backend_call_volume(hours)


async def df_call_volume_by_flow(
    hours: int = 1,
) -> str:
    tools = DialogflowTools()
    return await tools.df_call_volume_by_flow(hours)


async def df_backend_response_times(
    hours: int = 1,
) -> str:
    tools = DialogflowTools()
    return await tools.df_backend_response_times(hours)


async def df_backend_modem_health_response_times(
    hours: int = 1,
) -> str:
    tools = DialogflowTools()
    return await tools.df_backend_modem_health_response_times(hours)


async def df_backend_failures_by_http_code(
    hours: int = 1,
) -> str:
    tools = DialogflowTools()
    return await tools.df_backend_failures_by_http_code(hours)


async def df_backend_failures_by_backend_uri(
    hours: int = 1,
) -> str:
    tools = DialogflowTools()
    return await tools.df_backend_failures_by_backend_uri(hours)


# Session metadata wrappers
async def df_get_session_details(session_id: str, hours: int = 24) -> str:
    return await DialogflowTools().df_get_session_details(session_id, hours)

async def df_search_sessions(
    hours: int = 1,
    agent_id: Optional[str] = None,
    channel: Optional[str] = None,
    outcome: Optional[str] = None,
    limit: int = 50
) -> str:
    return await DialogflowTools().df_search_sessions(hours, agent_id, channel, outcome, limit)

async def df_session_analytics(hours: int = 1) -> str:
    return await DialogflowTools().df_session_analytics(hours)

async def df_session_by_channel(hours: int = 1) -> str:
    return await DialogflowTools().df_session_by_channel(hours)

async def df_session_by_outcome(hours: int = 1) -> str:
    return await DialogflowTools().df_session_by_outcome(hours)

async def df_session_top_intents(hours: int = 1) -> str:
    return await DialogflowTools().df_session_top_intents(hours)

# ========================================
# ADK WRAPPERS - Transcript Analytics
# ========================================

async def df_intent_confidence_distribution(hours: int = 24) -> str:
    """Get intent matching confidence distribution. Max 168 hours (7 days)."""
    tools = DialogflowTools()
    return await tools.df_intent_confidence_distribution(hours)

async def df_fallback_analysis(hours: int = 24) -> str:
    """Get deflection and fallback tracking. Max 168 hours (7 days)."""
    tools = DialogflowTools()
    return await tools.df_fallback_analysis(hours)

async def df_flow_traversal(hours: int = 24) -> str:
    """Get flow and page traversal heatmap. Max 168 hours (7 days)."""
    tools = DialogflowTools()
    return await tools.df_flow_traversal(hours)

async def df_session_replay(session_id: str, days: int = 7) -> str:
    """Get complete turn-by-turn conversation transcript. Searches last N days."""
    tools = DialogflowTools()
    return await tools.df_session_replay(session_id, days)

async def df_execution_complexity(hours: int = 24, min_turns: int = 20) -> str:
    """Get sessions with high conversation turn counts. Max 168 hours (7 days)."""
    tools = DialogflowTools()
    return await tools.df_execution_complexity(hours, min_turns)

async def df_voice_latency(hours: int = 24) -> str:
    """Get voice channel latency analysis. Max 168 hours (7 days)."""
    tools = DialogflowTools()
    return await tools.df_voice_latency(hours)

async def df_response_analysis(hours: int = 24) -> str:
    """Get most common agent responses. Max 168 hours (7 days)."""
    tools = DialogflowTools()
    return await tools.df_response_analysis(hours)

async def df_event_analysis(hours: int = 24) -> str:
    """Get event triggers by page and flow. Max 168 hours (7 days)."""
    tools = DialogflowTools()
    return await tools.df_event_analysis(hours)

async def df_failed_sessions_export(hours: int = 24, limit: int = 50) -> str:
    """Export sessions that ended in fallback. Max 168 hours (7 days)."""
    tools = DialogflowTools()
    return await tools.df_failed_sessions_export(hours, limit)

async def df_conversation_summary(session_id: str, days: int = 7) -> str:
    """Get quick conversation statistics for a session. Searches last N days."""
    tools = DialogflowTools()
    return await tools.df_conversation_summary(session_id, days)

