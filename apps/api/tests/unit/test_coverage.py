"""Coverage checker tests incl. empty inputs."""
from app.coverage.checker import compute_gaps


def test_no_gaps():
    assert compute_gaps(["r1"], [{"requirement_ids": ["r1"]}]) == []


def test_gap_found():
    assert compute_gaps(["r1", "r2"], [{"requirement_ids": ["r1"]}]) == ["r2"]


def test_empty_requirements():
    assert compute_gaps([], [{"requirement_ids": ["r1"]}]) == []


def test_empty_questions_all_gaps():
    assert compute_gaps(["r1", "r2"], []) == ["r1", "r2"]


def test_verified_links_override():
    qs = [{"requirement_ids": ["r1"]}]
    assert compute_gaps(["r1"], qs, verified_links={"q1": []}) == ["r1"]
