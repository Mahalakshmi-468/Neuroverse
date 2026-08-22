# NeuroVerse — Project Overview

## Problem
Traditional toys and games usually provide predefined rules and repeated experiences.

## Solution
NeuroVerse combines AI storytelling and interactive gameplay so a player's imagination becomes the input to a changing adventure.

## Innovation
The prototype demonstrates an imagination-driven loop: idea → world → story → mission → choice → evolving story. Future versions can connect the same software to a physical ESP32-based toy.

## Scope
This submission is a software prototype of the larger smart-toy vision. Hardware integration is documented as future work rather than claimed as completed.

## v0.2 upgrade
The prototype now supports optional live AI narration (Claude, via the Anthropic API) with a deterministic offline fallback, persists missions to a local database so a story can be resumed, and adds real gameplay mechanics (energy, score, a defined ending) on top of a redesigned interface. See `README.md` for setup and `ARCHITECTURE.md` for how the pieces fit together.

## v0.3 upgrade — "Advanced"
Gameplay now has real depth on top of the same reliable dual-engine core: a player's choices grow three "Imagination DNA" traits (bravery, curiosity, kindness), which unlock items into an inventory, ten achievements, and change which of several ending flavors a mission closes on. A mid-adventure riddle chapter tests the player without ever depending on which engine (Claude or offline) wrote the surrounding scene. The world roster doubled from 8 to 16, and ideas that don't match a keyword now land on a deterministic "surprise" world instead of always defaulting to fantasy.
