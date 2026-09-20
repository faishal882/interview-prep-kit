"""Appendix A Kit models — strict types."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Kind = Literal["technical", "behavioural", "domain"]
Priority = Literal["must", "nice"]
Category = Literal["technical", "behavioural", "system-design", "company-fit"]


class Source(BaseModel):
    company: str = ""
    company_url: str = ""
    role: str = ""
    location: str = ""
    jd_chars: int = 0
    researched_at: str = ""
    pages_used: list[str] = Field(default_factory=list)


class CompanyBrief(BaseModel):
    summary: str = ""
    what_they_do: str = ""
    sources: list[str] = Field(default_factory=list)
    hiring_process: str = ""  # additive extension (optional)


class Requirement(BaseModel):
    id: str
    text: str
    kind: Kind
    priority: Priority


class Role(BaseModel):
    title: str = ""
    seniority: str = "unspecified"
    responsibilities: list[str] = Field(default_factory=list)
    requirements: list[Requirement] = Field(default_factory=list)


class Question(BaseModel):
    id: str
    requirement_ids: list[str]
    category: Category
    prompt: str
    answer_outline: str
    difficulty: int
    outline_points: list[str] = Field(default_factory=list)  # additive extension

    @field_validator("difficulty")
    @classmethod
    def _difficulty_range(cls, v: object) -> object:
        if not isinstance(v, int) or isinstance(v, bool) or not (1 <= v <= 3):
            raise ValueError("difficulty must be int 1..3")
        return v


class Flashcard(BaseModel):
    id: str
    front: str
    back: str
    requirement_ids: list[str] = Field(default_factory=list)


class ScheduleDay(BaseModel):
    day: int
    focus: str = ""
    question_ids: list[str] = Field(default_factory=list)
    minutes: int

    @field_validator("minutes")
    @classmethod
    def _minutes_int(cls, v: object) -> object:
        if not isinstance(v, int) or isinstance(v, bool):
            raise ValueError("minutes must be an integer")
        return v


class Schedule(BaseModel):
    days_available: int
    days: list[ScheduleDay] = Field(default_factory=list)


class Coverage(BaseModel):
    uncovered_requirement_ids: list[str] = Field(default_factory=list)
    passes: int = 0


class Kit(BaseModel):
    source: Source
    company_brief: CompanyBrief
    role: Role
    questions: list[Question] = Field(default_factory=list)
    flashcards: list[Flashcard] = Field(default_factory=list)
    schedule: Schedule
    coverage: Coverage
    # Additive optional extensions (never break Appendix A shape)
    research_log: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
