from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


WorkMode = Literal["on_site", "hybrid", "remote"]
ContractType = Literal["cdi", "cdd", "internship", "freelance", "apprenticeship", "other"]


class SkillEntry(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    level: int = Field(..., ge=1, le=5)
    category: Literal["technical", "functional", "language", "tool", "other"] = "technical"


class CandidateLocation(BaseModel):
    city: str = Field(..., min_length=1, max_length=120)
    country: str = Field(default="France", min_length=1, max_length=120)
    remote_preference: WorkMode = "hybrid"
    mobility_km: int = Field(default=0, ge=0, le=10000)


class CandidateEducation(BaseModel):
    degree: Optional[str] = Field(default=None, max_length=120)
    field_of_study: Optional[str] = Field(default=None, max_length=120)
    certifications: List[str] = Field(default_factory=list)


class CandidatePreferences(BaseModel):
    target_roles: List[str] = Field(default_factory=list)
    target_sectors: List[str] = Field(default_factory=list)
    contract_types: List[ContractType] = Field(default_factory=list)
    salary_min: Optional[int] = Field(default=None, ge=0)
    values: List[str] = Field(default_factory=list)


class CandidateMotivation(BaseModel):
    free_text: str = Field(..., min_length=10, max_length=4000)
    drivers: List[str] = Field(default_factory=list)
    mission_preferences: List[str] = Field(default_factory=list)


class CandidatePotential(BaseModel):
    learning_goals: List[str] = Field(default_factory=list)
    transferable_experiences: str = Field(default="", max_length=3000)
    growth_domains: List[str] = Field(default_factory=list)


class CandidateAvailability(BaseModel):
    start_date: Optional[str] = Field(default=None, max_length=20)
    schedule: Literal["full_time", "part_time", "either"] = "full_time"
    constraints: str = Field(default="", max_length=1000)


class CandidateProfileCreate(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120)
    email: Optional[str] = Field(default=None, max_length=200)
    current_title: Optional[str] = Field(default=None, max_length=120)
    years_experience: int = Field(default=0, ge=0, le=60)
    location: CandidateLocation
    skills: List[SkillEntry] = Field(default_factory=list)
    education: CandidateEducation = Field(default_factory=CandidateEducation)
    preferences: CandidatePreferences = Field(default_factory=CandidatePreferences)
    motivation: CandidateMotivation
    potential: CandidatePotential = Field(default_factory=CandidatePotential)
    availability: CandidateAvailability = Field(default_factory=CandidateAvailability)


class CandidateProfile(CandidateProfileCreate):
    id: str
    created_at: str


class JobLocation(BaseModel):
    city: str = Field(..., min_length=1, max_length=120)
    country: str = Field(default="France", min_length=1, max_length=120)
    work_mode: WorkMode = "hybrid"


class JobRequirement(BaseModel):
    minimum_degree: Optional[str] = Field(default=None, max_length=120)
    minimum_years_experience: int = Field(default=0, ge=0, le=60)
    mandatory_skills: List[str] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)


class JobEnvironment(BaseModel):
    team_style: str = Field(default="", max_length=500)
    pace: str = Field(default="", max_length=200)
    culture_keywords: List[str] = Field(default_factory=list)


class JobConditions(BaseModel):
    salary_min: Optional[int] = Field(default=None, ge=0)
    salary_max: Optional[int] = Field(default=None, ge=0)
    contract_type: ContractType = "cdi"
    start_date: Optional[str] = Field(default=None, max_length=20)
    capacity: int = Field(default=1, ge=1, le=1000)


class JobTargetProfile(BaseModel):
    expected_traits: List[str] = Field(default_factory=list)
    growth_potential: str = Field(default="", max_length=1000)
    learning_expectations: List[str] = Field(default_factory=list)


class JobProfileCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=150)
    team: Optional[str] = Field(default=None, max_length=120)
    location: JobLocation
    requirements: JobRequirement = Field(default_factory=JobRequirement)
    desired_skills: List[SkillEntry] = Field(default_factory=list)
    missions: str = Field(..., min_length=10, max_length=5000)
    environment: JobEnvironment = Field(default_factory=JobEnvironment)
    conditions: JobConditions = Field(default_factory=JobConditions)
    target_profile: JobTargetProfile = Field(default_factory=JobTargetProfile)


class JobProfile(JobProfileCreate):
    id: str
    created_at: str


ScoreSource = Literal["structured", "embedding", "lexical_fallback", "hybrid"]


class CompatibilityRequest(BaseModel):
    candidate_ids: List[str] = Field(default_factory=list)
    job_ids: List[str] = Field(default_factory=list)
    top_k_per_candidate: int = Field(default=5, ge=1, le=50)


class CriterionScore(BaseModel):
    key: str
    label: str
    score: int = Field(..., ge=0, le=100)
    weight: float = Field(..., ge=0)
    weighted_score: float = Field(..., ge=0)
    source: ScoreSource
    explanation: str


class CompatibilityPenalty(BaseModel):
    label: str
    factor: float = Field(..., ge=0, le=1)


class PairCompatibility(BaseModel):
    candidate_id: str
    candidate_name: str
    job_id: str
    job_title: str
    overall_score: int = Field(..., ge=0, le=100)
    base_score: float = Field(..., ge=0, le=100)
    criteria: List[CriterionScore]
    penalties: List[CompatibilityPenalty] = Field(default_factory=list)
    summary: str


class CompatibilityResponse(BaseModel):
    generated_at: str
    embedding_mode: Literal["remote", "fallback"]
    embedding_model: str
    results: List[PairCompatibility]
