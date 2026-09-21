"""Validator tests: duplicate ids, dangling refs, schedule length, minutes, difficulty."""
from app.validation.kit_validator import validate_kit


def base_kit():
    return {
        "role": {"requirements": [{"id": "r1", "priority": "must"}, {"id": "r2", "priority": "nice"}]},
        "questions": [{"id": "q1", "requirement_ids": ["r1"], "category": "technical", "difficulty": 2}],
        "flashcards": [{"id": "f1"}],
        "schedule": {"days_available": 1, "days": [{"day": 1, "question_ids": ["q1"], "minutes": 15}]},
        "coverage": {"uncovered_requirement_ids": ["r2"], "passes": 1},
    }


def test_valid():
    assert validate_kit(base_kit()) == []


def test_duplicate_ids():
    k = base_kit()
    k["questions"].append({"id": "q1", "requirement_ids": ["r1"], "difficulty": 1})
    assert any("duplicate" in e for e in validate_kit(k))


def test_dangling_reference():
    k = base_kit()
    k["questions"][0]["requirement_ids"] = ["rX"]
    assert any("dangling" in e for e in validate_kit(k))


def test_schedule_length():
    k = base_kit()
    k["schedule"]["days_available"] = 3
    assert any("schedule length" in e for e in validate_kit(k))


def test_non_integer_minutes():
    k = base_kit()
    k["schedule"]["days"][0]["minutes"] = 12.5
    assert any("minutes" in e for e in validate_kit(k))


def test_bad_difficulty():
    k = base_kit()
    k["questions"][0]["difficulty"] = 5
    assert any("difficulty" in e for e in validate_kit(k))
