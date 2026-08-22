# NeuroVerse
### Where Imagination Becomes Reality

NeuroVerse is an AI-powered interactive storytelling prototype for a future smart toy. A player describes an adventure idea; NeuroVerse builds a world, casts a companion, narrates a mission, and evolves the story around every choice the player makes — with progress saved so a mission can be resumed later.

```
Imagination → Story Engine → Mission → Player Choice → Narration → Memory → Next Scene
```

## What's new in v0.4 (Real gameplay)

- **A choice countdown timer.** Every decision has 12 seconds on the clock — pick fast and you get a visible "Speed bonus!" flash. Adds real time pressure instead of a static menu.
- **A guardian reflex mini-game.** Before the mid-adventure riddle, players have to actually *play* — tap a moving target 5 times in 6 seconds to "impress the guardian" before the riddle choices unlock.
- **Confetti bursts** on every achievement unlock, and rebranded UI copy ("A Playable Story Game", "New game") so it reads as a game, not just a narrated story.

## What's new in v0.3 (Advanced)

- **Imagination DNA.** Three traits — bravery, curiosity, kindness — grow from the choices a player makes, shown as live meters, and shape which of several ending flavors the mission closes on.
- **Inventory.** Items are discovered across the adventure (guaranteed on solving the riddle chapter, chance-based otherwise) and shown as collectible chips.
- **Achievements.** Ten milestones (First Find, Riddle Master, Flawless Victory, ...) unlock as you play, with an in-app toast the moment one lands. `GET /api/achievements` exposes the full catalog.
- **A mid-adventure riddle.** One chapter per mission poses a guardian's riddle; solving it (by picking an answer that matches its theme) grants bonus score, a curiosity boost, and a guaranteed item — and it works identically whether the scene came from Claude or the offline generator.
- **16 worlds, not 8** — pirate isles, a volcano, a haunted manor, a neon cyber-district, and more — plus a deterministic "surprise" world for ideas that don't match any keyword, instead of always defaulting to fantasy.
- **Multiple endings.** The closing scene is flavored by whichever trait the player leaned on most.

## What's new in v0.2

- **Real LLM narration (optional).** Set `ANTHROPIC_API_KEY` and NeuroVerse asks Claude to write each scene live, with a structured-output tool call so the reply always fits the game state. No key? The app runs the same, using a built-in offline generator — nothing breaks.
- **Persistent missions.** Every adventure is saved to a local SQLite database, so players can close the tab and resume later. The launch screen lists recent missions with a resume/delete option.
- **Game mechanics.** An energy meter, a running score, a fixed mission length with a real ending, and a chapter log.
- **Redesigned interface.** A "mission console" UI: status panel, live-typed narration, and a chapter log, built mobile-first.
- **Test suite.** Unit tests for the story engine plus API-level tests using FastAPI's test client.

## Project structure

```
neuroverse/
├── backend/
│   ├── app.py            FastAPI app & routes
│   ├── config.py         Environment-driven settings
│   ├── database.py       SQLite persistence
│   ├── llm_engine.py      Claude-powered scene generation (optional)
│   ├── models.py          Pydantic request/response models
│   └── story_engine.py    Orchestration + offline generator + game rules
├── frontend/
│   ├── index.html
│   ├── css/style.css
│   └── js/app.js
├── tests/
│   ├── test_story_engine.py
│   └── test_api.py
├── requirements.txt
├── .env.example
└── README.md
```

## Run it

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env           # optional: add ANTHROPIC_API_KEY to enable live AI narration

uvicorn backend.app:app --reload
```

Open **http://127.0.0.1:8000**.

Without an API key, stories come from the deterministic offline engine (same idea → same opening, every time — handy for demos). With `ANTHROPIC_API_KEY` set, every scene is generated live by Claude, and the app falls back to the offline engine automatically if a call ever fails.

## Configuration

All configuration is via environment variables (see `.env.example`):

| Variable | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | *(unset)* | Enables live AI narration when set |
| `ANTHROPIC_MODEL` | `claude-sonnet-5` | Model used for narration |
| `NEUROVERSE_DB` | `neuroverse.db` | SQLite file location |
| `NEUROVERSE_MAX_CHAPTERS` | `6` | Chapters per adventure before it concludes |

## Deploying (Railway)

This repo includes a `railway.toml`. To deploy:

1. Push this repo to GitHub.
2. On [railway.app](https://railway.app), click **New Project → Deploy from GitHub repo** and pick this repo.
3. Railway auto-detects Python and reads `railway.toml` for the build/start commands.
4. Add a **Volume** (Settings → Volumes) mounted at `/data`, then set the `NEUROVERSE_DB` environment variable to `/data/neuroverse.db` so missions survive redeploys.
5. Optionally set `ANTHROPIC_API_KEY` and `ANTHROPIC_MODEL` in the Variables tab to enable live AI narration.
6. Railway assigns a public domain automatically (or generate one under Settings → Networking), e.g. `https://neuroverse-production.up.railway.app`.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/adventure` | Start a new adventure — `{idea, player}` |
| `POST` | `/api/choice` | Advance the story — `{session_id, choice}` |
| `GET` | `/api/sessions` | List recent saved missions |
| `GET` | `/api/session/{id}` | Load a specific mission |
| `DELETE` | `/api/session/{id}` | Delete a mission |
| `GET` | `/api/health` | Engine status (offline vs. live AI) |

## Tests

```bash
pytest tests/ -v
```

## Voice

Voice input/output uses the browser's built-in `SpeechRecognition` and `speechSynthesis` APIs — no server-side speech processing, so it works offline and costs nothing. Browser support varies (best in Chrome); the app degrades gracefully to typing when unsupported.

## Roadmap

See `ROADMAP.md` for the planned hardware (ESP32-based) version and next-version features like an "Imagination DNA" player profile.
