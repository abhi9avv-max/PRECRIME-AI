"""Compact scenario and evidence builder helper."""
import hashlib
import json
from datetime import datetime, timezone

def make_hash(payload: dict) -> str:
    s = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def make_rec(rec_id: str, stage: str, ckpt: str, payload: dict, avail: str = "AVAILABLE", src: str = "SYNTHETIC") -> dict:
    return {
        "id": rec_id,
        "stage": stage,
        "checkpoint_id": ckpt,
        "source_label": src,
        "availability": avail,
        "payload": payload,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "content_hash": make_hash(payload),
    }

def make_case(
    case_id: str,
    family: str,
    variant: str,
    split: str,
    name: str,
    description: str,
    spec: dict,
    initial_records: list,
    postfix_records: list,
) -> dict:
    return {
        "id": case_id,
        "family": family,
        "variant": variant,
        "split": split,
        "name": name,
        "description": description,
        "expectation_spec": spec,
        "initial_evidence": initial_records,
        "postfix_evidence": postfix_records,
    }
