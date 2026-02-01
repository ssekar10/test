

import requests
import json
import os

from bootstrap_agent.utils.custom_logger import CustomLogger
from google.adk.tools.tool_context import ToolContext

DUMMY_BASE_URL = os.getenv("DUMMY_BASE_URL", "https://api.dummycorp.net/v1")

logger = CustomLogger(__name__)

def _handle_api_response(api_endpoint: str, response: requests.Response) -> dict:
    
    logger.info(f"API call: {api_endpoint} status: {response.status_code}")

    if response.status_code == 200:
        try:
            return {"status": "success", "data": response.json()}
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON response.")
            return {"status": "error", "message": "Invalid API response format (JSON decode error)"}
    
    elif response.status_code == 404:
        return {"status": "error", "message": "Resource not found (404)"}
    
    elif 400 <= response.status_code < 500:
        logger.warning(f"Client error ({response.status_code}): {response.text}")
        return {"status": "error", "message": f"Client error: {response.text}"}
    
    else:
        logger.error(f"Server error ({response.status_code}): {response.text}")
        return {"status": "error", "message": f"API server error: {response.status_code}"}

def fetch_service_status(service_name: str) -> dict:
    
    url = f"{DUMMY_BASE_URL}/services/{service_name}/status"
    
    headers = {
        'Accept': 'application/json'
    }

    try:
        response = requests.get(url, headers=headers, timeout=5)
        return _handle_api_response(url, response)
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        return {"status": "error", "message": f"Network request failed: {e}"}

if __name__ == "__main__":
    
    print("--- Simplified Dummy Tool Execution Test ---")
    
    print("\n[TEST] fetch_service_status for 'checkout':")
    print(fetch_service_status("checkout"))


