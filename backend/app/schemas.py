"""Pydantic schemas for request and response validation."""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Any] = None


class InvestigationCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    source_mode: str = Field(default="DEMO")  # DEMO | WAZUH

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Title must not be empty or whitespace.")
        return s

    @field_validator("source_mode")
    @classmethod
    def validate_source(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in ("DEMO", "WAZUH"):
            raise ValueError("source_mode must be 'DEMO' or 'WAZUH'.")
        return v_upper


class RunCreate(BaseModel):
    scenario_id: str = Field(..., min_length=1)


class DiagnosisReviewRequest(BaseModel):
    decision: str = Field(..., description="ACCEPT or REJECT")
    reviewer: str = Field(..., min_length=1, description="Required non-empty reviewer name")
    note: Optional[str] = Field(default="")

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        v_upper = v.upper().strip()
        if v_upper not in ("ACCEPT", "REJECT"):
            raise ValueError("Review decision must be 'ACCEPT' or 'REJECT'.")
        return v_upper

    @field_validator("reviewer")
    @classmethod
    def validate_reviewer(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Reviewer name cannot be empty.")
        return s


class RemediationApproveRequest(BaseModel):
    decision: str = Field(..., description="APPROVE or REJECT")
    reviewer: str = Field(..., min_length=1, description="Required non-empty reviewer name")
    note: Optional[str] = Field(default="")

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        v_upper = v.upper().strip()
        if v_upper not in ("APPROVE", "REJECT"):
            raise ValueError("Approval decision must be 'APPROVE' or 'REJECT'.")
        return v_upper

    @field_validator("reviewer")
    @classmethod
    def validate_reviewer(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Reviewer name cannot be empty.")
        return s


class WazuhTestResponse(BaseModel):
    connected: bool
    message: str
