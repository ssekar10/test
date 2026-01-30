# ---
# **IMPORTANT: DO NOT MODIFY THIS REPOSITORY**
#
# Do not create branches, modify content, or delete anything in this repository. This is a template and should not be edited directly.
# ---
> **Note:** This template is developed using `google-adk~=1.20.0`.
> If you want to use `google-adk~=1.10.0`, please refer to the `feature/adk-v1.10.0` branch.

### ADK Bootstrap Template Repository
This is the template repository for creating ADK-based conversational AI agents. Developers use this template to build, integrate, and test their custom agents with pre-configured CI/CD pipelines and evaluation tools.

## Prerequisites
 
Before you begin, ensure you have the following installed:
 
- **Python 3.12** (required)
- Git
- (Optional) Google Cloud SDK (`gcloud`) for authentication and deployment
 
You can check your Python version with:
```powershell
python --version
```
## Getting Started

In order to use this template, developers must:

**1. Create a new repository from this template**

* Select **Create a new repository**
* Enter a repository name following the convention: **adk-platform-usecase** (example: **adk-platform-customerservice**)
* Add a description of what your agent will do
* In Configuration select Start with a template -->/comcast-dxp-conversational-core/ADK-Bootstrap-Template-Repo
* Leave all other fields at default values
* Click **Create repository**

**2. Clone your new repository**

```powershell
git clone https://github.com/comcast-dxp-conversational-core/adk-platform-usecase.git
cd adk-platform-usecase
```

**3. Create a feature branch for your development**

```powershell
git checkout -b feature/initial-setup
```

You are now ready to build your agent.

## Developing Your Agent

This template provides a sample agent (`test_agent`) as a reference. When you create your own repository from this template, you'll build your own agent implementation.

Follow these steps:

1.  **Create Your Sub-Agent**: Build your agent logic in `bootstrap_agent/sub_agents/[your_agent_name]/` directory with your agent files and prompts.
2.  **Modify `agent.py`**: Change `bootstrap_agent/agent.py` to import and use your new sub-agent instead of `test_agent_simple`.
3.  **Add Custom Tools**: If needed, add your tools to `bootstrap_agent/api_tools/` directory and integrate them into your agent.
4.  **Add Utilities**: Place helper functions or modules in `bootstrap_agent/utils/` directory.
5.  **Add Dependencies**: Add any new Python packages to `bootstrap_agent/requirements.txt`.
6.  **Modify `pyproject.toml`**: Change the project `name` and `description` to match your agent.
7.  **Review Deployment Logic**: Check `bootstrap_agent/utils/deploy_utils.py` and `bootstrap_agent/deploy/__main__.py` for your agent's needs.
8.  **Add Environment Variables**: Add any new variables to `.env` files (e.g., `env/.env.dev`). Example:
    ```
    YOUR_AGENT_NAME="my-test-agent"
    ```

## Configuration Requirements

### Important Notes

**DO NOT modify the .github directory** - CI/CD pipelines are pre-configured

**You MUST update these files before deploying:**

### 1. Environment Variables (Required for all environments)

Update all `.env` files in the `env/` directory (`env/.env.dev`, `env/.env.preprod`, `env/.env.prod`):

**Core Variables:**
```bash
AGENT_NAME="your-agent-name"                    # Must be lowercase, alphanumeric, and underscore only
AGENT_DIRECTORY="bootstrap_agent"               # Keep as-is (only change if you rename the directory)
ENVIRONMENT="dev"                               # Set to: dev, preprod, or prod (per environment)
```

**Google Cloud Configuration:**
```bash
GCP_PROJECT_ID="your-gcp-project-id"
AGENT_RUNTIME_SA="your-service-account@your-project.iam.gserviceaccount.com"
STAGING_BUCKET="gs://your-staging-bucket-name"
DEPLOY_REGIONS="us-central1,us-east4"        # Multi-region deployment (simultaneous)
```

