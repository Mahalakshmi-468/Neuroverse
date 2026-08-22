"""
NeuroVerse story engine — v0.3 "Advanced".

generate_adventure() / generate_next() are the only two entry points
used by the API layer. Each tries the LLM engine first (if configured)
and transparently falls back to the deterministic offline generator on
any failure, so gameplay never breaks.

New in v0.3:
- 16 worlds instead of 8, plus a deterministic "surprise" world for
  ideas that don't match a keyword (instead of always defaulting to
  fantasy).
- "Imagination DNA": three traits (bravery, curiosity, kindness) that
  grow from the choices a player makes, in both offline and LLM modes.
- Inventory: items are discovered across the adventure.
- A mid-adventure riddle chapter, engine-agnostic (works whether the
  scene came from Claude or the offline generator).
- Achievements, unlocked as milestones are hit.
- Multiple endings, flavoured by the player's dominant trait.
"""
import hashlib
import logging
import random

from . import config
from . import llm_engine

logger = logging.getLogger("neuroverse.story")

# --------------------------------------------------------------------- #
# Worlds
# --------------------------------------------------------------------- #
WORLDS = {
    "space": ("Nebula Frontier", "a stranded starship pilot", "the Crystal Core"),
    "dinosaur": ("Lost Jurassic Valley", "a young raptor", "the Golden Fossil"),
    "ocean": ("Sunken Moon Kingdom", "a curious octopus", "the Pearl of Tides"),
    "jungle": ("Emerald Jungle", "a clever parrot", "the Sunstone"),
    "fantasy": ("Kingdom of Luminara", "a tiny dragon", "the Heart Crystal"),
    "desert": ("Dunes of Sahara Prime", "a wise sand-fox", "the Sun Compass"),
    "arctic": ("Frostfall Peaks", "a talking snow owl", "the Aurora Shard"),
    "robot": ("Circuit City", "a friendly maintenance bot", "the Origin Core"),
    "pirate": ("Shattered Reef Isles", "a parrot first-mate", "the Sea King's Compass"),
    "volcano": ("Emberpeak Volcano", "a fire salamander", "the Phoenix Ember"),
    "sky": ("Skyreach Clouds", "a wind sprite", "the Storm Lantern"),
    "candy": ("Candy Cascade Valley", "a gummy-bear scout", "the Sugarplum Star"),
    "haunted": ("Hollow Manor", "a friendly ghost butler", "the Moonlit Locket"),
    "cave": ("The Whispering Caves", "a glowing cave bat", "the Echo Gem"),
    "cyber": ("Neon Circuit District", "a rogue helper-drone", "the Master Key"),
    "island": ("Forgotten Palm Atoll", "a chatty hermit crab", "the Tidecaller Shell"),
}

THREATS = [
    "a spreading shadow", "a mysterious storm", "a locked ancient gate",
    "a riddle-loving guardian", "a maze of shifting paths", "a sleeping giant",
]

# keyword -> (narration on choosing it, trait affected, trait delta)
CHOICE_PROFILES = {
    "explore": ("You follow a glowing trail and discover a hidden passage.", "curiosity", 2),
    "ask": ("Your companion remembers an old clue and reveals a safer route.", "kindness", 2),
    "search": ("You spot footprints and a strange symbol carved into the ground.", "curiosity", 1),
    "follow": ("The trail leads somewhere no one has been in a hundred years.", "curiosity", 1),
    "investigate": ("The symbol pulses with light the moment you touch it.", "curiosity", 2),
    "create": ("Your own plan surprises everyone, including you.", "bravery", 2),
    "climb": ("From higher up, the whole world suddenly makes sense.", "bravery", 2),
    "wait": ("Patience pays off as the path reveals itself in its own time.", "kindness", 1),
    "sing": ("Music echoes through the world and something ancient stirs.", "kindness", 2),
    "run": ("Speed gets you there before the danger even notices.", "bravery", 1),
    "help": ("Lending a hand turns a stranger into a friend.", "kindness", 3),
    "protect": ("Standing your ground earns quiet respect.", "kindness", 2),
    "share": ("What you give away comes back multiplied.", "kindness", 2),
    "fight": ("Courage carries you further than force ever could.", "bravery", 3),
    "sneak": ("Careful steps keep the whole plan alive.", "curiosity", 2),
    "build": ("Piece by piece, an idea becomes something real.", "bravery", 2),
}

