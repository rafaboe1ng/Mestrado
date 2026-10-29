"""Persistent expert-validation store (KEFC side).

Mirrors the group's store: a closed vocabulary of reason codes, get-or-create requests keyed by
(feature_id, operation, reason_code), a JSON file that persists across runs by design (so an expert
resolution recorded once unblocks the same step on a later run), and an explicit list of codes whose
resolution may be reused without new data.

Two codes are new in this repository:

- ``anomalous_operational_state``: sensor-derived evidence shows an anomalous state during the
  deposition of this feature. The planned parameters are still rule-derived and trustworthy, so an
  expert may approve the step as planned without new data (same reasoning as
  ``critical_simulation_finding`` in the group's store).
- ``parameter_adjustment_suggested``: a rule conditioned on evidence recommends a different parameter
  set. Approving it means adopting new values, so it is NOT approvable without new data: the expert
  either rejects it or records ``knowledge_update_suggested`` and the rule base is extended, after which
  the next run derives the value from a rule with its own identifier.
"""
from __future__ import annotations

import datetime as dt
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

STATUSES = (
    "requires_review",
    "auto_approved",
    "expert_approved",
    "expert_rejected",
    "knowledge_update_suggested",
)

REASON_CODES = (
    "missing_knowledge",
    "low_confidence_mapping",
    "rule_conflict",
    "unsafe_value",
    "unresolved_mapping",
    "machine_incompatible",
    "orientation_incompatible",
    "serialisation_unsupported",
    "critical_simulation_finding",
    "serialisation_input_missing",
    "anomalous_operational_state",
    "parameter_adjustment_suggested",
)

APPROVABLE_WITHOUT_NEW_DATA = frozenset({
    "unsafe_value",
    "low_confidence_mapping",
    "critical_simulation_finding",
    "anomalous_operational_state",
})

DECISIONS = ("expert_approved", "expert_rejected", "knowledge_update_suggested")


@dataclass
class ExpertValidationRequest:
    request_id: str
    feature_id: int
    feature_type: str
    operation: Optional[str]
    reason_code: str
    detail: str
    status: str = "requires_review"
    created_at: str = ""
    resolved_at: Optional[str] = None
    resolution_note: Optional[str] = None


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


class ExpertValidationStore:
    """JSON-backed store. ``output_path`` is reloaded on construction if it exists."""

    def __init__(self, output_path: str | Path):
        self.output_path = Path(output_path)
        self._requests: list[ExpertValidationRequest] = []
        self._counter = 0
        self._load()

    # persistence ---------------------------------------------------------
    def _load(self) -> None:
        if not self.output_path.exists():
            return
        data = json.loads(self.output_path.read_text(encoding="utf-8"))
        for row in data.get("requests", []):
            known = {k: row.get(k) for k in ExpertValidationRequest.__dataclass_fields__}
            self._requests.append(ExpertValidationRequest(**known))
        for r in self._requests:
            try:
                self._counter = max(self._counter, int(r.request_id.split("_")[-1]))
            except ValueError:
                continue

    def save(self) -> Path:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"summary": self.summary(), "requests": [asdict(r) for r in self._requests]}
        self.output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return self.output_path

    # requests ------------------------------------------------------------
    def _find_existing(self, feature_id: int, operation: Optional[str], reason_code: str) -> Optional[ExpertValidationRequest]:
        for r in self._requests:
            if r.feature_id == feature_id and r.operation == operation and r.reason_code == reason_code:
                return r
        return None

    def create_request(self, feature_id: int, feature_type: str, reason_code: str, detail: str,
                       operation: Optional[str] = None) -> ExpertValidationRequest:
        if reason_code not in REASON_CODES:
            raise ValueError(f"unknown reason code {reason_code!r}; known: {REASON_CODES}")
        existing = self._find_existing(feature_id, operation, reason_code)
        if existing is not None:
            return existing
        self._counter += 1
        req = ExpertValidationRequest(
            request_id=f"evr_{self._counter:04d}", feature_id=feature_id, feature_type=feature_type,
            operation=operation, reason_code=reason_code, detail=detail, created_at=_now(),
        )
        self._requests.append(req)
        return req

    def find_resolution(self, feature_id: int, operation: Optional[str], reason_code: str) -> Optional[ExpertValidationRequest]:
        return self._find_existing(feature_id, operation, reason_code)

    def apply_feedback(self, request_id: str, decision: str, note: Optional[str] = None) -> ExpertValidationRequest:
        if decision not in DECISIONS:
            raise ValueError(f"decision must be one of {DECISIONS}, got {decision!r}")
        for r in self._requests:
            if r.request_id == request_id:
                r.status = decision
                r.resolved_at = _now()
                r.resolution_note = note
                return r
        raise KeyError(f"no request {request_id!r}")

    def all_requests(self) -> list[ExpertValidationRequest]:
        return list(self._requests)

    def summary(self) -> dict:
        by_status = {s: 0 for s in STATUSES}
        by_code: dict[str, int] = {}
        for r in self._requests:
            by_status[r.status] = by_status.get(r.status, 0) + 1
            by_code[r.reason_code] = by_code.get(r.reason_code, 0) + 1
        return {"total_requests": len(self._requests), "by_status": by_status, "by_code": by_code}
