# OpenTelemetry imports
from opentelemetry import _events as events
from opentelemetry import _logs as logs
from opentelemetry import metrics, trace
from opentelemetry.exporter.cloud_logging import CloudLoggingExporter
from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.instrumentation.google_genai import GoogleGenAiSdkInstrumentor
from opentelemetry.instrumentation.vertexai import VertexAIInstrumentor
from opentelemetry.sdk._events import EventLoggerProvider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk._logs._internal.export import LogData

# Vertex AI ADK imports

import json
import os


# -------------------------------
# OpenTelemetry setup functions
# -------------------------------
class SafeJsonCloudLoggingExporter(CloudLoggingExporter):
    """
    Custom Cloud Logging Exporter that ensures log data is JSON-serializable
    and structured before exporting to Google Cloud Logging.
    """

    def export(self, batch: list[LogData]):
        """
        Sanitize all log entries in the batch before exporting.
        """
        for log_data in batch:
            log_record = log_data.log_record
            log_record.body = self._sanitize_and_structure(log_record.body)
        return super().export(batch)

    def _sanitize_and_structure(self, body):
        """
        Convert log body into a JSON-safe and structured format.

        Args:
            body: The log body to sanitize, which can be any type.

        Returns:
            A JSON-safe representation of the log body.
        """
        # --- Handle primitive types and None ---
        if isinstance(body, (str, int, float, bool)) or body is None:
            return body

        # --- Handle structured dictionaries ---
        if isinstance(body, dict):
            structured_payload = {}

            content = body.get("content")
            if isinstance(content, dict):
                structured_payload["role"] = content.get("role")
                parts = content.get("parts", [])
                if isinstance(parts, list):
                    for part in parts:
                        if isinstance(part, dict):
                            # Extract only existing keys
                            for key in ["function_call", "function_response", "text"]:
                                if key in part:
                                    structured_payload[key] = part[key]

            # Return structured payload if found
            if structured_payload:
                return json.dumps(structured_payload)

            # Fallback: ensure dict is JSON-serializable
            try:
                json.dumps(body)
                return body
            except Exception:
                return str(body)

        # --- Handle lists ---
        if isinstance(body, list):
            try:
                json.dumps(body)
                return body
            except Exception:
                return str(body)

        # --- Fallback for any other types ---
        return str(body)


def setup_opentelemetry(project_id: str) -> None:
    """
    Sets up OpenTelemetry SDK with Google Cloud exporters for tracing, metrics,
    and logging, including Vertex AI and Google Gen AI instrumentation.

    Args:
        project_id: Google Cloud project ID for exporting telemetry.
    """
    # --- Define resource attributes ---
    service_name = os.getenv("OTEL_SERVICE_NAME", "XA-Multi-Agent")
    resource = Resource.create(
        attributes={
            SERVICE_NAME: service_name,
            "gcp.project_id": project_id,
        }
    )

    # --- Tracing Setup ---
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(
            CloudTraceSpanExporter(project_id=project_id, resource_regex=".*")
        )
    )
    trace.set_tracer_provider(tracer_provider)

    # --- Logging Setup ---
    logger_provider = LoggerProvider(resource=resource)
    logger_provider.add_log_record_processor(
        BatchLogRecordProcessor(SafeJsonCloudLoggingExporter())
    )
    logs.set_logger_provider(logger_provider)

    # --- Event Logging Setup ---
    event_logger_provider = EventLoggerProvider(logger_provider)
    events.set_event_logger_provider(event_logger_provider)

    # # --- Metrics Setup ---
    # reader = PeriodicExportingMetricReader(CloudMonitoringMetricsExporter())
    # meter_provider = MeterProvider(metric_readers=[reader], resource=resource)
    # metrics.set_meter_provider(meter_provider)

    # --- Instrumentation for ADK (Vertex AI & Google Gen AI) ---
    # VertexAIInstrumentor().instrument()
    GoogleGenAiSdkInstrumentor().instrument()


def custom_instrumentor(project_id: str):
    setup_opentelemetry(project_id)
    return None