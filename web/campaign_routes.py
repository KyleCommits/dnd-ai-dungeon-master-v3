# web/campaign_routes.py
import asyncio
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import uuid
from datetime import datetime

from src.campaign_generation.campaign_orchestrator import CampaignOrchestrator

# Configure logging
logger = logging.getLogger(__name__)

# Create router
campaign_router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])

# Store active generation sessions
active_generations: Dict[str, Dict[str, Any]] = {}

class CampaignGenerationRequest(BaseModel):
    prompt: str
    user_preferences: Optional[Dict[str, Any]] = {}

class GenerationStatus(BaseModel):
    session_id: str
    status: str  # "starting", "in_progress", "completed", "failed"
    current_stage: str
    progress_percent: int
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

@campaign_router.post("/generate")
async def start_campaign_generation(request: CampaignGenerationRequest):
    """Start a new campaign generation process"""

    if not request.prompt or len(request.prompt.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Campaign prompt must be at least 10 characters long"
        )

    if len(request.prompt) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Campaign prompt must be less than 1000 characters"
        )

    # Create session
    session_id = str(uuid.uuid4())

    # Initialize session data
    active_generations[session_id] = {
        "status": "starting",
        "current_stage": "Initializing",
        "progress_percent": 0,
        "message": "Preparing campaign generation...",
        "started_at": datetime.now(),
        "prompt": request.prompt,
        "preferences": request.user_preferences,
        "result": None,
        "error": None
    }

    # Start generation in background
    asyncio.create_task(_run_generation(session_id, request.prompt))

    logger.info(f"Started campaign generation session: {session_id}")

    return {
        "session_id": session_id,
        "status": "started",
        "message": "Campaign generation started. Use /status/{session_id} to track progress."
    }

@campaign_router.get("/status/{session_id}")
async def get_generation_status(session_id: str) -> GenerationStatus:
    """Get the status of a campaign generation session"""

    if session_id not in active_generations:
        raise HTTPException(status_code=404, detail="Session not found")

    session_data = active_generations[session_id]

    return GenerationStatus(
        session_id=session_id,
        status=session_data["status"],
        current_stage=session_data["current_stage"],
        progress_percent=session_data["progress_percent"],
        message=session_data["message"],
        result=session_data.get("result"),
        error=session_data.get("error")
    )

@campaign_router.get("/stream/{session_id}")
async def stream_generation_progress(session_id: str):
    """Stream real-time updates for campaign generation"""

    if session_id not in active_generations:
        raise HTTPException(status_code=404, detail="Session not found")

    async def generate_updates():
        last_message = ""

        while session_id in active_generations:
            session_data = active_generations[session_id]
            current_message = session_data["message"]

            # Only send update if message changed
            if current_message != last_message:
                update = {
                    "status": session_data["status"],
                    "stage": session_data["current_stage"],
                    "progress": session_data["progress_percent"],
                    "message": current_message,
                    "timestamp": datetime.now().isoformat()
                }

                yield f"data: {json.dumps(update)}\n\n"
                last_message = current_message

            # Break if completed or failed
            if session_data["status"] in ["completed", "failed"]:
                break

            await asyncio.sleep(1)  # Update every second

    return StreamingResponse(
        generate_updates(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive"
        }
    )

@campaign_router.delete("/session/{session_id}")
async def cancel_generation(session_id: str):
    """Cancel an active generation session"""

    if session_id not in active_generations:
        raise HTTPException(status_code=404, detail="Session not found")

    # Mark as cancelled (the background task will handle cleanup)
    active_generations[session_id]["status"] = "cancelled"
    active_generations[session_id]["message"] = "Generation cancelled by user"

    return {"message": "Generation cancelled"}

@campaign_router.get("/sessions")
async def list_active_sessions():
    """List all active generation sessions"""

    sessions = []
    for session_id, data in active_generations.items():
        sessions.append({
            "session_id": session_id,
            "status": data["status"],
            "stage": data["current_stage"],
            "progress": data["progress_percent"],
            "started_at": data["started_at"].isoformat(),
            "prompt": data["prompt"][:100] + "..." if len(data["prompt"]) > 100 else data["prompt"]
        })

    return {"sessions": sessions}

async def _run_generation(session_id: str, prompt: str):
    """Background task to run campaign generation"""

    orchestrator = CampaignOrchestrator()

    try:
        # Update session status
        active_generations[session_id]["status"] = "in_progress"
        active_generations[session_id]["message"] = "Starting campaign generation..."

        # Progress callback
        async def progress_callback(message: str, current_stage: int, total_stages: int):
            if session_id in active_generations:
                progress_percent = int((current_stage / total_stages) * 100)
                active_generations[session_id].update({
                    "current_stage": f"Stage {current_stage}/{total_stages}",
                    "progress_percent": progress_percent,
                    "message": message
                })
                logger.info(f"Session {session_id}: {message} ({progress_percent}%)")

        # Stage completion callback
        async def stage_callback(stage_name: str, stage_results: Dict[str, Any]):
            if session_id in active_generations:
                active_generations[session_id]["message"] = f"Completed: {stage_name}"
                logger.info(f"Session {session_id}: Completed {stage_name}")

        # Check if cancelled
        if active_generations[session_id]["status"] == "cancelled":
            return

        # Run generation
        result = await orchestrator.generate_campaign(
            prompt,
            progress_callback=progress_callback,
            stage_callback=stage_callback
        )

        # Save campaign
        saved_path = await orchestrator.save_campaign(result)

        # Update session with success
        active_generations[session_id].update({
            "status": "completed",
            "current_stage": "Complete",
            "progress_percent": 100,
            "message": f"Campaign generated successfully! Saved to: {saved_path}",
            "result": {
                "title": result.get("title", "Generated Campaign"),
                "description": result.get("description", ""),
                "file_path": saved_path,
                "metadata": result.get("metadata", {}),
                "content_preview": result.get("content", "")[:500] + "..." if result.get("content") else ""
            }
        })

        logger.info(f"Campaign generation completed for session: {session_id}")

    except Exception as e:
        logger.error(f"Campaign generation failed for session {session_id}: {e}")

        if session_id in active_generations:
            active_generations[session_id].update({
                "status": "failed",
                "message": f"Generation failed: {str(e)}",
                "error": str(e)
            })

    # Clean up old sessions after 1 hour
    asyncio.create_task(_cleanup_session(session_id, 3600))

async def _cleanup_session(session_id: str, delay_seconds: int):
    """Clean up session data after delay"""
    await asyncio.sleep(delay_seconds)
    if session_id in active_generations:
        del active_generations[session_id]
        logger.info(f"Cleaned up session: {session_id}")

# Health check endpoint
@campaign_router.get("/health")
async def campaign_health_check():
    """Check if campaign generation system is healthy"""

    try:
        # Test that we can import and initialize key components
        from src.campaign_generation.campaign_context_loader import CampaignContextLoader
        context_loader = CampaignContextLoader()

        # Check if we have campaign examples
        examples = context_loader.get_example_campaigns(1)

        return {
            "status": "healthy",
            "campaign_examples_available": len(examples),
            "active_sessions": len(active_generations),
            "message": "Campaign generation system is operational"
        }

    except Exception as e:
        logger.error(f"Campaign health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Campaign generation system has issues"
        }