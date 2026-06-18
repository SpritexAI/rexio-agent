import os
import sys
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any

# Ensure codebase package is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rexio_agent.db.connection import (
    init_db,
    get_skills,
    get_messages,
    get_db_connection
)
from rexio_agent.core.loop import AgentSession

# Database initialization on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

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

@app.get("/api/skills")
def get_agent_skills():
    """Retrieves all custom dynamic skills learned by the agent."""
    try:
        skills = get_skills()
        return {"skills": skills}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount built web static files if they exist
web_dist_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "dist")
if os.path.exists(web_dist_path):
    app.mount("/", StaticFiles(directory=web_dist_path, html=True), name="static")

def start():
    # Load configuration
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("run_agent:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    start()