DEFAULT_ENDING_EVENT = "Your decision changes the adventure in an unexpected way."

# --------------------------------------------------------------------- #
# Inventory
# --------------------------------------------------------------------- #
ITEM_POOL = [
    "a glowing shard", "a tattered map fragment", "a mysterious key",
    "a shimmering feather", "an old coin", "a strange seed",
    "a fragment of a song", "a carved stone token", "a warm ember in a jar",
    "a spiral shell that hums", "a bead of frozen starlight",
]

# --------------------------------------------------------------------- #
# Riddle chapter (engine-agnostic: works for both LLM & offline scenes,
# because it's resolved against the player's *chosen* text, not against
# how the scene itself was generated)
# --------------------------------------------------------------------- #
RIDDLES = [
    {
        "text": "I point the way but never move. Those who look closely find me hidden in symbols and signs.",
        "keywords": ["investigate", "search", "study", "examine", "symbol"],
    },
    {
        "text": "I am found by those who ask, not those who wait.",
        "keywords": ["ask", "talk", "question", "speak"],
    },
    {
        "text": "Follow me and I lead somewhere new; ignore me and you stay lost.",
        "keywords": ["follow", "trail", "track", "path"],
    },
    {
        "text": "Built not by hands but by imagination — dare to make your own.",
        "keywords": ["create", "build", "plan", "invent", "make"],
    },
]

# --------------------------------------------------------------------- #
# Achievements — id -> (name, description, predicate(state) -> bool)
# --------------------------------------------------------------------- #
def _achievement_defs():
    return [
        ("first_light", "New Beginnings", "Started your very first mission.",
         lambda s: s["chapter"] >= 1),
        ("first_find", "First Find", "Discovered your first item.",
         lambda s: len(s.get("inventory", [])) >= 1),
        ("treasure_hunter", "Treasure Hunter", "Collected three or more items.",
         lambda s: len(s.get("inventory", [])) >= 3),
        ("brave_heart", "Brave Heart", "Grew a strong sense of bravery.",
         lambda s: s.get("traits", {}).get("bravery", 0) >= 10),
        ("curious_mind", "Curious Mind", "Grew a strong sense of curiosity.",
         lambda s: s.get("traits", {}).get("curiosity", 0) >= 10),
        ("kind_soul", "Kind Soul", "Grew a strong sense of kindness.",
         lambda s: s.get("traits", {}).get("kindness", 0) >= 10),
        ("riddle_master", "Riddle Master", "Solved the guardian's riddle.",
         lambda s: s.get("puzzle_correct", 0) >= 1),
        ("close_call", "Close Call", "Finished a mission on very little energy.",
         lambda s: s["finished"] and 0 < s["health"] <= 20),
        ("flawless", "Flawless Victory", "Finished a mission at nearly full energy.",
         lambda s: s["finished"] and s["health"] >= 90),
        ("mission_complete", "Mission Complete", "Completed an adventure.",
         lambda s: s["finished"] and bool(s["choices"] == [])),
    ]


def _update_achievements(state: dict) -> list:
    unlocked = list(state.get("achievements", []))
    have = set(unlocked)
    for aid, _name, _desc, predicate in _achievement_defs():
        if aid not in have and predicate(state):
            unlocked.append(aid)
    return unlocked


ACHIEVEMENT_LOOKUP = {aid: (name, desc) for aid, name, desc, _ in _achievement_defs()}

# --------------------------------------------------------------------- #
# Endings by dominant trait
# --------------------------------------------------------------------- #
ENDING_FLAVOR = {
    "bravery": "{player} didn't wait for the danger to pass — {player} walked straight through it, and {companion} has never been prouder.",
    "curiosity": "Every question {player} asked led to another, until the whole mystery finally made sense.",
    "kindness": "It wasn't strength that won the day — it was every small kindness {player} showed along the way.",
    "default": "{player} and {companion} made it, together, exactly as they were meant to.",
}


def _dominant_trait(state: dict) -> str:
    traits = state.get("traits", {"bravery": 0, "curiosity": 0, "kindness": 0})
    best = max(traits, key=lambda k: traits[k])
    if traits[best] == 0:
        return "default"
    return best


# --------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------- #
def detect_world(idea: str) -> str:
    text = idea.lower()
    for key in WORLDS:
        if key in text:
            return key
    # No keyword matched: pick a deterministic "surprise" world so
    # unmatched ideas don't all collapse into the same default.
    rng = _seeded_random(idea)
    return rng.choice(list(WORLDS.keys()))


