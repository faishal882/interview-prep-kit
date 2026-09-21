"""Typed item schemas: unknown fields rejected, values validated.

Ids are always assigned by the server; requests carrying `id` or `_meta`
have them ignored (create) or rejected (patch). Patches always carry the
item revision; a missing revision is INVALID_INPUT, a stale one CONFLICT.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["technical", "behavioural", "system-design", "company-fit"]
Kind = Literal["technical", "behavioural", "domain"]
Priority = Literal["must", "nice"]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class QuestionCreate(Strict):
    prompt: str = Field(min_length=1, max_length=2000)
    answer_outline: str = Field(min_length=1, max_length=4000)
    category: Category = "technical"
    difficulty: int = Field(default=2, ge=1, le=3)
    requirement_ids: list[str] = Field(default_factory=list)
    outline_points: list[str] = Field(default_factory=list)


class QuestionPatch(Strict):
    rev: int
    prompt: str | None = Field(default=None, min_length=1, max_length=2000)
    answer_outline: str | None = Field(default=None, min_length=1, max_length=4000)
    category: Category | None = None
    difficulty: int | None = Field(default=None, ge=1, le=3)
    requirement_ids: list[str] | None = None
    outline_points: list[str] | None = None
    pinned: bool | None = None
    category_moved: bool | None = None


class FlashcardCreate(Strict):
    front: str = Field(min_length=1, max_length=1000)
    back: str = Field(min_length=1, max_length=2000)
    requirement_ids: list[str] = Field(default_factory=list)


class FlashcardPatch(Strict):
    rev: int
    front: str | None = Field(default=None, min_length=1, max_length=1000)
    back: str | None = Field(default=None, min_length=1, max_length=2000)
    requirement_ids: list[str] | None = None
    pinned: bool | None = None


class RequirementCreate(Strict):
    text: str = Field(min_length=1, max_length=2000)
    kind: Kind = "technical"
    priority: Priority = "must"


class RequirementPatch(Strict):
    rev: int
    text: str | None = Field(default=None, min_length=1, max_length=2000)
    kind: Kind | None = None
    priority: Priority | None = None
    pinned: bool | None = None


class BriefPatch(Strict):
    rev: int
    summary: str | None = Field(default=None, max_length=8000)
    what_they_do: str | None = Field(default=None, max_length=8000)
    hiring_process: str | None = Field(default=None, max_length=8000)
    pinned: bool | None = None


class ScheduleDayPatch(Strict):
    focus: str | None = Field(default=None, max_length=500)
    question_ids: list[str] | None = None


class ScheduleMove(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str = Field(min_length=1)
    to_day: int = Field(ge=1, le=60)


class ReorderBodyStrict(Strict):
    id: str = Field(min_length=1)
    category: Category | None = None
    after_id: str | None = None
