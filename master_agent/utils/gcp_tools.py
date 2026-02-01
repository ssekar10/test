# check this file if not required remove it

from google.cloud import secretmanager, storage
from bootstrap_agent.utils.custom_logger import CustomLogger

custom_logger = CustomLogger(__name__)

# Tool registry
TOOL_REGISTRY = []


def tool(func):
    TOOL_REGISTRY.append(func)
    return func


@tool
def get_secret_value(project_id: str, secret_name: str):
    """
    This is an internal to GCP tool to determine if I can read from a secrets registry
    """
    secret_manager_client = secretmanager.SecretManagerServiceClient()
    try:
        name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = secret_manager_client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as e:
        custom_logger.error(f"Error accessing secret '{secret_name}': {e}")
        return {
            "status": "error",
            "message": f"Error accessing {secret_name} in {project_id}. Error reported is {str(e)}",
        }


@tool
def get_file_from_bucket(bucket_name: str, file_name: str):
    """
    Fetch a JSON file from a Google Cloud Storage bucket.
    """
    # Initialize the client
    storage_client = storage.Client()

    # Get a reference to the bucket
    bucket = storage_client.bucket(bucket_name)

    # Get a reference to the file (json usually)
    json_file = bucket.blob(file_name)

    # Download the contents of the blob as a string
    # .download_as_bytes() returns a byte string, so we decode it.
    file_content = json_file.download_as_bytes().decode("utf-8")

    return file_content


@tool
def write_event_to_bucket(bucket_name: str, session_id: str, event: str):
    """
    Write an event to a Google Cloud Storage bucket. It will take a json string
    """
    import json

    try:
        event_dict = json.loads(event)
    except (TypeError, json.JSONDecodeError):
        event_dict = event

    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(f"events/{session_id}.json")

    # Here you would typically serialize your event data to JSON
    event_data = {"session_id": session_id, "event": event_dict}
    blob.upload_from_string(json.dumps(event_data), content_type="application/json")


if __name__ == "__main__":
    import os

    # Open the file in write mode
    with open("env_vars.txt", "w") as f:
        # Iterate through the os.environ dictionary
        for key, value in os.environ.items():
            # Write each key-value pair to the file
            f.write(f"{key}={value}\n")