**CI/CD Authentication (GitHub Actions):**
```bash
GCP_SA_WIF_PROVIDER="projects/123456/locations/global/workloadIdentityPools/pool-name/providers/provider-name"
GCP_SA_WIF_SA="github-actions-sa@your-project.iam.gserviceaccount.com"
```

**Optional Variables:**
```bash
ALL_REGIONS="us-central1,us-east4"              # For multi-region deployment
GEMINI_MODEL="gemini-2.5-flash"                 # LLM model to use
```

**Application-Specific Variables:**

Add any custom variables your agent needs:
```bash
YOUR_API_KEY="your-value"
```

### 2. Project Metadata

Update `pyproject.toml` with your agent details:

```toml
[project]
name = "adk-your-agent-name"                    # Change to match your agent
version = "0.1.0"
description = "Description of your agent"        # Describe what your agent does
```

### 3. Python Dependencies

Update `bootstrap_agent/requirements.txt`:

* **Keep all existing ADK dependencies** 
* **Add your custom packages below** the existing dependencies

Example:
```txt
# Existing ADK dependencies (DO NOT REMOVE)
boto3~=1.40.35
google-adk~=1.10.0
...
# (Keep all existing packages)

# Your custom dependencies (ADD BELOW)
your-package==1.0.0
```

## Building Your Agent

This template includes example code (`test_agent`, `test_tool.py`) to show you the structure. You'll build your own implementation in your new repository.

### Step 1: Create Your Sub-Agent

**Location:** `bootstrap_agent/sub_agents/[your_agent_name]/`

Build your sub-agent in a new directory. The template includes a `test/` directory as an example - you can use it as reference and create your own.

Example structure:
```
bootstrap_agent/sub_agents/customer_service/
    ├── customer_service_agent.py      # Your agent definition
    ├── customer_service_prompts.py    # Agent instructions (optional)
    └── customer_service_utils.py      # Helper functions (optional)
```

**Example Agent Code:**
```python
# bootstrap_agent/sub_agents/customer_service/customer_service_agent.py

import os
from google.adk.agents import LlmAgent
from google.genai import types

agent_model = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

customer_service_agent = LlmAgent(
    name="customer_service_agent",
    model=agent_model,
    instruction="You are a helpful customer service agent...",
    description="Handles general customer inquiries and support requests",
    tools=[],  # Add your tools here
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,
        top_p=0.1,
        top_k=10,
    ),
)
```

### Step 2: Create Your API Tools

**Location:** `bootstrap_agent/api_tools/[tool_name].py`

Build your API integration tools. The template includes `test_tool.py` as an example structure.

**Example Tool Code:**
```python
# bootstrap_agent/api_tools/account_tools.py

from google.adk.tools import agent_tool
from google.adk.tools.tool_context import ToolContext

@agent_tool
def get_account_info(account_id: str, tool_context: ToolContext) -> dict:
    """
    Retrieves account information for a customer.
    
    Args:
        account_id: Customer account ID
        tool_context: ADK tool context
        
    Returns:
        Account information dictionary
    """
    # Your API call logic here
    return {"account_id": account_id, "status": "active"}
```

### Step 3: Register Your Agent

**Location:** `bootstrap_agent/agent.py`

You must make 3 changes in this file:

**Change 1:** Change the import to your sub-agent
```python
from .sub_agents.test.test_agent import test_agent_simple
# Change to your actual sub-agent import
# Example: from .sub_agents.customer_service.customer_service_agent import customer_service_agent
```

**Change 2:** Change the root agent name
```python
root_agent = Agent(
    name="adk_agent",  # Change to your agent name
    # ...
)
# Example: name="customer_support_orchestrator"
```

**Change 3:** Change the sub-agent in the list
```python
sub_agents=[
    test_agent_simple,  # Replace with your actual sub-agent
]
# Example: sub_agents=[customer_service_agent, search_agent]
```

### Step 4: Add Evaluation Test Cases

**Location:** `bootstrap_agent/eval/`

