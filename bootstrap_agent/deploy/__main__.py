import argparse
import os
import sys
from dotenv import load_dotenv

from bootstrap_agent.utils.deploy_utils import (
    deploy_agent,
    get_latest_global_engine_info,
    make_deploy_name,
)
from bootstrap_agent.utils.custom_logger import CustomLogger

custom_logger = CustomLogger(__name__)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        type=str,
        choices=["deploy"],
        default="deploy",
        help="The mode to run the script in.",
    )
    args = parser.parse_args()

    try:
        # Select .env file based on ENVIRONMENT variable, default to .env.dev
        environment = os.getenv("ENVIRONMENT", "dev").lower()
        env_file = os.path.join(os.getcwd(), "env", f".env.{environment}")
        if os.path.exists(env_file):
            custom_logger.info(f"Loading environment variables from {env_file}")
            load_dotenv(dotenv_path=env_file, override=True)
        else:
            # Rely solely on environment variables from the CI/CD pipeline
            custom_logger.info(f"No env file found for environment '{environment}'. Relying on environment variables from the pipeline.")

        project_id = os.getenv("GCP_PROJECT_ID")
        agent_name_prefix = os.getenv("AGENT_NAME")
        agent_directory = os.getenv("AGENT_DIRECTORY")
        service_account = os.getenv("AGENT_RUNTIME_SA")
        staging_bucket = os.getenv("STAGING_BUCKET")
        regions = os.getenv("DEPLOY_REGIONS", "us-central1").split(",")

        # Increment version for new deployment
        latest_engine = get_latest_global_engine_info(
            project_id, regions, agent_name_prefix
        )
        new_version = latest_engine.version + 1
        new_agent_name = make_deploy_name(agent_name_prefix, new_version)

        custom_logger.info(f"Latest version found: {latest_engine.version} in region {latest_engine.region}")
        custom_logger.info(f"New agent name for deployment: {new_agent_name}")

        # Validate that all required environment variables are set
        required_vars = {
            "GCP_PROJECT_ID": project_id,
            "AGENT_NAME": agent_name_prefix,
            "AGENT_DIRECTORY": agent_directory,
            "AGENT_RUNTIME_SA": service_account,
            "STAGING_BUCKET": staging_bucket,
        }
        for var_name, var_value in required_vars.items():
            if not var_value:
                raise ValueError(f"Required environment variable '{var_name}' is not set.")

        # Run deployments sequentially
        for region in regions:
            custom_logger.info(f"Starting deployment to region: {region}")
            try:
                # Deploy the new version
                deploy_agent(
                    project_id=project_id,
                    region=region,
                    agent_name=new_agent_name,
                    agent_directory=agent_directory,
                    service_account=service_account,
                    staging_bucket=staging_bucket,
                )
                custom_logger.info(f"[{region}] Deployment Completed!")
            except Exception as e:
                custom_logger.error(f"[{region}] Deployment error occurred: {e}")
                # Ensure the pipeline script can see the failure
                print(f"Deploy failed: {e}", file=sys.stderr)
                sys.exit(1)

    except Exception as e:
        custom_logger.error(f"Deployment script failed: {e}")
        # Ensure the pipeline script can see the failure
        print(f"Deploy failed: {e}", file=sys.stderr)
        sys.exit(1)

    custom_logger.info("All deployments completed successfully.")
    sys.exit(0)