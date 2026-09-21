"""Typed API responses: every endpoint declares one of these models.

Document-shaped models allow extra fields so additive extensions never break
validation, but all core properties are declared — the committed OpenAPI
document describes real shapes and the frontend generates types from it.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.api.schemas.items import Category as CategoryLit
from app.api.schemas.items import Kind as KindLit
from app.api.schemas.items import Priority as PriorityLit

KitStatus = Literal["generating", "ready", "failed"]
JobStatus = Literal["pending", "running", "done", "failed"]
StepStatus = Literal["pending", "running", "done", "skipped", "failed"]


class AllowExtra(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class UserOut(BaseModel):
    id: str
    email: str


class OkOut(BaseModel):
    ok: bool = True


class HealthOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    ok: bool = True
    problems: list[str] | None = None


class KitCreateOut(BaseModel):
    kit_id: str
    job_id: str | None = None
    duplicate: bool = False


class SourceOut(AllowExtra):
    company: str = ""
    company_url: str = ""
    role: str = ""
    location: str = ""
    jd_chars: int = 0
    researched_at: str = ""
    pages_used: list[str] = Field(default_factory=list)


class KitSummaryOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    status: KitStatus
    company: str
    role: str
    days: int
    requirement_count: int
    question_count: int
    updated_at: float | None = None
    job_id: str | None = None


class KitListOut(BaseModel):
    kits: list[KitSummaryOut]


class BriefOut(AllowExtra):
    summary: str
    what_they_do: str
    hiring_process: str
    sources: list[str]


class ItemMeta(BaseModel):
    origin: str = "generated"
    edited: bool = False
    pinned: bool = False
    rev: int = 1
    order: str = ""
    gen_run: str | None = None


class BriefMeta(BaseModel):
    origin: str = "generated"
    edited: bool = False
    pinned: bool = False
    rev: int = 0


class ProposalOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    summary: str = ""
    status: str = ""


class KitInputOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    jd: str = ""
    company_url: str = ""
    days: int = 5


class RequirementOut(AllowExtra):
    id: str
    text: str
    kind: KindLit
    priority: PriorityLit
    meta: ItemMeta | None = Field(default=None, alias="_meta", serialization_alias="_meta", validation_alias="_meta")


class RoleOut(AllowExtra):
    title: str
    seniority: str
    responsibilities: list[str]
    requirements: list[RequirementOut]


class QuestionOut(AllowExtra):
    id: str
    requirement_ids: list[str]
    category: CategoryLit
    prompt: str
    answer_outline: str
    difficulty: int
    outline_points: list[str]
    meta: ItemMeta | None = Field(default=None, alias="_meta", serialization_alias="_meta", validation_alias="_meta")


class FlashcardOut(AllowExtra):
    id: str
    front: str
    back: str
    requirement_ids: list[str]
    meta: ItemMeta | None = Field(default=None, alias="_meta", serialization_alias="_meta", validation_alias="_meta")


class ScheduleDayOut(AllowExtra):
    day: int
    focus: str
    question_ids: list[str]
    minutes: int


class ScheduleOut(AllowExtra):
    days_available: int
    days: list[ScheduleDayOut]


class CoverageOut(AllowExtra):
    uncovered_requirement_ids: list[str]
    passes: int


class KitContentOut(AllowExtra):
    source: SourceOut = Field(default_factory=SourceOut)
    research_log: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    company_brief: BriefOut = Field(default_factory=BriefOut)
    role: RoleOut = Field(default_factory=RoleOut)
    questions: list[QuestionOut] = Field(default_factory=list)
    flashcards: list[FlashcardOut] = Field(default_factory=list)
    schedule: ScheduleOut = Field(default_factory=ScheduleOut)
    coverage: CoverageOut = Field(default_factory=CoverageOut)
    brief_meta: BriefMeta | None = Field(default=None, alias="_brief_meta", serialization_alias="_brief_meta", validation_alias="_brief_meta")


class ErrorInfo(BaseModel):
    model_config = ConfigDict(extra="allow")
    code: str = ""
    message: str = ""


class KitDocOut(AllowExtra):
    id: str
    status: KitStatus
    input: KitInputOut | None = None
    kit: KitContentOut | None = None
    error: ErrorInfo | None = None
    schedule_stale: bool = False
    proposals: dict[str, ProposalOut] = Field(default_factory=dict)
    created_at: float | None = None


class ExportOut(KitContentOut):
    pass


class JobStepOut(AllowExtra):
    name: str
    status: StepStatus
    message: str
    started_at: str | None = None
    finished_at: str | None = None


class JobOut(AllowExtra):
    id: str
    kit_id: str
    kind: str
    status: JobStatus
    steps: list[JobStepOut]
    created_at: float | None = None
    deadline: float | None = None
    error: ErrorInfo | None = None
    retryable: bool


class AcceptedEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    id: str
    kit_id: str
    job_id: str | None = None
    duplicate: bool = False


class RejectedEntry(BaseModel):
    id: str
    reason: str


class BatchOut(BaseModel):
    accepted: list[AcceptedEntry]
    rejected: list[RejectedEntry]


class DeleteItemOut(BaseModel):
    ok: bool = True
    flagged: list[str] = Field(default_factory=list)


class QueueOut(BaseModel):
    queue: list[str]


class PracticeSummaryOut(BaseModel):
    total: int
    covered: int
    uncovered: int


class WeakSpotEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    requirement_id: str
    reasons: list[str]
    score: int
    question_ids: list[str]
    flashcard_ids: list[str]


class WeakSpotsOut(BaseModel):
    spots: list[WeakSpotEntry]


class CheckPoint(BaseModel):
    point: str
    covered: bool


class CheckOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    results: list[CheckPoint]
    method: str
    limits: str


class RegenOut(BaseModel):
    model_config = ConfigDict(extra="allow")
    job_id: str | None = None
    ok: bool | None = None
    proposal: dict | None = None
    warning: str | None = None


class MoveOut(BaseModel):
    ok: bool = True
    day: int = 0


ItemOut = QuestionOut | FlashcardOut | RequirementOut | BriefOut
