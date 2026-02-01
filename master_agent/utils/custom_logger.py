import logging
import os
import inspect
from contextvars import ContextVar

# Session context variable for tracking session IDs
session_id_var: ContextVar[str] = ContextVar("session_id", default="unknown")


class CustomLogger:
    def __init__(self, name, level=logging.DEBUG):
        self.resource_id = os.environ.get(
            "GOOGLE_CLOUD_AGENT_ENGINE_ID", "xa-adk-agent"
        )
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False

        if not self.logger.handlers:
            # Console Handler
            console_handler = logging.StreamHandler()
            # More meaningful formatter for console
            console_formatter = logging.Formatter(
                "[%(asctime)s] - %(levelname)s - [%(source_file)s:%(source_lineno)d] - [%(func_id)s] - %(message)s [session:%(session_id)s]"
            )
            console_handler.setFormatter(console_formatter)
            self.logger.addHandler(console_handler)

        if os.environ.get("IS_ENABLE_LOCAL_LOGGING", "false").lower() == "true":
            self._set_file_handler()

            # GCP Handler
            # if os.environ.get("ENABLE_GCP_LOGGING", "false").lower() == "false":
            #     try:
            #         client = google_logging.Client()
            #         gcp_handler = client.get_default_handler()
            #         self.logger.addHandler(gcp_handler)
            #         self.info("Successfully attached Google Cloud Logging handler.")
            #     except Exception as e:
            #         # Use a basic print here to avoid a logging loop if the logger itself fails
            #         print(f"ERROR: Failed to initialize Google Cloud Logging: {e}")

    def _set_file_handler(self):
        file_handler = logging.FileHandler("log.log", mode="w")
        file_formatter = logging.Formatter(
            "[%(asctime)s] - %(levelname)s - [%(source_file)s:%(source_lineno)d] - [%(func_id)s] - %(message)s [session:%(session_id)s]"
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

    def debug(self, message, tracking_id=None, session_override=None):
        self.log("DEBUG", message, tracking_id, session_override=session_override)

    def log(self, level, message, tracking_id=None, session_override=None):
        """Core log method with optional explicit session_override for background tasks."""
        log_method = getattr(self.logger, level.lower())
        func_id = "unknown.function"
        filename = "unknown.py"
        lineno = 0
        try:
            stack = inspect.stack()
            # Find the first frame that is not part of the CustomLogger itself
            for frame_info in stack[1:]:
                cls = frame_info.frame.f_locals.get("self", None)
                if not (cls and isinstance(cls, CustomLogger)):
                    func_id = f"{frame_info.frame.f_globals.get('__name__', '?')}.{frame_info.function}"
                    filename = os.path.basename(frame_info.filename)
                    lineno = frame_info.lineno
                    break
        except Exception:
            pass  # Keep the default values on error

        effective_session_id = session_override or session_id_var.get()

        # Unified payload for all handlers
        log_payload = {
            "func_id": func_id,
            "source_file": filename,  # Renamed to avoid conflict
            "source_lineno": lineno,  # Renamed to avoid conflict
            "resource_id": self.resource_id,
            "tracking_id": tracking_id or "",
            "session_id": effective_session_id,
        }

        # The GCP handler uses 'json_fields', while the console handler uses the top-level keys.
        # We provide both for compatibility.
        log_method(message, extra={"json_fields": log_payload, **log_payload})

    def info(self, message, tracking_id=None, session_override=None):
        self.log("INFO", message, tracking_id, session_override=session_override)

    def warning(self, message, tracking_id=None, session_override=None):
        self.log("WARNING", message, tracking_id, session_override=session_override)

    def error(self, message, tracking_id=None, session_override=None):
        self.log("ERROR", message, tracking_id, session_override=session_override)

    def critical(self, message, tracking_id=None, session_override=None):
        self.log("CRITICAL", message, tracking_id, session_override=session_override)
