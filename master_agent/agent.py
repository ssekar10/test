"""Root Orchestrator Agent - Coordinates and delegates to sub-agents."""

import os
from google.adk.agents import LlmAgent
from sub_agents.cloud_run_expert.agent import create_cloud_run_agent


ROOT_SYSTEM_INSTRUCTION = """You are the Platform Coordinator, a root orchestration agent for Google Cloud infrastructure operations.

Your role is to:
1. Understand user intent regarding cloud infrastructure queries
2. Delegate compute-related queries to the appropriate specialist
3. Provide a unified experience across multiple cloud services

DELEGATION RULES:
- Cloud Run queries (services, containers, revisions, scaling, metrics) → Delegate to cloud_run_specialist
- Operational issues (latency, errors, performance) → Delegate to cloud_run_specialist
- Configuration questions (how is X set up?) → Delegate to cloud_run_specialist
- Request counts, traffic analysis → Delegate to cloud_run_specialist

The cloud_run_specialist is an expert SRE agent with:
- 100% accurate request counting from Cloud Logging
- Fast metrics from Cloud Monitoring
- Configuration analysis
- Troubleshooting workflows

You are a coordinator, not an executor. Always delegate to sub-agents when their expertise matches the query."""


def create_master_agent() -> LlmAgent:
    """Factory function to create the root orchestrator agent."""
    
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
    cloud_run_agent = create_cloud_run_agent()
    
    master_agent = LlmAgent(
        model=model,
        name="platform_coordinator",
        instruction=ROOT_SYSTEM_INSTRUCTION,
        sub_agents=[cloud_run_agent],
    )
    
    return master_agent


# ADK Web expects a variable named 'root_agent' at module level
root_agent = create_master_agent()
