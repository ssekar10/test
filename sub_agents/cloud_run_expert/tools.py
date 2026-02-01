"""GCP Cloud Run API Tools - Discovery, Configuration, and Metrics with Scale & Resilience."""

import os
import asyncio
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from google.cloud import asset_v1, monitoring_v3, run_v2, logging_v2
from google.auth import default
from google.api_core import retry, exceptions
import json
from dotenv import load_dotenv
import time

# Performance optimization imports
from sub_agents.cloud_run_expert.config import (
    get_cached_config,
    set_cached_config,
    DEFAULT_REGION,
    COMMON_REGIONS,
    PARALLEL_REGION_QUERIES,
    MAX_PARALLEL_CALLS
)

# Load environment variables from env/.env.dev
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
MAX_BACKOFF = 60.0  # seconds
LOGS_PAGE_SIZE = 1000  # Reduced from 10000 for better rate limiting
CHUNK_HOURS = 6  # Time window chunk size for multi-day queries


class RateLimiter:
    """Simple rate limiter with exponential backoff."""
    
    def __init__(self):
        self.request_count = 0
        self.last_request_time = time.time()
        self.backoff_time = 0
    
    async def wait_if_needed(self):
        """Wait if we're hitting rate limits."""
        if self.backoff_time > 0:
            print(f"[RATE_LIMIT] Backing off for {self.backoff_time:.2f}s")
            await asyncio.sleep(self.backoff_time)
            self.backoff_time = 0
        
        # Minimum delay between requests
        elapsed = time.time() - self.last_request_time
        if elapsed < 0.1:  # 100ms minimum between requests
            await asyncio.sleep(0.1 - elapsed)
        
        self.last_request_time = time.time()
        self.request_count += 1
    
    def set_backoff(self, attempt: int):
        """Set exponential backoff time."""
        self.backoff_time = min(INITIAL_BACKOFF * (2 ** attempt), MAX_BACKOFF)


