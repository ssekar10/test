from dataclasses import dataclass
from datetime import datetime
import os
import re
import shutil
import subprocess
import vertexai
from vertexai import agent_engines
import google.cloud.storage as storage
from google.api_core import exceptions
from google.cloud.aiplatform_v1beta1.services.reasoning_engine_service import (
    ReasoningEngineServiceClient,
)
import requests
from bootstrap_agent.utils.custom_logger import CustomLogger

custom_logger = CustomLogger(__name__)
from dotenv import dotenv_values, load_dotenv


def make_deploy_name(agent_prefix: str, version: int) -> str:
    return f"{agent_prefix}-V{version}"


@dataclass
class EngineInfo:
    region: str = ""
    version: int = 0  # Default to 0 if not provided
    display_name: str = ""
    full_name: str = (
        ""  # projects/{project}/locations/{loc}/reasoningEngines/{resource_id}
    )
    resource_id: str = ""


def get_latest_global_engine_info(
    project_id: str, regions: list[str], agent_prefix: str
) -> EngineInfo:
    """Returns the engine with the highest version number across all regions."""
    version_pat = re.compile(rf"^{re.escape(agent_prefix)}-V(\d+)$")
    best = EngineInfo()  # Initialize with default values instead of None

    for region in regions:
        try:
            client = ReasoningEngineServiceClient(
                client_options={"api_endpoint": f"{region}-aiplatform.googleapis.com"}
            )
            parent = f"projects/{project_id}/locations/{region}"

            for agent in client.list_reasoning_engines(parent=parent):
                dn = agent.display_name or ""
                m = version_pat.match(dn)
                if not m:
                    continue
                ver = int(m.group(1))
                full_name = str(agent.name)  # resource name from API
                rid = full_name.rsplit("/", 1)[-1]

                if ver >= best.version:  # Changed from > to >= to handle version 0 case
                    best = EngineInfo(region, ver, dn, full_name, rid)

        except Exception as e:
            custom_logger.error(f"[{region}] Error: {e}")

    return best


def get_auth_header():
    """Gets auth header from environment variable."""
    access_token = os.getenv("GCP_ACCESS_TOKEN")
    if not access_token:
        raise ValueError("GCP_ACCESS_TOKEN not found in environment.")
    return {"Authorization": f"Bearer {access_token}"}


def delete_older_versions(
    project_id: str,
    region: str,
    agent_prefix: str,
    versions_to_keep: int,
    current_version: int,
):
    """
    Deletes older versions of agents in a specific region, keeping only the specified
    number of most recent versions. Uses REST API with force delete.
    """
    agent_name = None
    try:
        from google.cloud import aiplatform_v1beta1

        client = aiplatform_v1beta1.ReasoningEngineServiceClient(
            client_options={"api_endpoint": f"{region}-aiplatform.googleapis.com"}
        )
        parent = f"projects/{project_id}/locations/{region}"

        agents_by_version = {}
        version_pattern = re.compile(rf"^{re.escape(agent_prefix)}-V(\d+)$")

        # List reasoning engines
        for agent in client.list_reasoning_engines(parent=parent):
            display_name = agent.display_name
            if display_name:
                match = version_pattern.match(display_name)
                if match:
                    version = int(match.group(1))
                    agents_by_version[version] = agent.name

        sorted_versions = sorted(agents_by_version.keys(), reverse=True)

        if len(sorted_versions) > versions_to_keep:
            versions_to_delete = sorted_versions[versions_to_keep:]
            base_url = f"https://{region}-aiplatform.googleapis.com/v1beta1"

            for version in versions_to_delete:
                agent_name = agents_by_version[version]
                print(
                    f"[{region}] Force deleting {agent_name} (and sessions/memories)..."
                )
                url = f"{base_url}/{agent_name}"
                headers = get_auth_header()

                resp = requests.delete(url, headers=headers, params={"force": "true"})
                if resp.status_code in (200, 204):
                    print(f"[{region}] Deleted agent {agent_name} (version {version})")
                else:
                    print(f"[{region}] Failed to delete {agent_name}: {resp.text}")

        else:
            print(
                f"[{region}] No old versions to delete. Keeping all {len(sorted_versions)} versions."
            )

    except Exception as e:
        print(f"[{region}] Error deleting old agents: {e}")


