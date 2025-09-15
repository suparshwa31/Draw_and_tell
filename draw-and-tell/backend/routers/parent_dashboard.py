# Endpoints: recap, sessions, media serving
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os

from backend.utils.local_storage import local_storage
from backend.services.tts_service import tts_service
from backend.services.cv_service import cv_service

router = APIRouter(prefix="/parent", tags=["parent_dashboard"])


class ParentSessionSummary(BaseModel):
    id: int
    timestamp: str
    prompt: str
    drawings_count: int


class ParentRecap(BaseModel):
    session_id: int
    prompt: str
    num_drawings: int
    skills: List[str]
    top_tags: List[str]
    highlights: str


@router.get("/sessions", response_model=List[ParentSessionSummary])
def list_sessions() -> List[ParentSessionSummary]:
    import sqlite3
    db_path = local_storage.db_path
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id, timestamp, prompt FROM sessions ORDER BY datetime(timestamp) DESC")
        sessions = [dict(r) for r in cur.fetchall()]
        summaries: List[ParentSessionSummary] = []
        for s in sessions:
            cur.execute("SELECT COUNT(*) FROM drawings WHERE session_id = ?", (s["id"],))
            count = cur.fetchone()[0]
            summaries.append(ParentSessionSummary(id=s["id"], timestamp=s["timestamp"], prompt=s["prompt"], drawings_count=count))
        return summaries


@router.get("/session/{session_id}")
def get_session(session_id: int) -> Dict[str, Any]:
    try:
        session = local_storage.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recap/{session_id}", response_model=ParentRecap)
def recap(session_id: int) -> ParentRecap:
    session = local_storage.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    drawings = session.get("drawings", [])
    prompt = session.get("prompt", "")
    
    # Analyze each drawing for detailed insights
    all_tags: List[str] = []
    color_mentions = 0
    people_mentions = 0
    nature_mentions = 0
    object_mentions = 0
    detailed_drawings = 0
    
    for drawing in drawings:
        caption = drawing.get("caption", "").lower()
        tags = drawing.get("tags", [])
        all_tags.extend(tags)
        
        # Count thematic elements
        if "color" in caption or any("color" in tag.lower() for tag in tags):
            color_mentions += 1
            
        if "people" in caption or "person" in caption or "child" in caption:
            people_mentions += 1
            
        if any(word in caption for word in ["tree", "animal", "flower", "nature", "bird", "fish"]):
            nature_mentions += 1
            
        if any(word in caption for word in ["car", "house", "building", "toy", "object"]):
            object_mentions += 1
            
        # Assess complexity
        if len(caption.split()) > 8:
            detailed_drawings += 1

    # Generate skills based on analysis
    skills: List[str] = []
    if color_mentions > 0:
        skills.append("Color Recognition & Expression")
    if people_mentions > 0:
        skills.append("Social Understanding & Empathy")
    if nature_mentions > 0:
        skills.append("Environmental Awareness")
    if object_mentions > 0:
        skills.append("Spatial Reasoning & Object Recognition")
    if detailed_drawings > 0:
        skills.append("Attention to Detail")
    if len(drawings) > 1:
        skills.append("Creative Persistence")
    if not skills:
        skills.append("Creative Expression & Imagination")

    # Generate top tags
    from collections import Counter
    tag_counts = Counter(all_tags)
    top_tags = [t for t, _ in tag_counts.most_common(5)]

    # Create detailed summary
    summary_parts = []
    
    if len(drawings) == 1:
        summary_parts.append(f"Your child created 1 drawing")
    else:
        summary_parts.append(f"Your child created {len(drawings)} drawings")
    
    if prompt:
        summary_parts.append(f"in response to the prompt: '{prompt}'")
    
    # Add thematic analysis
    themes = []
    if color_mentions > 0:
        themes.append("color exploration")
    if people_mentions > 0:
        themes.append("people and relationships")
    if nature_mentions > 0:
        themes.append("nature and environment")
    if object_mentions > 0:
        themes.append("objects and structures")
    
    if themes:
        summary_parts.append(f"focusing on {', '.join(themes)}")
    
    # Add complexity assessment
    if detailed_drawings > 0:
        summary_parts.append(f"with {detailed_drawings} detailed composition{'s' if detailed_drawings > 1 else ''}")
    
    # Add encouraging note
    if len(drawings) > 1:
        summary_parts.append("showing great creative persistence!")
    else:
        summary_parts.append("demonstrating wonderful creativity!")

    summary = ". ".join(summary_parts) + "."

    return ParentRecap(
        session_id=session_id,
        prompt=prompt,
        num_drawings=len(drawings),
        skills=skills,
        top_tags=top_tags,
        highlights=summary
    )


@router.get("/image/{drawing_id}")
def get_image(drawing_id: int):
    drawing = local_storage.get_drawing(drawing_id)
    if not drawing:
        raise HTTPException(status_code=404, detail="Drawing not found")
    image_path = drawing.get("image_path")
    if not image_path or not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path, media_type="image/png")






@router.get("/tts-cache")
def get_tts_cache_info():
    """Get TTS cache statistics"""
    try:
        cache_info = tts_service.get_cache_info()
        return {
            "cache_info": cache_info,
            "hit_rate": cache_info["hits"] / (cache_info["hits"] + cache_info["misses"]) if (cache_info["hits"] + cache_info["misses"]) > 0 else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts-cache/clear")
def clear_tts_cache():
    """Clear TTS cache"""
    try:
        tts_service.clear_cache()
        return {"message": "TTS cache cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cv-cache")
def get_cv_cache_info():
    """Get CV cache statistics"""
    try:
        cache_info = cv_service.get_cache_info()
        return {
            "cache_info": cache_info,
            "hit_rate": cache_info["hits"] / (cache_info["hits"] + cache_info["misses"]) if (cache_info["hits"] + cache_info["misses"]) > 0 else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cv-cache/clear")
def clear_cv_cache():
    """Clear CV cache"""
    try:
        cv_service.clear_cache()
        return {"message": "CV cache cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cv-optimize")
def optimize_cv_memory():
    """Optimize CV memory usage"""
    try:
        cv_service.optimize_memory()
        return {"message": "CV memory optimized successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tts-optimize")
def optimize_tts_memory():
    """Optimize TTS memory usage"""
    try:
        tts_service.optimize_memory()
        return {"message": "TTS memory optimized successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
