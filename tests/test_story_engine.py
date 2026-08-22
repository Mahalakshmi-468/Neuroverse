import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Force the offline engine for deterministic tests, regardless of the
# environment the tests are run in.
os.environ.pop("ANTHROPIC_API_KEY", None)

from backend import story_engine  # noqa: E402


def test_create_dinosaur_world():
    s = story_engine.generate_adventure("dinosaur adventure", "Maha")
    assert s["world"] == "Lost Jurassic Valley"
    assert s["chapter"] == 1
    assert s["source"] == "offline"
    assert len(s["choices"]) == 3


def test_unknown_idea_still_deterministic():
    a = story_engine.generate_adventure("something with no keyword at all", "Maha")
    b = story_engine.generate_adventure("something with no keyword at all", "Maha")
    assert a["world"] == b["world"]
    assert a["world"] in [w for w, _c, _a in story_engine.WORLDS.values()]


def test_choice_advances_chapter_and_score():
    s = story_engine.generate_adventure("space adventure", "Maha")
    n = story_engine.generate_next(s, s["choices"][0])
    assert n["chapter"] == 2
    assert n["score"] == 10
    assert n["history"][-1]["choice"] == s["choices"][0]


def test_adventure_finishes_after_max_chapters():
    s = story_engine.generate_adventure("ocean adventure", "Maha")
    for _ in range(s["max_chapters"] - 1):
        s = story_engine.generate_next(s, s["choices"][0] if s["choices"] else "Continue")
    assert s["finished"] is True
    assert s["choices"] == []


def test_same_idea_is_deterministic_offline():
    a = story_engine.generate_adventure("jungle adventure", "Maha")
    b = story_engine.generate_adventure("jungle adventure", "Maha")
    assert a["story"] == b["story"]
    assert a["mission"] == b["mission"]


def test_traits_start_at_zero_and_move_with_choices():
    s = story_engine.generate_adventure("space adventure", "Maha")
    assert s["traits"] == {"bravery": 0, "curiosity": 0, "kindness": 0}
    n = story_engine.generate_next(s, "Ask your companion for help")
    assert n["traits"]["kindness"] >= 2


def test_inventory_and_achievements_are_lists():
    s = story_engine.generate_adventure("desert adventure", "Maha")
    assert isinstance(s["inventory"], list)
    assert isinstance(s["achievements"], list)
    assert "first_light" in s["achievements"]


def test_full_playthrough_reaches_an_ending_with_flavor_text():
    s = story_engine.generate_adventure("robot adventure", "Maha")
    while not s["finished"]:
        s = story_engine.generate_next(s, s["choices"][0] if s["choices"] else "Continue")
    assert s["finished"] is True
    assert "mission_complete" in s["achievements"]
    assert len(s["story"]) > 0


def test_riddle_chapter_can_be_solved():
    s = story_engine.generate_adventure("cave adventure", "Maha")
    puzzle_chapter = story_engine._puzzle_chapter_number(s["max_chapters"])
    riddle = story_engine._pick_riddle(s["idea"])
    # Walk forward to (and including) the riddle chapter using an answer
    # that always matches one of the riddle keyword sets.
    while s["chapter"] < puzzle_chapter:
        s = story_engine.generate_next(s, s["choices"][0] if s["choices"] else "Continue")
    assert riddle["text"] in s["mission"]
    answer = f"I {riddle['keywords'][0]} the path"
    s = story_engine.generate_next(s, answer)
    assert s["puzzle_correct"] == 1
    assert "riddle_master" in s["achievements"]
