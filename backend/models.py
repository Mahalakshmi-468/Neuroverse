from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class AdventureRequest(BaseModel):
    idea: str = Field(..., min_length=1, max_length=500)
    player: str = Field(default="Explorer", max_length=60)


class ChoiceRequest(BaseModel):
    session_id: str
    choice: str = Field(..., min_length=1, max_length=200)


class SessionSummary(BaseModel):
    session_id: str
    player: str
    world: str
    chapter: int
    score: int
    health: int
    finished: bool
    updated_at: str


class Traits(BaseModel):
    bravery: int = 0
    curiosity: int = 0
    kindness: int = 0


class StoryState(BaseModel):
    session_id: str
    player: str
    idea: str
    world: str
    companion: str
    artifact: str
    chapter: int
    max_chapters: int
    score: int
    health: int
    finished: bool
    history: List[dict]
    story: str
    mission: str
    choices: List[str]
    source: str  # "llm" or "offline"
    traits: Dict[str, int] = {"bravery": 0, "curiosity": 0, "kindness": 0}
    inventory: List[str] = []
    achievements: List[str] = []
    puzzle_correct: int = 0
    new_achievements: Optional[List[str]] = None
