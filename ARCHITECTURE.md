# Architecture

## Current (software prototype)

```
                 ┌─────────────────────┐
                 │   Browser (UI)       │
                 │  index.html/css/js   │
                 │  Speech Recognition  │
                 │  Speech Synthesis    │
                 └──────────┬───────────┘
                            │ fetch() JSON
                            ▼
                 ┌─────────────────────┐
                 │     FastAPI app      │
                 │      backend/app.py  │
                 └──────────┬───────────┘
                            │
              ┌─────────────┼──────────────┐
              ▼                            ▼
   ┌─────────────────────┐      ┌─────────────────────┐
   │   story_engine.py    │      │    database.py        │
   │  orchestrates scene   │◄────┤  SQLite persistence   │
   │  generation + rules   │─────►  (sessions table)      │
   └──────────┬───────────┘      └─────────────────────┘
              │
     ┌────────┴─────────┐
     ▼                   ▼
┌───────────┐   ┌─────────────────────┐
│ Offline    │   │  llm_engine.py       │
│ generator  │   │  Anthropic API call  │
│ (always    │   │  (only if API key    │
│ available) │   │  is configured)      │
└───────────┘   └─────────────────────┘
```

Design choices:
- **Graceful degradation.** `story_engine.py` always tries the LLM path first when configured, and falls back to the deterministic offline generator on any exception (missing key, network error, malformed response). The player never sees a broken turn.
- **Structured LLM output.** `llm_engine.py` forces Claude to reply through a `write_scene` tool call with a strict JSON schema, so the model's output always slots directly into game state — no fragile text parsing.
- **State lives server-side.** The client only holds the session ID; the authoritative game state is persisted in SQLite and reloaded on every request, so a mission survives a page refresh or a closed tab.
- **Engine-agnostic game mechanics.** Traits, inventory, achievements, and the riddle chapter are all computed in `story_engine.py` from the *player's choice text* and *resulting state*, never from how a scene was generated. That's what lets the riddle chapter, for example, work identically whether Claude or the offline generator wrote the surrounding narration — the mechanic doesn't care which engine was used.
- **Achievement diffing lives in the API layer.** `story_engine.py` returns the full, accumulated achievement list; `app.py` diffs it against the list from *before* the turn to compute `new_achievements`, so the frontend can show a toast without re-deriving game logic itself.

## v0.3 additions

```
story_engine.py
 ├─ WORLDS (16)            world / companion / artifact per keyword, + deterministic fallback
 ├─ CHOICE_PROFILES        choice text → (event text, trait, delta)   [offline mode]
 ├─ RIDDLES                riddle text + answer keywords              [both modes]
 ├─ ITEM_POOL              inventory items, granted probabilistically or on riddle success
 ├─ _achievement_defs()    10 achievement predicates over game state
 └─ ENDING_FLAVOR          closing-scene text keyed by dominant trait
```

Traits, inventory, and achievements are stored as JSON columns in SQLite (`database.py` migrates existing databases in place via `ALTER TABLE`, so upgrading never drops a saved mission).

## Future hardware path

```
Browser/AI backend → ESP32 → LEDs / speaker / sensors / RFID
```

The FastAPI backend is transport-agnostic: the same `/api/adventure` and `/api/choice` endpoints that the browser calls today could equally be called by firmware on an ESP32, driving LEDs, a speaker, and sensors instead of a screen. No backend changes are anticipated for that transition — only a new physical client.
