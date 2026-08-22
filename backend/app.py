import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, database, story_engine
from .models import AdventureRequest, ChoiceRequest

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    yield


app = FastAPI(title="NeuroVerse API", version="0.3.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(config.BASE_DIR / "frontend")), name="static")


def _with_new_achievements(saved: dict, previously_unlocked: set) -> dict:
    """Attach which achievements (if any) just unlocked this turn, so the
    frontend can show a toast without re-deriving it from raw state."""
    saved = dict(saved)
    saved["new_achievements"] = [a for a in saved.get("achievements", []) if a not in previously_unlocked]
    return saved


@app.get("/")
def home():
    return FileResponse(str(config.BASE_DIR / "frontend" / "index.html"))


@app.get("/api/health")
def health():
    return {"status": "ok", "llm_enabled": config.LLM_ENABLED, "model": config.ANTHROPIC_MODEL if config.LLM_ENABLED else None}


@app.get("/api/achievements")
def achievements_catalog():
    """Metadata (name/description) for every achievement id the engine can unlock."""
    return {aid: {"name": name, "description": desc} for aid, name, desc in
            [(a, n, d) for a, n, d, _pred in story_engine._achievement_defs()]}


@app.post("/api/adventure")
def adventure(req: AdventureRequest):
    state = story_engine.generate_adventure(req.idea, req.player)
    saved = database.create_session(state)
    return _with_new_achievements(saved, previously_unlocked=set())


@app.post("/api/choice")
def choice(req: ChoiceRequest):
    try:
        current = database.load_session(req.session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found. Start a new adventure.")

    if current["finished"]:
        raise HTTPException(status_code=400, detail="This adventure has already finished.")

    previously_unlocked = set(current.get("achievements", []))
    next_state = story_engine.generate_next(current, req.choice)
    saved = database.update_session(req.session_id, next_state)
    return _with_new_achievements(saved, previously_unlocked)


@app.get("/api/sessions")
def sessions():
    return database.list_sessions()


@app.get("/api/session/{session_id}")
def get_session(session_id: str):
    try:
        return database.load_session(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Session not found.")


@app.delete("/api/session/{session_id}")
def delete_session(session_id: str):
    database.delete_session(session_id)
    return {"deleted": session_id}
