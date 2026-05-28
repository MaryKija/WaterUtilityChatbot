from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import sys
import json
from typing import Dict, Any, Optional

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.orchestrator import Orchestrator
from backend.context_engine import ContextManager
from backend.intent_pipeline import IntentPipeline
from backend.tool_executor import ToolExecutor
from backend.config import Config
from backend.logger import logger

# Initialize FastAPI app
app = FastAPI(title="Agentic WhatsApp Bot API")

# Configure CORS for Vercel deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
config = Config()

# Initialize core components
context_manager = ContextManager()
intent_pipeline = IntentPipeline()
tool_executor = ToolExecutor()
orchestrator = Orchestrator(config, context_manager, intent_pipeline, tool_executor)

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
    confidence: float
    intent: Optional[str] = None
    escalated: bool = False

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Handle chat messages for the WhatsApp bot
    """
    try:
        logger.info(f"Received chat request: {request.message[:100]}...")

        # Process the message through the orchestrator
        result = await orchestrator.process(
            message=request.message,
            user_id=request.user_id or request.session_id or "demo-user"
        )

        # Format response
        response = ChatResponse(
            response=result.get("response", "I apologize, but I couldn't process your request."),
            session_id=result.get("session_id", request.session_id or "unknown"),
            confidence=result.get("confidence", 0.0),
            intent=result.get("intent"),
            escalated=result.get("escalated", False)
        )

        logger.info(f"Chat response: {response.response[:100]}...")
        return response

    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy", "service": "agentic-whatsapp-bot"}

# Vercel serverless function handler
def handler(event, context):
    """
    Vercel serverless function handler
    """
    from mangum import Mangum

    # Create Mangum handler for FastAPI
    handler = Mangum(app)

    # Handle the event
    return handler(event, context)

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)