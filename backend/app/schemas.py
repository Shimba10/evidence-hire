from typing import Any
from pydantic import BaseModel, Field

class Requirement(BaseModel):
    skill: str
    importance: str
    evidence_to_verify: list[str]

class Claim(BaseModel):
    skill: str
    claim: str
    evidence_in_resume: str
    confidence: float = Field(ge=0, le=1)

class Analysis(BaseModel):
    candidate_name: str
    role_title: str
    requirements: list[Requirement]
    claims: list[Claim]
    evidence_gaps: list[str]
    interview_plan: list[str]
    summary: str

class InterviewStart(BaseModel):
    assessment_id: int

class AnswerRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=10000)

class Question(BaseModel):
    skill: str
    question: str
    why: str

class Evaluation(BaseModel):
    score: float = Field(ge=0, le=10)
    confidence: float = Field(ge=0, le=1)
    evidence: str
    concern: str
    follow_up_needed: bool

class InterviewTurn(BaseModel):
    question: str
    skill: str
    evaluation: Evaluation
    next_question: Question | None = None
    completed: bool

class ReportSkill(BaseModel):
    skill: str
    score: float
    confidence: float
    claim: str
    demonstrated_evidence: str
    uncertainty: str

class FinalReport(BaseModel):
    overall_score: float
    evidence_confidence: float
    recommendation: str
    strengths: list[str]
    risks: list[str]
    skills: list[ReportSkill]
    hiring_summary: str