Create `.evalset.json` files to test your agent's behavior.

**Example Test Case:**
```json
{
  "cases": [
    {
      "id": "test-account-lookup",
      "app_name": "bootstrap_agent",
      "user_id": "test_user_001",
      "query": "What is my account status?",
      "expected": {
        "routes": {
          "items": ["customer_service_agent"]
        },
        "tools": {
          "items": ["get_account_info"]
        }
      }
    }
  ]
}
```



### Step 5: Test your agent locally before deploying

This section describes how to set up your local development environment.

1.  **Set the environment to dev:**
    ```powershell
    $env:ENVIRONMENT = "dev"
    ```

2.  **Authenticate to Google Cloud:**
    ```powershell
    gcloud auth application-default login
    ```

3.  **Run the following command to bring up the web UI:**
    ```powershell
    adk web
    ```

**Access your agent:**
* Dev UI: http://localhost:8080/dev-ui


### Step 6: Update This README

Replace this README.md with documentation specific to your agent, including:
* What your agent does
* Available features and capabilities
* API endpoints and usage examples
* Team contact information

## Deployment Workflow

### Committing Your Code

Once your agent is ready, commit and push your changes:

```powershell
git add .
git commit -m "Initial agent implementation"
git push origin feature/initial-setup
```

### Creating a Pull Request

1. Navigate to your repository on GitHub
2. Click **Pull requests** → **New pull request**
3. Configure the PR:
   * **Base branch**: `dev`
   * **Compare branch**: `feature/initial-setup` (your feature branch)
4. Review the changes to ensure everything looks correct
5. Click **Create pull request**
6. Request reviews from 2 team members
7. Wait for **2 approvals** before merging

**The deployment pipeline will automatically trigger when you merge into the `dev` branch and deploy simultaneously to both us-central1 and us-east4 regions.**

### Viewing Pipeline Results

To view pipeline runs and deployment status:

1. Go to the **Actions** tab in your repository
2. Click on the latest workflow run
3. View detailed logs and deployment results

**Note:** Your GitHub ID must be part of a team with **repository-write** role. Contact your team lead to be added to teams like: AIX-OPS, DF-Partner-Authors, dialogflow-release-managers, Google DevOps, or google-team.

### Environment Promotion

Promote your agent through environments using the same Pull Request process:

```
feature/your-branch → dev → preprod → prod
                      ↓       ↓         ↓
                    DEV   PREPROD    PROD
```

**Promotion Steps:**

1. **DEV Environment**
   * Merge feature branch → `dev`
   * Automatic deployment to dev environment (us-central1 and us-east4)

2. **PREPROD Environment**
   * Create PR: `dev` → `preprod`
   * Get 2 approvals
   * Merge triggers deployment to preprod (us-central1 and us-east4)

3. **PROD Environment**
   * Create PR: `preprod` → `prod`
   * Get 2 approvals
   * Merge triggers deployment to production (us-central1 and us-east4)

**Each merge triggers an automatic deployment to the corresponding environment across both regions simultaneously.**

## Quick Reference

### Code Changes Required

| File | Line/Section | What to Change |
|------|-------------|------------------|
| `bootstrap_agent/agent.py` | Line ~23 | Change `test_agent_simple` import to your sub-agent import |
| `bootstrap_agent/agent.py` | Line ~30 | Change `name="adk_agent"` to your agent name |
| `bootstrap_agent/agent.py` | Line ~38 | Change `test_agent_simple` to your sub-agent in `sub_agents=[]` list |
| `bootstrap_agent/api_tools/test_tool.py` | Entire file | Create your actual API tools |

### Files You Must Modify

| File | What to Change |
|------|----------------|
| `env/.env.dev` | Set all environment variables for dev |
| `env/.env.preprod` | Set all environment variables for preprod |
| `env/.env.prod` | Set all environment variables for prod |
| `pyproject.toml` | Update project name and description |
| `bootstrap_agent/agent.py` | Import and register your sub-agents |
| `bootstrap_agent/requirements.txt` | Add your Python dependencies |