def update_env_file(file_path: str, key: str, value: str):
    """
    Updates or adds a key-value pair in a .env file.

    Args:
        file_path: The path to the .env file.
        key: The name of the environment variable.
        value: The new value for the variable.
    """
    try:
        # Check if the file exists, if not, create it
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                f.write(f"{key}={value}\n")
            print(f"Created new .env file and added {key}.")
            return

        # Read the content of the .env file
        with open(file_path, "r") as f:
            content = f.read()

        # Regex to find the key at the start of a line
        pattern = re.compile(f"^{re.escape(key)}=.*", re.MULTILINE)

        if re.search(pattern, content):
            # Key found: replace the old value with the new one
            new_content = re.sub(pattern, f"{key}={value}", content)
            print(f"Updated '{key}' in {file_path}.")
        else:
            # Key not found: append it to the end of the file
            new_content = content.strip() + f"\n{key}={value}\n"
            print(f"Added new key '{key}' to {file_path}.")

        # Write the updated content back to the file
        with open(file_path, "w") as f:
            f.write(new_content)

    except Exception as e:
        print(f"An error occurred while updating {file_path}: {e}")


def deploy_agent(
    project_id: str,
    region: str,
    agent_name: str,
    agent_directory: str,
    service_account: str,
    staging_bucket: str,
):
    """
    Deploys the agent to Vertex AI Agent Builder using the ADK CLI.
    """
    custom_logger.info(
        f"[{region}] Deploying agent '{agent_name}' to project '{project_id}' in region '{region}'..."
    )

    os.environ["GOOGLE_CLOUD_LOCATION"] = region
    os.environ["LOCATION"] = region
    os.environ["location"] = region

    # Get the absolute path to the .env file in the agent directory
    # This assumes the script is run from the project root
    agent_env_path = os.path.join(os.getcwd(), agent_directory, ".env")

    # Copy the environment-specific .env file to the agent directory 
    environment = os.getenv("ENVIRONMENT", "dev").lower()
    source_env_file = os.path.join(os.getcwd(), "env", f".env.{environment}")
    if os.path.exists(source_env_file):
        custom_logger.info(f"Syncing {source_env_file} to {agent_env_path}")
        shutil.copy2(source_env_file, agent_env_path)
    else:
        custom_logger.warning(f"Source env file {source_env_file} not found, using existing {agent_env_path}")

    staging_bucket_name = f"{staging_bucket}-{region}"

    create_bucket_if_not_exists(
        bucket_name=staging_bucket_name, project=project_id, location=region
    )
    custom_logger.info(
        f"[GOOGLE_CLOUD_LOCATION {os.getenv('GOOGLE_CLOUD_LOCATION')}] location {os.getenv('LOCATION')}  region '{region}'..."
    )

    # --- Check if custom OpenTelemetry tracing is enabled ---
    load_dotenv(agent_env_path, override=True)
    custom_otel_trace = os.getenv("ENABLE_CUSTOM_OTEL_TRACE")
    print(f"Custom OTEL tracing env var: {custom_otel_trace}")

    custom_adk_deploy = os.getenv("ENABLE_CUSTOM_ADK_DEPLOY")
    print(f"Custom ADK deploy env var: {custom_adk_deploy}")

    try:
        # Check if custom OpenTelemetry tracing is enabled
        # DISABLED: Custom OTEL tracing incompatible with ADK 1.20
        if False and custom_otel_trace and custom_otel_trace.lower() == "true":
            print("Custom OTEL tracing is enabled for deployment.")

            import textwrap
            import tempfile
            import google.adk.cli.cli_deploy as cli_deploy

            cli_deploy._AGENT_ENGINE_APP_TEMPLATE = textwrap.dedent(
                """
                from vertexai.preview.reasoning_engines import AdkApp
                import vertexai.preview.reasoning_engines.templates.adk as adk_template
                from {app_name}.utils.custom_otel import custom_instrumentor
                from {app_name}.agent import root_agent
                import vertexai
                import os

                # Initialize vertexai for GCP_PROJECT_ID and GOOGLE_CLOUD_LOCATION
                vertexai.init(
                    project=os.getenv("GCP_PROJECT_ID"),
                    location=os.getenv("GOOGLE_CLOUD_LOCATION"),
                )

                # Patch ADK's internal default instrumentor
                adk_template._default_instrumentor_builder = custom_instrumentor

                # Initialize AdkApp with tracing enabled
                adk_app = AdkApp(
                    agent=root_agent,
                    enable_tracing={trace_to_cloud_option},
                )
            """
            )

            cli_deploy.to_agent_engine(
                project=project_id,
                region=region,
                display_name=agent_name,
                staging_bucket=staging_bucket_name,
                trace_to_cloud=True,  # Ensure tracing data is sent to Cloud Trace
                agent_folder=agent_directory,
                adk_app="agent_engine_app",
                temp_folder=os.path.join(
                    tempfile.gettempdir(),
                    "agent_engine_deploy_src",
                    datetime.now().strftime("%Y%m%d_%H%M%S"),
                ),
            )

        # Check if custom adk deployment is enabled
        elif custom_adk_deploy and custom_adk_deploy.lower() == "true":
            print(
                "Custom ADK deployment is enabled, Custom OTEL tracing is NOT enabled."
            )

            import textwrap
            import tempfile
            import google.adk.cli.cli_deploy as cli_deploy

            cli_deploy._AGENT_ENGINE_APP_TEMPLATE = textwrap.dedent(
                """
                from vertexai.preview.reasoning_engines import AdkApp
                import vertexai.preview.reasoning_engines.templates.adk as adk_template
                from {app_name}.agent import root_agent
                import vertexai
                import os
               
                # Initialize vertexai for GCP_PROJECT_ID and GOOGLE_CLOUD_LOCATION
                vertexai.init(
                    project=os.getenv("GCP_PROJECT_ID"),
                    location=os.getenv("GOOGLE_CLOUD_LOCATION"),
                )

                # Initialize AdkApp with tracing enabled
                adk_app = AdkApp(
                    agent=root_agent,
                    enable_tracing={trace_to_cloud_option},
                )
            """
            )

            cli_deploy.to_agent_engine(
                project=project_id,
                region=region,
                display_name=agent_name,
                staging_bucket=staging_bucket_name,
                trace_to_cloud=True,
                agent_folder=agent_directory,
                adk_app="agent_engine_app",
                temp_folder=os.path.join(
                    tempfile.gettempdir(),
                    "agent_engine_deploy_src",
                    datetime.now().strftime("%Y%m%d_%H%M%S"),
                ),
            )

        else:
            # --- Standard ADK CLI deployment ---
            print(f"Custom OTEL tracing is NOT enabled for deployment.")
            subprocess.run(
                [
                    "adk",
                    "deploy",
                    "agent_engine",
                    f"--project={project_id}",
                    f"--region={region}",
                    f"--display_name={agent_name}",
                    # f"--service-account={service_account}",  # Currently unsupported in CLI
                    f"--staging_bucket={staging_bucket_name}",
                    f"--trace_to_cloud",  # Enable basic tracing
                    # f"--env_file=.env",  # Optional: using loaded env vars instead
                    agent_directory,
                ],
                check=True,
            )
        # --- Deployment success output ---
        print("Deployment finished successfully!")

    except Exception as e:
        # This will catch the subprocess.run deployment failure
        print(f"ADK deployment error occurred: {e}")
        # Re-raise the exception to be handled by the main function's try/except block
        raise


def create_bucket_if_not_exists(bucket_name: str, project: str, location: str) -> None:
    """Creates a new bucket if it doesn't already exist.

    Args:
        bucket_name: Name of the bucket to create
        project: Google Cloud project ID
        location: Location to create the bucket in (defaults to us-central1)
    """
    storage_client = storage.Client(project=project)

    if bucket_name.startswith("gs://"):
        bucket_name = bucket_name[5:]
    try:
        storage_client.get_bucket(bucket_name)
        custom_logger.info(f"Bucket {bucket_name} already exists")
    except exceptions.NotFound:
        bucket = storage_client.create_bucket(
            bucket_name,
            location=location,
            project=project,
        )
        custom_logger.info(f"Created bucket {bucket.name} in {bucket.location}")
