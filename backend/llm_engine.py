"""
Optional LLM-powered story generation.

When ANTHROPIC_API_KEY is set, NeuroVerse asks Claude to write each
scene and forces a structured JSON reply via tool-use, so the response
always matches the shape the game engine expects. If the key is missing
or a call fails for any reason, story_engine.py falls back to the
offline generator — the app never breaks because of network/LLM issues.
"""
import logging

from . import config

logger = logging.getLogger("neuroverse.llm")

_SCENE_TOOL = {
    "name": "write_scene",
    "description": "Write the next scene of a children's interactive adventure.",
    "input_schema": {
        "type": "object",
        "properties": {
            "story": {
                "type": "string",
                "description": "2-4 vivid, age-appropriate sentences narrating what just happened.",
            },
            "mission": {
                "type": "string",
                "description": "One sentence describing the player's next goal.",
            },
            "choices": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 3,
                "maxItems": 3,
                "description": "Three short, distinct action choices for the player.",
            },
            "health_delta": {
                "type": "integer",
                "description": "Change to player's health this turn, from -20 to +10. Use negative sparingly and never below -20.",
            },
            "item_gained": {
                "type": ["string", "null"],
                "description": (
                    "A short name for an item the player discovers this scene "
                    "(e.g. 'a tarnished silver key'), or null if nothing is found. "
                    "Don't force one every turn — most scenes should have none."
                ),
            },
        },
        "required": ["story", "mission", "choices", "health_delta", "item_gained"],
    },
}

_SYSTEM_PROMPT = (
    "You are the narrator engine inside NeuroVerse, an interactive storytelling "
    "toy for children. Write warm, imaginative, age-appropriate scenes (no "
    "violence, no scary gore, no real-world harm). Keep continuity with the "
    "world, companion, and artifact given to you, and with the player's "
    "inventory and personality traits. Always respond by calling "
    "the write_scene tool — never plain text."
)


def _client():
    import anthropic  # imported lazily so the app works without the package installed

    return anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)


def _call_claude(user_prompt: str) -> dict:
    client = _client()
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=700,
        system=_SYSTEM_PROMPT,
        tools=[_SCENE_TOOL],
        tool_choice={"type": "tool", "name": "write_scene"},
        messages=[{"role": "user", "content": user_prompt}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "write_scene":
            return block.input
    raise RuntimeError("Claude did not return a write_scene tool call")


def generate_opening_scene(idea: str, player: str, world: str, companion: str, artifact: str) -> dict:
    prompt = (
        f"Start a brand-new adventure.\n"
        f"Player name: {player}\n"
        f"Player's idea: \"{idea}\"\n"
        f"World: {world}\n"
        f"Companion: {companion}\n"
        f"Artifact to eventually find: {artifact}\n"
        f"This is chapter 1. Introduce the world, the companion, and a gentle "
        f"early obstacle. health_delta should be 0 for the opening scene. "
        f"item_gained should almost always be null in the opening scene."
    )
    return _call_claude(prompt)


def generate_next_scene(state: dict, choice: str, is_puzzle_chapter: bool = False, dominant_trait: str | None = None) -> dict:
    recent_history = state["history"][-3:]
    history_lines = "\n".join(
        f"- Chapter {h['chapter']}: player chose \"{h['choice']}\"" for h in recent_history
    )
    traits = state.get("traits", {"bravery": 0, "curiosity": 0, "kindness": 0})
    inventory = state.get("inventory", [])

    puzzle_note = (
        "\nNote: right after this scene the engine will present the player with a "
        "guardian's riddle — you do NOT need to write the riddle yourself, just "
        "write a natural scene that could plausibly lead into a guardian appearing."
        if is_puzzle_chapter else ""
    )
    ending_note = (
        f"\nThis is the FINAL chapter — resolve the adventure and let the player find "
        f"or reach {state['artifact']}. The player's strongest trait has been {dominant_trait}; "
        f"let the ending reflect that quality if it fits naturally, but keep it a single "
        f"warm, satisfying resolution (the engine will append one closing sentence after yours)."
        if dominant_trait else ""
    )

    prompt = (
        f"Continue the adventure.\n"
        f"Player name: {state['player']}\n"
        f"World: {state['world']}\n"
        f"Companion: {state['companion']}\n"
        f"Artifact goal: {state['artifact']}\n"
        f"Current chapter: {state['chapter']} of {state['max_chapters']}\n"
        f"Current health: {state['health']}\n"
        f"Traits so far — bravery: {traits.get('bravery', 0)}, curiosity: {traits.get('curiosity', 0)}, kindness: {traits.get('kindness', 0)}\n"
        f"Inventory so far: {', '.join(inventory) if inventory else 'nothing yet'}\n"
        f"Recent history:\n{history_lines or '- none yet'}\n"
        f"Player's latest choice: \"{choice}\"\n"
        f"Write what happens next as a direct consequence of that choice."
        f"{puzzle_note}{ending_note}"
    )
    return _call_claude(prompt)