### Files to Create

| Location | What to Create |
|----------|----------------|
| `bootstrap_agent/sub_agents/[name]/` | Your sub-agent implementation |
| `bootstrap_agent/api_tools/[name].py` | Your API integration tools |
| `bootstrap_agent/eval/[name].evalset.json` | Your test cases |
| `tests/unit/` | Unit tests for your code |

### Files NOT to Modify

* `.github/workflows/` - Pre-configured CI/CD pipelines

### Common Issues and Solutions

**Issue: Import errors when running locally**
* Solution: Ensure you've activated your virtual environment and installed dependencies: `pip install -r bootstrap_agent/requirements.txt`

**Issue: Agent name validation fails during deployment**
* Solution: AGENT_NAME must be lowercase, alphanumeric, and underscore only (e.g., "customer_service_agent")

**Issue: "Module not found" errors for your sub-agent**
* Solution: Make sure you've created `__init__.py` files in your sub-agent directory and properly imported your agent

**Issue: Callbacks not found errors**
* Solution: Remove any callback references in `agent.py` that you haven't implemented. The template includes commented examples.

## Testing Commands

```powershell
# Run unit tests
pytest tests/

# Run tests with coverage
pytest --cov=bootstrap_agent tests/

# Run evaluation tests
python -m bootstrap_agent.eval.eval --evalset bootstrap_agent/eval/your_test.evalset.json

# Start local development server
python main.py
```

## Additional Documentation

* [Google ADK Documentation](https://cloud.google.com/generative-ai/docs/agent-builder)
* [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
* [FastAPI Documentation](https://fastapi.tiangolo.com/)

---



## Pre-Deployment Checklist

Before deploying your agent, ensure you have completed all of these steps:

### Configuration
- [ ] Updated `AGENT_NAME` in all environment files (dev, preprod, prod)
- [ ] Updated `GCP_PROJECT_ID` in all environment files
- [ ] Updated `AGENT_RUNTIME_SA` (service account) in all environment files
- [ ] Updated `STAGING_BUCKET` in all environment files
- [ ] Updated `GCP_SA_WIF_PROVIDER` and `GCP_SA_WIF_SA` for GitHub Actions
- [ ] Updated `pyproject.toml` with your project name and description
- [ ] Set `ENVIRONMENT` correctly in each env file (dev, preprod, prod)

### Code Implementation
- [ ] Built your sub-agent in `bootstrap_agent/sub_agents/[your_agent_name]/`
- [ ] Built your API tools in `bootstrap_agent/api_tools/`
- [ ] Changed the import in `bootstrap_agent/agent.py` (line ~23) to your sub-agent
- [ ] Set your agent name in `bootstrap_agent/agent.py` (line ~30)
- [ ] Added your sub-agent to `sub_agents=[]` list (line ~38)
- [ ] Built your API tools (you can keep or remove `test_tool.py`)
- [ ] Added your dependencies to `bootstrap_agent/requirements.txt`
- [ ] Cleaned up example files when ready (`test/` directory, `test_tool.py`)
- [ ] Customized root agent instruction for your use case

### Testing
- [ ] Created evaluation test cases in `bootstrap_agent/eval/`
- [ ] Tested agent locally using `python main.py`
- [ ] Verified agent responds correctly at http://localhost:8080/dev-ui
- [ ] Ran unit tests with `pytest tests/`
- [ ] All tests pass successfully

### Documentation
- [ ] Replaced this README.md with documentation specific to your agent
- [ ] Documented your agent's capabilities and features
- [ ] Added team contact information
- [ ] Documented any custom API endpoints

### GitHub
- [ ] Created feature branch for your work
- [ ] Committed all changes
- [ ] Created Pull Request to `dev` branch
- [ ] Requested 2 reviewers
- [ ] All CI/CD checks pass

**Once all items are checked, you're ready to merge and deploy!**

