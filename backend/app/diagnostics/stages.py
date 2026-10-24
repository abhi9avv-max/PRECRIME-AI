"""Stages, statuses, and domain definitions for diagnostic analysis."""
from enum import Enum
from typing import List

class PipelineStage(str, Enum):
    EVENT_GENERATION = "event_generation"
    COLLECTION = "collection"
    PARSING = "parsing"
    RULE_EVALUATION = "rule_evaluation"
    ALERT_GENERATION = "alert_generation"
    DELIVERY_VISIBILITY = "delivery_visibility"

STAGE_ORDER: List[PipelineStage] = [
    PipelineStage.EVENT_GENERATION,
    PipelineStage.COLLECTION,
    PipelineStage.PARSING,
    PipelineStage.RULE_EVALUATION,
    PipelineStage.ALERT_GENERATION,
    PipelineStage.DELIVERY_VISIBILITY,
]

STAGE_CHECKPOINTS = {
    PipelineStage.EVENT_GENERATION: "EG-1",
    PipelineStage.COLLECTION: "COL-1",
    PipelineStage.PARSING: "PAR-1",
    PipelineStage.RULE_EVALUATION: "RUL-1",
    PipelineStage.ALERT_GENERATION: "ALT-1",
    PipelineStage.DELIVERY_VISIBILITY: "DEL-1",
}

class StageStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_REACHED = "NOT REACHED"

class DiagnosticOutcome(str, Enum):
    FAILURE_LOCALIZED = "FAILURE_LOCALIZED"
    HEALTHY = "HEALTHY"
    UNDETERMINED = "UNDETERMINED"

class ConfidenceLabel(str, Enum):
    SUPPORTED_BY_EVIDENCE = "SUPPORTED_BY_EVIDENCE"
    NO_FAILURE_FOUND = "NO_FAILURE_FOUND"
    UNDETERMINED = "UNDETERMINED"

class SourceLabel(str, Enum):
    SYNTHETIC = "SYNTHETIC"
    WAZUH = "WAZUH"

class Availability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