class CloudRunTools:
    """Toolset for Cloud Run operations with scale & resilience."""
    
    def __init__(self, project_id: Optional[str] = None):
        """Initialize GCP clients."""
        credentials, default_project = default()
        
        self.project_id = (
            project_id or 
            os.getenv("GCP_PROJECT_ID") or 
            os.getenv("GOOGLE_CLOUD_PROJECT") or 
            default_project
        )
        
        print(f"[CloudRunTools] Using GCP Project: {self.project_id}")
        
        self.asset_client = asset_v1.AssetServiceClient(credentials=credentials)
        self.run_client = run_v2.ServicesClient(credentials=credentials)
        self.monitoring_client = monitoring_v3.MetricServiceClient(credentials=credentials)
        self.logging_client = logging_v2.Client(project=self.project_id, credentials=credentials)
        self.rate_limiter = RateLimiter()
    
    def _to_est_string(self, dt) -> str:
        """Convert datetime to EST timezone string."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        est_dt = dt.astimezone(EST_TZ)
        return est_dt.strftime("%Y-%m-%d %I:%M:%S %p EST")
    
    def _get_current_est_time(self) -> datetime:
        """Get current time in EST."""
        return datetime.now(EST_TZ)
    
    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Execute function with exponential backoff on rate limit errors."""
        for attempt in range(MAX_RETRIES):
            try:
                await self.rate_limiter.wait_if_needed()
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except exceptions.ResourceExhausted as e:
                if attempt == MAX_RETRIES - 1:
                    raise
                self.rate_limiter.set_backoff(attempt)
                print(f"[RETRY] Rate limit hit, attempt {attempt + 1}/{MAX_RETRIES}")
            except Exception as e:
                if "429" in str(e) or "quota" in str(e).lower():
                    if attempt == MAX_RETRIES - 1:
                        raise
                    self.rate_limiter.set_backoff(attempt)
                    print(f"[RETRY] Quota error, attempt {attempt + 1}/{MAX_RETRIES}")
                else:
                    raise
        
    async def discover_cloud_run_services(
        self,
        region: Optional[str] = None,
        label_filter: Optional[str] = None
    ) -> str:
        """Discover all Cloud Run services using Cloud Asset API."""
        try:
            scope = f"projects/{self.project_id}"
            asset_types = ["run.googleapis.com/Service"]
            
            print(f"[DEBUG] Searching in project: {self.project_id}, region: {region}")
            
            query_parts = []
            if region:
                query_parts.append(f"location:{region}")
            if label_filter:
                query_parts.append(f"labels.{label_filter}")
            
            query = " AND ".join(query_parts) if query_parts else None
            
            request = asset_v1.SearchAllResourcesRequest(
                scope=scope,
                asset_types=asset_types,
                query=query,
                page_size=500
            )
            
            services = []
            results = await self._retry_with_backoff(
                self.asset_client.search_all_resources, 
                request=request
            )
            
            for resource in results:
                parts = resource.name.split("/")
                service_info = {
                    "name": parts[-1] if len(parts) > 0 else "unknown",
                    "location": parts[-3] if len(parts) >= 4 else "unknown",
                    "full_name": resource.name,
                    "display_name": resource.display_name,
                    "labels": dict(resource.labels) if resource.labels else {},
                    "state": resource.state if hasattr(resource, 'state') else "UNKNOWN"
                }
                services.append(service_info)
            
            current_time = self._get_current_est_time()
            
            return json.dumps({
                "total_services": len(services),
                "services": services,
                "project": self.project_id,
                "query_time_est": self._to_est_string(current_time)
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": str(e), 
                "tool": "discover_cloud_run_services",
                "project_id": self.project_id
            })

    async def get_service_configuration(
        self,
        service_name: str,
        region: str
    ) -> str:
        """Get detailed configuration for a specific Cloud Run service."""
        try:
            full_name = f"projects/{self.project_id}/locations/{region}/services/{service_name}"
            
            print(f"[DEBUG] Getting config for: {full_name}")
            
            request = run_v2.GetServiceRequest(name=full_name)
            service = await self._retry_with_backoff(
                self.run_client.get_service,
                request=request
            )
            
            template = service.template
            
            created_est = self._to_est_string(service.create_time) if service.create_time else None
            updated_est = self._to_est_string(service.update_time) if service.update_time else None
            
            config = {
                "service_name": service_name,
                "region": region,
                "project": self.project_id,
                "url": service.uri,
                "ingress": str(service.ingress),
                "latest_revision": service.latest_ready_revision,
                "scaling": {
                    "min_instances": template.scaling.min_instance_count if template.scaling else 0,
                    "max_instances": template.scaling.max_instance_count if template.scaling else 100,
                },
                "containers": [],
                "created_est": created_est,
                "updated_est": updated_est,
            }
            
            if template.containers:
                for container in template.containers:
                    container_info = {
                        "image": container.image,
                        "resources": {
                            "cpu_limit": container.resources.limits.get("cpu", "1000m") if container.resources else "1000m",
                            "memory_limit": container.resources.limits.get("memory", "512Mi") if container.resources else "512Mi",
                        },
                        "env_vars": {env.name: env.value for env in container.env} if container.env else {}
                    }
                    config["containers"].append(container_info)
            
            return json.dumps(config, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": str(e), 
                "tool": "get_service_configuration",
                "project_id": self.project_id
            })

    async def get_service_configuration_cached(
        self,
        service_name: str,
        region: str
    ) -> str:
        """Get service configuration with caching for performance."""
        # Check cache first
        cached = get_cached_config(service_name, region)
        if cached:
            print(f"[CACHE HIT] Using cached config for {service_name} in {region}")
            return cached
        
        # Cache miss - fetch from API
        print(f"[CACHE MISS] Fetching config for {service_name} in {region}")
        config = await self.get_service_configuration(service_name, region)
        
        # Cache the result
        set_cached_config(service_name, region, config)
        
        return config

    async def get_service_multi_region(
        self,
        service_name: str,
        regions: list = None
    ) -> str:
        """Get service configuration across multiple regions in parallel."""
        if regions is None:
            regions = COMMON_REGIONS
        
        print(f"[PARALLEL] Fetching {service_name} from {len(regions)} regions simultaneously")
        
        # Create tasks for parallel execution
        tasks = []
        for region in regions:
            task = self.get_service_configuration_cached(service_name, region)
            tasks.append(task)
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine results
        configs = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"[ERROR] Failed to fetch from {regions[i]}: {result}")
                continue
            configs.append(result)
        
        # Return combined JSON
        if not configs:
            return json.dumps({"error": "No configurations retrieved"})
        
        # Parse and combine
        combined = []
        for config_str in configs:
            try:
                config_data = json.loads(config_str)
                combined.append(config_data)
            except:
                continue
        
        return json.dumps({
            "service_name": service_name,
            "regions": len(combined),
            "configurations": combined
        }, indent=2)

    async def _fetch_logs_chunk(
        self,
        filter_str: str,
        start_time: datetime,
        end_time: datetime,
        max_entries: int = 50000
    ) -> Dict:
        """Fetch a single chunk of logs with pagination."""
        service_counts = {}
        total_entries = 0
        
        # Add time window to filter
        start_str = start_time.astimezone(ZoneInfo("UTC")).strftime('%Y-%m-%dT%H:%M:%SZ')
        end_str = end_time.astimezone(ZoneInfo("UTC")).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        time_filter = f'timestamp>="{start_str}" AND timestamp<"{end_str}"'
        full_filter = f"{filter_str}\n{time_filter}"
        
        print(f"[DEBUG] Fetching logs from {self._to_est_string(start_time)} to {self._to_est_string(end_time)}")
        
        try:
            await self.rate_limiter.wait_if_needed()
            
            # list_entries returns an iterator directly
            entries_iterator = self.logging_client.list_entries(
                filter_=full_filter,
                order_by=logging_v2.DESCENDING,
                page_size=LOGS_PAGE_SIZE,
            )
            
            # Iterate through entries
            for entry in entries_iterator:
                total_entries += 1
                
                service_name = 'unknown'
                location = 'unknown'
                
                if hasattr(entry, 'resource') and entry.resource:
                    if hasattr(entry.resource, 'labels'):
                        service_name = entry.resource.labels.get('service_name', 'unknown')
                        location = entry.resource.labels.get('location', 'unknown')
                
                status_code = None
                if hasattr(entry, 'http_request') and entry.http_request:
                    if isinstance(entry.http_request, dict):
                        status_code = entry.http_request.get('status')
                    elif hasattr(entry.http_request, 'status'):
                        status_code = entry.http_request.status
                
                key = f"{service_name}|{location}"
                
                if key not in service_counts:
                    service_counts[key] = {
                        "service": service_name,
                        "region": location,
                        "total_requests": 0,
                        "status_2xx": 0,
                        "status_4xx": 0,
                        "status_5xx": 0,
                    }
                
                service_counts[key]["total_requests"] += 1
                
                if status_code:
                    try:
                        status_int = int(status_code)
                        if 200 <= status_int < 300:
                            service_counts[key]["status_2xx"] += 1
                        elif 400 <= status_int < 500:
                            service_counts[key]["status_4xx"] += 1
                        elif 500 <= status_int < 600:
                            service_counts[key]["status_5xx"] += 1
                    except (ValueError, TypeError):
                        pass
                
                # Stop if we've reached max entries for this chunk
                if total_entries >= max_entries:
                    print(f"[DEBUG] Reached max entries limit ({max_entries}) for this chunk")
                    break
                    
        except exceptions.ResourceExhausted as e:
            print(f"[WARN] Rate limit hit while fetching logs: {e}")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[ERROR] Error fetching logs: {e}")
            import traceback
            traceback.print_exc()
        
        return {
            "service_counts": service_counts,
            "total_entries": total_entries
        }

    async def get_exact_request_counts_from_logs(
        self,
        region: Optional[str] = None,
        hours: int = 1,
        limit: int = 100
    ) -> str:
        """Get EXACT request counts from Cloud Logging with chunking for large time windows."""
        try:
            print(f"[DEBUG] Querying Cloud Logging for exact request counts")
            
            now_est = self._get_current_est_time()
            start_time_est = now_est - timedelta(hours=hours)
            
            filter_parts = [
                'resource.type="cloud_run_revision"',
                'httpRequest.status>=200',
            ]
            
            if region:
                filter_parts.append(f'resource.labels.location="{region}"')
            
            filter_str = "\n".join(filter_parts)
            
            # For queries > 24 hours, use chunking
            if hours > 24:
                print(f"[SCALE] Large time window ({hours}h), using chunked retrieval")
                return await self._get_request_counts_chunked(
                    filter_str, start_time_est, now_est, region, limit
                )
            
            # Single chunk for smaller time windows
            result = await self._fetch_logs_chunk(
                filter_str, start_time_est, now_est, max_entries=100000
            )
            
            service_counts = result["service_counts"]
            total_entries = result["total_entries"]
            
            sorted_services = sorted(
                service_counts.values(),
                key=lambda x: x['total_requests'],
                reverse=True
            )[:limit]
            
            return json.dumps({
                "data_source": "Cloud Logging (100% accurate)",
                "time_window_hours": hours,
                "time_range_start_est": self._to_est_string(start_time_est),
                "time_range_end_est": self._to_est_string(now_est),
                "query_time_est": self._to_est_string(now_est),
                "total_log_entries_analyzed": total_entries,
                "total_services_with_requests": len(service_counts),
                "showing_top": min(limit, len(service_counts)),
                "project": self.project_id,
                "region_filter": region or "all regions",
                "note": f"Retrieved {total_entries} log entries",
                "services": sorted_services
            }, indent=2)
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"[ERROR] {error_details}")
            return json.dumps({
                "error": str(e),
                "error_details": error_details,
                "tool": "get_exact_request_counts_from_logs",
                "project_id": self.project_id
            })

    async def _get_request_counts_chunked(
        self,
        filter_str: str,
        start_time: datetime,
        end_time: datetime,
        region: Optional[str],
        limit: int
    ) -> str:
        """Fetch request counts in chunks for large time windows (up to 7 days)."""
        total_hours = int((end_time - start_time).total_seconds() / 3600)
        num_chunks = (total_hours + CHUNK_HOURS - 1) // CHUNK_HOURS
        
        print(f"[SCALE] Splitting {total_hours}h into {num_chunks} chunks of {CHUNK_HOURS}h each")
        
        combined_counts = {}
        total_entries = 0
        chunks_processed = 0
        
        current_start = start_time
        
        for i in range(num_chunks):
            current_end = min(current_start + timedelta(hours=CHUNK_HOURS), end_time)
            
            print(f"[CHUNK {i+1}/{num_chunks}] Processing {self._to_est_string(current_start)} to {self._to_est_string(current_end)}")
            
            chunk_result = await self._fetch_logs_chunk(
                filter_str, current_start, current_end, max_entries=50000
            )
            
            # Merge results
            for key, counts in chunk_result["service_counts"].items():
                if key not in combined_counts:
                    combined_counts[key] = counts.copy()
                else:
                    combined_counts[key]["total_requests"] += counts["total_requests"]
                    combined_counts[key]["status_2xx"] += counts["status_2xx"]
                    combined_counts[key]["status_4xx"] += counts["status_4xx"]
                    combined_counts[key]["status_5xx"] += counts["status_5xx"]
            
            total_entries += chunk_result["total_entries"]
            chunks_processed += 1
            
            current_start = current_end
            
            if current_start >= end_time:
                break
        
        sorted_services = sorted(
            combined_counts.values(),
            key=lambda x: x['total_requests'],
            reverse=True
        )[:limit]
        
        return json.dumps({
            "data_source": "Cloud Logging (100% accurate, chunked)",
            "time_window_hours": total_hours,
            "chunks_processed": chunks_processed,
            "time_range_start_est": self._to_est_string(start_time),
            "time_range_end_est": self._to_est_string(end_time),
            "query_time_est": self._to_est_string(self._get_current_est_time()),
            "total_log_entries_analyzed": total_entries,
            "total_services_with_requests": len(combined_counts),
            "showing_top": min(limit, len(combined_counts)),
            "project": self.project_id,
            "region_filter": region or "all regions",
            "note": f"Retrieved {total_entries} log entries across {chunks_processed} time chunks",
            "services": sorted_services
        }, indent=2)

    async def query_all_services_metrics_summary(
        self,
        metric_type: str,
        region: Optional[str] = None,
        hours: int = 1,
        limit: int = 100
    ) -> str:
        """Query metrics from Cloud Monitoring (fast but approximate)."""
        try:
            metric_map = {
                "request_count": "run.googleapis.com/request_count",
                "instance_count": "run.googleapis.com/container/instance_count",
            }
            
            if metric_type not in metric_map:
                return json.dumps({
                    "error": f"Metric type '{metric_type}' not supported. Use 'request_count' or 'instance_count'.",
                    "supported_metrics": list(metric_map.keys())
                })
            
            full_metric_type = metric_map[metric_type]
            project_name = f"projects/{self.project_id}"
            
            print(f"[DEBUG] Querying {metric_type} from Cloud Monitoring")
            
            now_est = self._get_current_est_time()
            start_time_est = now_est - timedelta(hours=hours)
            
            now_utc = now_est.astimezone(ZoneInfo("UTC"))
            start_time_utc = start_time_est.astimezone(ZoneInfo("UTC"))
            
            filter_parts = [f'resource.type = "cloud_run_revision"']
            filter_parts.append(f'metric.type = "{full_metric_type}"')
            
            if region:
                filter_parts.append(f'resource.labels.location = "{region}"')
            
            filter_str = " AND ".join(filter_parts)
            
            interval = monitoring_v3.TimeInterval({
                "end_time": now_utc.replace(tzinfo=None),
                "start_time": start_time_utc.replace(tzinfo=None)
            })
            
            if metric_type == "request_count":
                aggregation = monitoring_v3.Aggregation({
                    "alignment_period": {"seconds": 60},
                    "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_RATE,
                    "cross_series_reducer": monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
                    "group_by_fields": ["resource.service_name", "resource.location"]
                })
            else:
                aggregation = monitoring_v3.Aggregation({
                    "alignment_period": {"seconds": 60},
                    "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_MEAN,
                    "cross_series_reducer": monitoring_v3.Aggregation.Reducer.REDUCE_SUM,
                    "group_by_fields": ["resource.service_name", "resource.location"]
                })
            
            request = monitoring_v3.ListTimeSeriesRequest({
                "name": project_name,
                "filter": filter_str,
                "interval": interval,
                "aggregation": aggregation,
            })
            
            results = await self._retry_with_backoff(
                self.monitoring_client.list_time_series,
                request=request
            )
            
            service_metrics = {}
            
            for series in results:
                service_name = series.resource.labels.get("service_name", "unknown")
                location = series.resource.labels.get("location", "unknown")
                key = f"{service_name}|{location}"
                
                values = []
                for point in series.points:
                    val = point.value.double_value or point.value.int64_value or 0
                    values.append(val)
                
                if metric_type == "request_count":
                    total_requests = sum(values) * 60
                    display_value = int(total_requests)
                    max_rate = round(max(values), 2) if values else 0
                    avg_rate = round(sum(values) / len(values), 2) if values else 0
                    
                    service_metrics[key] = {
                        "service": service_name,
                        "region": location,
                        "total_requests": display_value,
                        "avg_requests_per_sec": avg_rate,
                        "max_requests_per_sec": max_rate,
                    }
                else:
                    avg_instances = sum(values) / len(values) if values else 0
                    max_instances = max(values) if values else 0
                    
                    service_metrics[key] = {
                        "service": service_name,
                        "region": location,
                        "avg_instances": round(avg_instances, 2),
                        "max_instances": round(max_instances, 2),
                    }
            
            if metric_type == "request_count":
                sorted_services = sorted(
                    service_metrics.values(),
                    key=lambda x: x['total_requests'],
                    reverse=True
                )[:limit]
            else:
                sorted_services = sorted(
                    service_metrics.values(),
                    key=lambda x: x['avg_instances'],
                    reverse=True
                )[:limit]
            
            return json.dumps({
                "data_source": "Cloud Monitoring (fast, sampled data)",
                "metric_type": metric_type,
                "time_window_hours": hours,
                "time_range_start_est": self._to_est_string(start_time_est),
                "time_range_end_est": self._to_est_string(now_est),
                "query_time_est": self._to_est_string(now_est),
                "total_services_with_data": len(service_metrics),
                "showing_top": min(limit, len(service_metrics)),
                "project": self.project_id,
                "region_filter": region or "all regions",
                "note": "For exact request counts, use get_exact_request_counts tool",
                "services": sorted_services
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "tool": "query_all_services_metrics_summary",
                "project_id": self.project_id
            })

    async def get_resource_utilization(
        self,
        service_name: str,
        region: str,
        hours: int = 1,
    ) -> str:
        """Get actual CPU and memory utilization for a specific service."""
        try:
            project_name = f"projects/{self.project_id}"

            print(f"[DEBUG] Querying resource utilization for {service_name} in {region}")

            now_est = self._get_current_est_time()
            start_time_est = now_est - timedelta(hours=hours)

            now_utc = now_est.astimezone(ZoneInfo("UTC"))
            start_time_utc = start_time_est.astimezone(ZoneInfo("UTC"))

            interval = monitoring_v3.TimeInterval(
                end_time=now_utc.replace(tzinfo=None),
                start_time=start_time_utc.replace(tzinfo=None),
            )

            metrics_to_fetch = {
                "cpu_utilization": "run.googleapis.com/container/cpu/utilizations",
                "memory_utilization": "run.googleapis.com/container/memory/utilizations",
            }

            results = {}

            for metric_name, metric_type in metrics_to_fetch.items():
                filter_str = (
                    'resource.type = "cloud_run_revision" '
                    f'AND metric.type = "{metric_type}" '
                    f'AND resource.labels.service_name = "{service_name}" '
                    f'AND resource.labels.location = "{region}"'
                )

                # DISTRIBUTION metrics → use percentile aligner
                aggregation = monitoring_v3.Aggregation(
                    alignment_period={"seconds": 60},
                    per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_PERCENTILE_50,
                )

                request = monitoring_v3.ListTimeSeriesRequest(
                    name=project_name,
                    filter=filter_str,
                    interval=interval,
                    aggregation=aggregation,
                )

                try:
                    await self.rate_limiter.wait_if_needed()
                    time_series = self.monitoring_client.list_time_series(request=request)

                    values = []
                    for series in time_series:
                        for point in series.points:
                            val = point.value.double_value or 0
                            values.append(val * 100)  # convert 0–1 to %

                    if values:
                        results[metric_name] = {
                            "current": round(values[-1], 2),
                            "average": round(sum(values) / len(values), 2),
                            "max": round(max(values), 2),
                            "min": round(min(values), 2),
                            "datapoints": len(values),
                            "unit": "%",
                        }
                    else:
                        results[metric_name] = {
                            "current": 0,
                            "average": 0,
                            "max": 0,
                            "min": 0,
                            "datapoints": 0,
                            "unit": "%",
                            "note": "No data available for this time range",
                        }

                except Exception as e:
                    print(f"[ERROR] Failed to fetch {metric_name}: {e}")
                    results[metric_name] = {"error": str(e)}

            return json.dumps(
                {
                    "service_name": service_name,
                    "region": region,
                    "time_window_hours": hours,
                    "time_range_start_est": self._to_est_string(start_time_est),
                    "time_range_end_est": self._to_est_string(now_est),
                    "query_time_est": self._to_est_string(now_est),
                    "cpu_utilization": results.get("cpu_utilization"),
                    "memory_utilization": results.get("memory_utilization"),
                    "project": self.project_id,
                },
                indent=2,
            )

        except Exception as e:
            import traceback
            return json.dumps(
                {
                    "error": str(e),
                    "error_details": traceback.format_exc(),
                    "tool": "get_resource_utilization",
                    "project_id": self.project_id,
                }
            )

    async def get_all_utilization_metrics(
        self,
        service_name: str,
        region: str,
        hours: int = 1
    ) -> str:
        """Get comprehensive utilization metrics including CPU, memory, requests, and instances."""
        try:
            print(f"[DEBUG] Fetching comprehensive metrics for {service_name} in {region}")
            
            # Fetch all metrics in parallel
            resource_util_task = self.get_resource_utilization(service_name, region, hours)
            instance_count_task = self.query_all_services_metrics_summary("instance_count", region, hours, 100)
            
            resource_util, instance_data = await asyncio.gather(
                resource_util_task,
                instance_count_task,
                return_exceptions=True
            )
            
            # Parse results
            resource_data = json.loads(resource_util) if not isinstance(resource_util, Exception) else {"error": str(resource_util)}
            instance_json = json.loads(instance_data) if not isinstance(instance_data, Exception) else {"error": str(instance_data)}
            
            # Extract instance info for this specific service
            instance_info = {}
            if "services" in instance_json:
                for svc in instance_json["services"]:
                    if svc.get("service") == service_name and svc.get("region") == region:
                        instance_info = svc
                        break
            
            # Get configuration
            config_data = await self.get_service_configuration(service_name, region)
            config = json.loads(config_data) if config_data else {}
            
            return json.dumps({
                "service_name": service_name,
                "region": region,
                "time_window_hours": hours,
                "query_time_est": self._to_est_string(self._get_current_est_time()),
                
                "resource_utilization": {
                    "cpu": resource_data.get("cpu_utilization", {}),
                    "memory": resource_data.get("memory_utilization", {})
                },
                
                "instance_metrics": instance_info,
                
                "configuration": {
                    "cpu_limit": config.get("containers", [{}])[0].get("resources", {}).get("cpu_limit", "unknown"),
                    "memory_limit": config.get("containers", [{}])[0].get("resources", {}).get("memory_limit", "unknown"),
                    "min_instances": config.get("scaling", {}).get("min_instances", 0),
                    "max_instances": config.get("scaling", {}).get("max_instances", 100)
                },
                
                "project": self.project_id
            }, indent=2)
            
        except Exception as e:
            import traceback
            return json.dumps({
                "error": str(e),
                "traceback": traceback.format_exc(),
                "tool": "get_all_utilization_metrics"
            })


