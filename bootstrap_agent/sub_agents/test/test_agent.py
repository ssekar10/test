# SAMPLE DUMMY SUB-AGENT FOR DEVELOPERS REFERENCE

from google.adk.agents import Agent
from google.adk.tools import agent_tool
import os

# Define a simple test agent
test_agent_simple = Agent(
    name="adk_test_agent",
    model=os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"),
    instruction="This is a test agent for simple tasks.",
    tools=[],
)


