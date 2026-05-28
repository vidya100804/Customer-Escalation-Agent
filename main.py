"""
main.py — FastAPI REST API for the Customer Escalation Agent
Run: python main.py
Docs: http://localhost:8000/docs
"""

import os
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from agent import EscalationRequest, EscalationResponse, run_agent, format_for_slack

app = FastAPI(
    title="Customer Escalation Agent",
    description="AI-powered support escalation analysis. Paste a user email + issue, get instant root cause & action plan.",
    version="1.0.0",
)


@app.post("/investigate", response_model=EscalationResponse, summary="Investigate an escalation")
async def investigate(request: EscalationRequest, x_openai_key: Optional[str] = Header(None)):
    """
    Submit a customer escalation. The agent will:
    - Fetch user account, payment, logs, and ticket history (in parallel)
    - Analyze with GPT-4o
    - Return a structured summary with escalation decision
    """
    try:
        return await run_agent(request, custom_api_key=x_openai_key)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/investigate/slack", summary="Investigate and return Slack-formatted text")
async def investigate_slack(request: EscalationRequest, x_openai_key: Optional[str] = Header(None)):
    """Same as /investigate but returns Slack-formatted mrkdwn text."""
    try:
        result = await run_agent(request, custom_api_key=x_openai_key)
        return {"text": format_for_slack(request, result)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.get("/health", summary="Health check")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Serve the interactive dashboard at the root path
@app.get("/")
async def serve_dashboard():
    static_index = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(static_index):
        return FileResponse(static_index)
    return HTMLResponse(
        "<h2>Dashboard index.html not found!</h2><p>Please ensure static/index.html exists.</p>"
    )

# Mount the static directory for CSS/JS
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

