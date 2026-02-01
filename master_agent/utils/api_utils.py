
#DUMMY TOOLS FOR DEVELOPERS REFERENCE

import datetime
import json
import os
from dotenv import load_dotenv
from bootstrap_agent.utils.custom_logger import CustomLogger

load_dotenv("ADK-BOOTSTRAP/bootstrap_agent/.env")


# Configure module-level logger
custom_logger = CustomLogger(__name__)

# Constants
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
REQUEST_TIMEOUT = 120  # seconds

project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

# Backend URLs from environment variables (add these to your .env file)
DUMMY_URL = os.getenv("DUMMY_API_URL")

def dummy_tool(input_text: str) -> str:
    """
    A simple placeholder tool that echoes the input.

    Args:
        input_text (str): Any text provided by the user or agent.

    Returns:
        str: A mock processed output.
    """
    return f"[DUMMY TOOL EXECUTED] Received: {input_text}"



