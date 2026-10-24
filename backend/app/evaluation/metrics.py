"""Metrics computation strictly from persisted evaluation_results records.

Zero hardcoded numbers. All values computed dynamically from database rows.
"""
from typing import Dict, Any, List, Optional
import statistics
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models import EvaluationResult
from app.evaluation.ground_truth import GROUND_TRUTH_CASES


def compute_ratio(num: int, den: int) -> Optional[float]:
    if den == 0:
        return None
    return round((num / den) * 100.0, 1)


def slice_metrics(records: List[EvaluationResult], evaluated_at: str) -> Dict[str, Any]:
    """Compute all required metrics over a set of EvaluationResult records."""
    total_cases = len(records)
    if total_cases == 0:
        return {}

    # 1. Failure localization accuracy: correct failure_stage / evaluable failed cases
    # An evaluable failed case is one where ground truth has an expected failure stage
    evaluable_failed = [r for r in records if r.is_evaluable and GROUND_TRUTH_CASES[r.case_id]["expected_failure_stage"] is not None]
    loc_num = sum(1 for r in evaluable_failed if r.correct_localization)
    loc_den = len(evaluable_failed)

    # 2. False attribution rate: incorrect root-cause claims / all FAILURE_LOCALIZED claims
    all_claims = [r for r in records if r.outcome == "FAILURE_LOCALIZED"]
    false_claims = sum(1 for r in all_claims if r.false_attribution)
    false_den = len(all_claims)

    # 3. Abstention quality:
    # (a) UNDETERMINED on insufficient-evidence cases / insufficient-evidence cases
    insufficient_cases = [r for r in records if r.is_insufficient]
    ins_num = sum(1 for r in insufficient_cases if r.outcome == "UNDETERMINED")
    ins_den = len(insufficient_cases)

    # (b) Unnecessary abstentions = UNDETERMINED on diagnosable cases / diagnosable cases
    diagnosable_cases = [r for r in records if r.is_evaluable]
    unnec_num = sum(1 for r in diagnosable_cases if r.outcome == "UNDETERMINED")
    unnec_den = len(diagnosable_cases)

    # 4. Latency
    latencies = [r.latency_ms for r in records]
    mean_lat = round(statistics.mean(latencies), 1) if latencies else None
    median_lat = round(statistics.median(latencies), 1) if latencies else None
    max_lat = max(latencies) if latencies else None

    # 5. Retest verification accuracy: retest class equal to retest truth / cases with retest
    retested_cases = [r for r in records if r.retest_result and r.retest_result != "N/A"]
    retest_correct = sum(
        1 for r in retested_cases
        if r.retest_result == GROUND_TRUTH_CASES[r.case_id]["expected_retest_class"]
    )
    retest_den = len(retested_cases)

    # 6. Evidence coverage: checkpoints_available / checkpoints_required
    total_avail = sum(r.checkpoints_available for r in records)
    total_req = sum(r.checkpoints_required for r in records)

    return {
        "case_count": total_cases,
        "failure_localization_accuracy": {
            "numerator": loc_num,
            "denominator": loc_den,
            "value": compute_ratio(loc_num, loc_den),
            "display": f"{loc_num}/{loc_den} ({compute_ratio(loc_num, loc_den)}%)" if loc_den > 0 else "N/A",
            "definition": "Correct failure_stage identified across evaluable failure cases.",
        },
        "false_attribution_rate": {
            "numerator": false_claims,
            "denominator": false_den,
            "value": compute_ratio(false_claims, false_den),
            "display": f"{false_claims}/{false_den} ({compute_ratio(false_claims, false_den)}%)" if false_den > 0 else "N/A",
            "definition": "Incorrect root-cause claims across all localized failure claims.",
        },
        "abstention_quality": {
            "supported_abstention": {
                "numerator": ins_num,
                "denominator": ins_den,
                "value": compute_ratio(ins_num, ins_den),
                "display": f"{ins_num}/{ins_den} ({compute_ratio(ins_num, ins_den)}%)" if ins_den > 0 else "N/A",
                "definition": "UNDETERMINED outcome on cases with incomplete/conflicting telemetry.",
            },
            "unnecessary_abstention": {
                "numerator": unnec_num,
                "denominator": unnec_den,
                "value": compute_ratio(unnec_num, unnec_den),
                "display": f"{unnec_num}/{unnec_den} ({compute_ratio(unnec_num, unnec_den)}%)" if unnec_den > 0 else "N/A",
                "definition": "UNDETERMINED outcome on fully diagnosable cases.",
            },
        },
        "diagnosis_latency": {
            "mean_ms": mean_lat,
            "median_ms": median_lat,
            "max_ms": max_lat,
            "manual_baseline": "not recorded",
            "definition": "Execution time from run invocation to persisted diagnosis.",
        },
        "retest_verification_accuracy": {
            "numerator": retest_correct,
            "denominator": retest_den,
            "value": compute_ratio(retest_correct, retest_den),
            "display": f"{retest_correct}/{retest_den} ({compute_ratio(retest_correct, retest_den)}%)" if retest_den > 0 else "N/A",
            "definition": "Retest outcome classification matching ground truth recovery class.",
        },
        "evidence_coverage": {
            "numerator": total_avail,
            "denominator": total_req,
            "value": compute_ratio(total_avail, total_req),
            "display": f"{total_avail}/{total_req} ({compute_ratio(total_avail, total_req)}%)" if total_req > 0 else "N/A",
            "definition": "Required pipeline checkpoints confirmed present in evaluation evidence.",
        },
    }


def get_latest_metrics(db: Session) -> Dict[str, Any]:
    """Retrieve and compute metrics from the most recent evaluation batch."""
    latest_rec = db.query(EvaluationResult).order_by(desc(EvaluationResult.evaluated_at)).first()
    if not latest_rec:
        return {
            "has_data": False,
            "message": "No evaluation has been run yet. Run the validation suite to compute metrics.",
            "metrics": None,
        }

    latest_batch_id = latest_rec.batch_id
    batch_records = db.query(EvaluationResult).filter(EvaluationResult.batch_id == latest_batch_id).all()
    evaluated_at = latest_rec.evaluated_at

    dev_records = [r for r in batch_records if r.split == "development"]
    held_records = [r for r in batch_records if r.split == "held-out"]

    combined_metrics = slice_metrics(batch_records, evaluated_at)
    dev_metrics = slice_metrics(dev_records, evaluated_at)
    held_metrics = slice_metrics(held_records, evaluated_at)

    return {
        "has_data": True,
        "batch_id": latest_batch_id,
        "evaluated_at": evaluated_at,
        "disclaimer": f"Evaluated on {len(batch_records)} synthetic cases on {evaluated_at[:10]}. Not a measure of production accuracy.",
        "combined": combined_metrics,
        "development": dev_metrics,
        "held_out": held_metrics,
    }
