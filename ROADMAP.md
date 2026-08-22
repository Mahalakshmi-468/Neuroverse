# Roadmap

## Prototype (v0.1) — done
- Story generation
- Dynamic choices
- Narration
- Local memory (browser only)
- Futuristic interface

## v0.2 — done
- ✅ LLM API integration (Claude, via `llm_engine.py`, with offline fallback)
- ✅ Persistent database (SQLite, resumable missions)
- ✅ Gameplay mechanics (energy, score, defined ending)
- ✅ Redesigned "mission console" interface
- ✅ Test suite (story engine + API)

## v0.3 — done
- ✅ "Imagination DNA" trait system (bravery / curiosity / kindness) that shapes the ending
- ✅ Inventory — items discovered across the adventure
- ✅ Achievements (10, with live toast + `/api/achievements` catalog endpoint)
- ✅ Mid-adventure riddle chapter, engine-agnostic (works for both Claude and offline scenes)
- ✅ 16 worlds (up from 8) + deterministic "surprise" world for unmatched ideas
- ✅ Multiple endings, flavored by dominant trait
- ✅ Redesigned status/inventory/achievement panels in the frontend

## Next Version
- Character memory across multiple adventures (not just within one)
- Imagination DNA persisting and shaping future worlds across missions
- AI-generated puzzles and mini-games mid-chapter (currently one fixed riddle per mission)
- Multiplayer / shared adventures
- Illustration generation per scene

## Hardware Version
- ESP32
- microphone
- speaker
- RGB LEDs
- RFID/NFC
- motion sensors