def _seeded_random(seed_text: str) -> random.Random:
    seed = int(hashlib.md5(seed_text.encode()).hexdigest()[:8], 16)
    return random.Random(seed)


def _puzzle_chapter_number(max_chapters: int) -> int:
    return max(2, max_chapters // 2)


def _pick_riddle(idea: str) -> dict:
    rng = _seeded_random(idea + "|riddle")
    return rng.choice(RIDDLES)


def _clamp_trait(value: int) -> int:
    return max(0, min(30, value))


def _apply_choice_traits(state: dict, choice: str):
    lower = choice.lower()
    traits = state.setdefault("traits", {"bravery": 0, "curiosity": 0, "kindness": 0})
    matched = False
    for kw, (_event, trait, delta) in CHOICE_PROFILES.items():
        if kw in lower:
            traits[trait] = _clamp_trait(traits[trait] + delta)
            matched = True
            break
    if not matched:
        traits["curiosity"] = _clamp_trait(traits["curiosity"] + 1)


def _add_item(state: dict, item: str):
    inventory = state.setdefault("inventory", [])
    if item and item not in inventory:
        inventory.append(item)


def _grant_item_maybe(state: dict, idea: str, chapter: int, forced: bool = False):
    rng = _seeded_random(f"{idea}|item|{chapter}")
    if forced or rng.random() < 0.55:
        held = set(state.get("inventory", []))
        remaining = [i for i in ITEM_POOL if i not in held] or ITEM_POOL
        _add_item(state, rng.choice(remaining))


def _base_state(idea: str, player: str) -> dict:
    key = detect_world(idea)
    world, companion, artifact = WORLDS[key]
    return {
        "player": player,
        "idea": idea,
        "world": world,
        "companion": companion,
        "artifact": artifact,
        "chapter": 1,
        "max_chapters": config.MAX_CHAPTERS,
        "score": 0,
        "health": config.STARTING_HEALTH,
        "finished": False,
        "history": [],
        "story": "",
        "mission": "",
        "choices": [],
        "source": "offline",
        "traits": {"bravery": 0, "curiosity": 0, "kindness": 0},
        "inventory": [],
        "achievements": [],
        "puzzle_correct": 0,
    }


# --------------------------------------------------------------------- #
# Offline (deterministic, no network) generator
# --------------------------------------------------------------------- #
def _offline_opening(state: dict) -> dict:
    rng = _seeded_random(state["idea"])
    threat = rng.choice(THREATS)
    state["story"] = (
        f"Welcome, {state['player']}. You have entered {state['world']}. "
        f"Your companion is {state['companion']}. Legends speak of {state['artifact']}, "
        f"but {threat} is blocking the path. Your adventure begins now."
    )
    state["mission"] = f"Find a way past {threat} and discover clues about {state['artifact']}."
    state["choices"] = ["Explore the mysterious path", "Ask your companion for help", "Search the surroundings"]
    state["source"] = "offline"
    return state


def _offline_next(state: dict, choice: str) -> dict:
    lower = choice.lower()
    event = next(
        (text for kw, (text, _t, _d) in CHOICE_PROFILES.items() if kw in lower),
        DEFAULT_ENDING_EVENT,
    )
    is_final = state["chapter"] + 1 >= state["max_chapters"]
    if is_final:
        state["story"] = (
            f"{event} At last, {state['player']} and {state['companion']} reach "
            f"{state['artifact']}. The adventure in {state['world']} is complete — for now."
        )
        state["mission"] = "Adventure complete. Start a new one whenever you're ready."
        state["choices"] = []
    else:
        state["story"] = event + f" Chapter {state['chapter'] + 1} has begun."
        state["mission"] = f"Use the new clue to move closer to {state['artifact']}."
        state["choices"] = ["Follow the clue", "Investigate the symbol", "Create your own plan"]
    state["source"] = "offline"
    return state


# --------------------------------------------------------------------- #
# Shared game-state mechanics (apply regardless of scene source)
# --------------------------------------------------------------------- #
def _apply_llm_scene(state: dict, scene: dict, is_final: bool):
    state["story"] = scene["story"]
    state["mission"] = scene["mission"]
    state["choices"] = [] if is_final else list(scene["choices"])[:3]
    delta = scene.get("health_delta", 0)
    try:
        delta = max(-20, min(10, int(delta)))
    except (TypeError, ValueError):
        delta = 0
    state["health"] = max(0, min(100, state["health"] + delta))
    state["source"] = "llm"


def generate_adventure(idea: str, player: str) -> dict:
    state = _base_state(idea, player)

    if config.LLM_ENABLED:
        try:
            scene = llm_engine.generate_opening_scene(
                idea, player, state["world"], state["companion"], state["artifact"]
            )
            _apply_llm_scene(state, scene, is_final=False)
            state["achievements"] = _update_achievements(state)
            return state
        except Exception:
            logger.exception("LLM opening scene failed, falling back to offline generator")

    state = _offline_opening(state)
    state["achievements"] = _update_achievements(state)
    return state


def generate_next(state: dict, choice: str) -> dict:
    state = dict(state)
    state.setdefault("traits", {"bravery": 0, "curiosity": 0, "kindness": 0})
    state.setdefault("inventory", [])
    state.setdefault("achievements", [])
    state.setdefault("puzzle_correct", 0)

    state.setdefault("history", []).append({"chapter": state["chapter"], "choice": choice})
    prev_chapter = state["chapter"]
    state["chapter"] += 1
    state["score"] += 10

    max_chapters = state.get("max_chapters", config.MAX_CHAPTERS)
    puzzle_chapter = _puzzle_chapter_number(max_chapters)
    is_final = state["chapter"] >= max_chapters or state["health"] <= 0

    # Resolve a riddle posed in the previous scene, if any — this check
    # works no matter whether that scene came from Claude or offline.
    if prev_chapter == puzzle_chapter:
        riddle = _pick_riddle(state["idea"])
        solved = any(kw in choice.lower() for kw in riddle["keywords"])
        if solved:
            state["score"] += 15
            state["puzzle_correct"] += 1
            state["traits"]["curiosity"] = _clamp_trait(state["traits"]["curiosity"] + 3)
            _grant_item_maybe(state, state["idea"], state["chapter"], forced=True)
        else:
            state["traits"]["curiosity"] = _clamp_trait(state["traits"]["curiosity"] + 1)

    # The choice itself nudges the player's Imagination DNA either way.
    _apply_choice_traits(state, choice)

    if config.LLM_ENABLED:
        try:
            scene = llm_engine.generate_next_scene(
                state, choice,
                is_puzzle_chapter=(state["chapter"] == puzzle_chapter and not is_final),
                dominant_trait=_dominant_trait(state) if is_final else None,
            )
            _apply_llm_scene(state, scene, is_final=is_final)
            item = scene.get("item_gained")
            if item:
                _add_item(state, str(item))
        except Exception:
            logger.exception("LLM next scene failed, falling back to offline generator")
            state = _offline_next(state, choice)
            if not is_final:
                _grant_item_maybe(state, state["idea"], state["chapter"])
    else:
        state = _offline_next(state, choice)
        if not is_final:
            _grant_item_maybe(state, state["idea"], state["chapter"])

    # Weave the riddle into the mission text for the puzzle chapter,
    # regardless of which engine wrote the scene.
    if state["chapter"] == puzzle_chapter and not is_final and state["choices"]:
        riddle = _pick_riddle(state["idea"])
        state["mission"] = state["mission"].rstrip() + f' A guardian blocks the way and asks a riddle: "{riddle["text"]}"'

    if state["health"] <= 0 and not is_final:
        # LLM scene dropped health below zero mid-adventure: end gracefully.
        is_final = True
        state["story"] += f" {state['player']} is out of energy and must rest. The adventure pauses here."
        state["choices"] = []

    # The offline generator decides its own ending a step ahead of the
    # `is_final` flag above (it ends once *no more* chapters would follow),
    # so re-derive the real "is this the end" signal from the resulting
    # choice list rather than trusting the earlier flag alone.
    is_final = is_final or not state["choices"]

    if is_final:
        dom = _dominant_trait(state)
        flavor = ENDING_FLAVOR.get(dom, ENDING_FLAVOR["default"]).format(
            player=state["player"], companion=state["companion"]
        )
        state["story"] = state["story"].rstrip() + " " + flavor
        state["choices"] = []

    state["finished"] = is_final or not state["choices"]
    state["achievements"] = _update_achievements(state)
    return state
