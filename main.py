import os
import uvicorn
from google.adk.cli.fast_api import get_fast_api_app
from master_agent import create_master_agent  # CHANGED: bootstrap_agent → master_agent

ALLOWED_ORIGINS = ["*"]
SERVE_WEB_INTERFACE = True

# Create FastAPI app using ADK helper - pass agent directly
app = get_fast_api_app(
    agent=create_master_agent(),  # CHANGED: get_agent() → create_master_agent()
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        log_level="info",
    )
