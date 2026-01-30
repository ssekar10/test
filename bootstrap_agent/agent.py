import json
import os
from typing import Optional
import logging
import vertexai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.tools import agent_tool, google_search
from google.genai import types
from dotenv import load_dotenv


# configure logging __name__
custom_logger = logging.getLogger(__name__)
custom_logger.info("Initializing root agent...")

load_dotenv()

agent_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
custom_logger.info(f"setting the agent model to {agent_model}")


from .sub_agents.test.test_agent import test_agent_simple



# The orchestrator will rely on its sub_agents.
root_agent = Agent(
    name="adk_agent",
    model=agent_model,
    instruction="""You are the orchestrator for a multi-agent system. Your primary responsibility is to understand the user's intent and delegate the task to the most appropriate sub-agent or tool. You must ensure a single, coherent resolution path and enforce privacy by never exposing sensitive information.
- For simple tests, delegate to the `test_agent_simple`.
""",
    description="The main orchestrator for all conversations. It determines the user’s intent and delegates to the appropriate sub-agent or tool.",
    sub_agents=[
        test_agent_simple,
    ],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        top_p=0.1,
        top_k=10,
        safety_settings=[
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            ),
        ],
    ),
)