# Tool function wrappers
async def list_services(region: str = None, label_filter: str = None) -> str:
    """List all Cloud Run services in the project."""
    tools = CloudRunTools()
    return await tools.discover_cloud_run_services(region, label_filter)


async def get_service_details(service_name: str, region: str) -> str:
    """Get detailed configuration for a specific Cloud Run service."""
    tools = CloudRunTools()
    return await tools.get_service_configuration(service_name, region)


async def get_service_details_fast(service_name: str, region: str = None) -> str:
    """
    Get service configuration with caching (5min TTL).
    Faster for repeated queries of the same service.
    """
    if region is None:
        region = DEFAULT_REGION
    
    tools = CloudRunTools()
    return await tools.get_service_configuration_cached(service_name, region)


async def get_service_all_regions(service_name: str) -> str:
    """
    Get service configuration from all common regions in parallel.
    Much faster than sequential queries.
    """
    tools = CloudRunTools()
    return await tools.get_service_multi_region(service_name, COMMON_REGIONS)


async def get_metrics_summary(
    metric_type: str,
    region: str = None,
    hours: int = 1,
    limit: int = 100
) -> str:
    """Get metrics from Cloud Monitoring (fast, approximate)."""
    tools = CloudRunTools()
    return await tools.query_all_services_metrics_summary(metric_type, region, hours, limit)


async def get_exact_request_counts(
    region: str = None,
    hours: int = 1,
    limit: int = 100
) -> str:
    """
    Get EXACT request counts from Cloud Logging (100% accurate).
    Supports large time windows up to 7 days (168 hours) with automatic chunking.
    All timestamps shown in EST timezone.
    """
    tools = CloudRunTools()
    return await tools.get_exact_request_counts_from_logs(region, hours, limit)


async def get_resource_utilization(service_name: str, region: str, hours: int = 1) -> str:
    """
    Get actual CPU and memory utilization for a specific Cloud Run service.
    Returns current, average, max, and min utilization percentages.
    """
    tools = CloudRunTools()
    return await tools.get_resource_utilization(service_name, region, hours)


async def get_all_utilization_metrics(service_name: str, region: str, hours: int = 1) -> str:
    """
    Get comprehensive utilization metrics for a Cloud Run service including:
    - CPU utilization (current, avg, max, min)
    - Memory utilization (current, avg, max, min)
    - Instance count (avg, max)
    - Configuration limits (CPU, memory, scaling)
    
    This provides a complete view of service resource usage and capacity.
    """
    tools = CloudRunTools()
    return await tools.get_all_utilization_metrics(service_name, region, hours)