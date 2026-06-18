import os
import sys
import uvicorn
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any

# Ensure codebase package is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rexio_agent.core.config import load_environment
load_environment()

from rexio_agent.db.connection import (
    init_db,
    get_skills,
    get_pending_skills,
    approve_skill,
    reject_skill,
    get_markdown_skills,
    save_markdown_skill,
    delete_markdown_skill,
    get_messages,
    get_db_connection
)
from rexio_agent.core.loop import AgentSession

# Database and Gateway initialization on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    
    # Start Telegram gateway in the background if token is configured
    telegram_task = None
    if os.getenv("TELEGRAM_BOT_TOKEN"):
        from rexio_agent.gateway.telegram import run_telegram_bot
        telegram_task = asyncio.create_task(run_telegram_bot())
        
    yield
    
    # Clean up tasks on shutdown
    if telegram_task:
        telegram_task.cancel()
        try:
            await telegram_task
        except asyncio.CancelledError:
            pass

app = FastAPI(title="RexiO Agent API", lifespan=lifespan)

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    conversation_id: str = "default_web_session"
    platform: str = "web"
    channel_id: str = "dashboard"

# Keep track of active sessions
sessions: Dict[str, AgentSession] = {}

@app.get("/api/status")
def get_status():
    """Returns the current status of the agent backend."""
    return {"status": "online", "model": os.getenv("MODEL_NAME", "gemini-2.5-flash")}

@app.get("/api/conversations")
def get_conversations():
    """Retrieves all interactive sessions stored in database."""
    try:
        with get_db_connection() as conn:
            rows = conn.execute("SELECT id, created_at, platform, channel_id, summary FROM conversations ORDER BY created_at DESC").fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/conversations/{conv_id}/messages")
def get_conversation_messages(conv_id: str):
    """Retrieves message history for a given session."""
    try:
        messages = get_messages(conv_id)
        return {"conversation_id": conv_id, "messages": messages}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
def post_chat_message(req: ChatRequest):
    """Sends a message to the agent and executes the decision/action loop."""
    conv_id = req.conversation_id
    
    # Initialize or fetch existing agent session
    if conv_id not in sessions:
        try:
            sessions[conv_id] = AgentSession(
                platform=req.platform,
                channel_id=req.channel_id,
                conversation_id=conv_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize session: {str(e)}")
            
    session = sessions[conv_id]
    
    try:
        response = session.run(req.message)
        # Fetch updated message history to return
        messages = get_messages(conv_id)
        return {
            "conversation_id": conv_id,
            "response": response,
            "messages": messages,
            "execution_log": session.execution_log
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/stream")
def post_chat_stream(req: ChatRequest):
    """Sends a message and streams the agent's response as Server-Sent Events."""
    conv_id = req.conversation_id

    if conv_id not in sessions:
        try:
            sessions[conv_id] = AgentSession(
                platform=req.platform,
                channel_id=req.channel_id,
                conversation_id=conv_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to initialize session: {str(e)}")

    session = sessions[conv_id]

    return StreamingResponse(
        session.run_stream(req.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )

class MarkdownSkillRequest(BaseModel):
    name: str
    description: str
    content: str

# --- Compiled Skills ---

@app.get("/api/skills")
def get_agent_skills():
    try:
        return {"skills": get_skills()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/skills/pending")
def get_pending_agent_skills():
    try:
        return {"skills": get_pending_skills()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/skills/{name}/approve")
def approve_agent_skill(name: str):
    try:
        approve_skill(name)
        for session in sessions.values():
            session.registry.load_custom_skills()
        return {"status": "approved", "name": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/skills/{name}/reject")
def reject_agent_skill(name: str):
    try:
        reject_skill(name)
        return {"status": "rejected", "name": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Markdown Skills ---

@app.get("/api/markdown-skills")
def get_md_skills():
    try:
        return {"skills": get_markdown_skills()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/markdown-skills")
def create_md_skill(req: MarkdownSkillRequest):
    try:
        save_markdown_skill(req.name, req.description, req.content)
        return {"status": "saved", "name": req.name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/markdown-skills/{name}")
def delete_md_skill(name: str):
    try:
        delete_markdown_skill(name)
        return {"status": "deleted", "name": name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount built web static files if they exist
web_dist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "dist")
if os.path.exists(web_dist_path):
    app.mount("/", StaticFiles(directory=web_dist_path, html=True), name="static")

def start():
    # Load configuration
    port = int(os.getenv("PORT", 51730))
    uvicorn.run("run_agent:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    start()
