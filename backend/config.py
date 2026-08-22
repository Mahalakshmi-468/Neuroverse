"""
Central configuration for NeuroVerse.

All values are read from environment variables so the app can be
configured without touching code (see .env.example).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# --- LLM (optional) ---------------------------------------------------
# If ANTHROPIC_API_KEY is set, NeuroVerse generates stories with Claude.
# If it is not set, NeuroVerse automatically falls back to the built-in
# offline story generator so the app always works out of the box.
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
LLM_ENABLED = bool(ANTHROPIC_API_KEY)

# --- Storage ------------------------------------------------------------
DB_PATH = os.environ.get("NEUROVERSE_DB", str(BASE_DIR / "neuroverse.db"))

# --- Gameplay -------------------------------------------------------------
MAX_CHAPTERS = int(os.environ.get("NEUROVERSE_MAX_CHAPTERS", "6"))
STARTING_HEALTH = 100
