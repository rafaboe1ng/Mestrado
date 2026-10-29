"""CFRM: Contextual Feature-Rule Mapper.

Maps KINM feature records to ontology individuals (class from ``FEATURE_TYPE_TO_CLASS``), asserts the
numeric qualifier classes the rule format cannot express (``QUALIFIERS``, each with its own identifier
recorded as provenance), asserts the job's operation-log entries as operation instances and the SPCM
states as operational states, and marks a feature with ``FeatureWithAnomalousDeposition`` when an
anomalous state was observed during its deposition. Confidence follows the group's rule:
``combined = min(mapping_confidence, match_confidence)``, low confidence below 0.5.

Without sensor evidence (``evidence=None`` or empty) the CFRM asserts exactly what the group's CFRM
would: classes, material and machine. The evidence class is the only addition and it is opt-in.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from contracts.base import comparar
from framework.kinm import FeatureRecord, OperationLogEntry
from framework.skl.repository import SKLRepository
from framework.spcm import OperationalStateRecord

LOW_CONFIDENCE_THRESHOLD = 0.5
FEATURE_TYPE_TO_CLASS = {"Base": "Base", "Wall": "Wall", "Hole": "Hole", "Rib": "Rib", "Overhang": "Overhang"}

# (qualifier id, feature class, dimension, operator, value, class if true, class if false). Mirrors the
# conditions of the process rules R1..R5 of the Portuguese base (R1 and R2 share Q1).
QUALIFIERS = (
    ("Q1", "Wall", "thickness_mm", "<", 1.2, "ThinWall", "StandardWall"),
    ("Q2", "Overhang", "angle_deg", ">", 50.0, "SteepOverhang", "StandardOverhang"),
    ("Q3", "Hole", "diameter_mm", "<", 3.0, "SmallHole", "StandardHole"),
    ("Q4", "Rib", "thickness_mm", "<", 1.0, "ThinRib", "StandardRib"),
)
STATE_KIND_TO_CLASS = {"anomaly": "Anomaly", "stable_pattern": "StablePattern", "transition": "Transition"}


@dataclass
class ReconciledFeature:
    feature_id: int
    local_id: str
    type: str
    owl_class: str | None
    leaf_class: str | None
    qualifier_rule_id: str | None
    individual: str | None
    dimensions: dict[str, float]
    mapping_confidence: float
    match_confidence: float
    combined_confidence: float
    low_confidence: bool
    unmapped: bool
    evidence_state_ids: list[str] = field(default_factory=list)
    mapping_note: str = ""


def classify(record: FeatureRecord) -> tuple[str | None, str | None, str | None, float, str]:
    """(owl_class, leaf_class, qualifier_id, mapping_confidence, note)."""
    cls = FEATURE_TYPE_TO_CLASS.get(record.type)
    if cls is None:
        return None, None, None, 0.0, f"type {record.type!r} has no class in the SKL"
    for qid, qcls, dim, op, val, if_true, if_false in QUALIFIERS:
        if qcls != cls:
            continue
        if dim not in record.dimensions:
            return cls, None, None, 0.6, f"{dim} missing: qualifier {qid} cannot be evaluated, no leaf class asserted"
        leaf = if_true if comparar(float(record.dimensions[dim]), op, val) else if_false
        return cls, leaf, qid, 1.0, f"{qid}: {dim} {op} {val} -> {leaf}"
    return cls, None, None, 1.0, "no qualifier for this class"


def map_features(records: list[FeatureRecord], repo: SKLRepository, material: str, machine_key: str,
                 evidence: dict[str, list[str]] | None = None) -> list[ReconciledFeature]:
    evidence = evidence or {}
    out: list[ReconciledFeature] = []
    for r in records:
        cls, leaf, qid, mconf, note = classify(r)
        combined = min(mconf, float(r.match_confidence))
        if cls is None:
            out.append(ReconciledFeature(r.id, r.local_id, r.type, None, None, None, None, dict(r.dimensions), mconf,
                                         r.match_confidence, combined, True, True, [], note))
            continue
        name = repo.assert_feature(r.id, cls, leaf, material, machine_key, qid)
        states = list(evidence.get(r.local_id, []))
        out.append(ReconciledFeature(r.id, r.local_id, r.type, cls, leaf, qid, name, dict(r.dimensions), mconf,
                                     r.match_confidence, combined, combined < LOW_CONFIDENCE_THRESHOLD, False, states, note))
    return out


def map_operation_log(entries: list[OperationLogEntry], features: list[ReconciledFeature], repo: SKLRepository,
                      job_name: str) -> dict[str, str]:
    """Asserts one OperationInstance per log entry; returns entry_id -> individual name."""
    by_local = {f.local_id: f.individual for f in features if f.individual}
    names: dict[str, str] = {}
    for k, e in enumerate(entries, start=1):
        name = f"opinst_{k}"
        repo.assert_operation_instance(name, by_local.get(e.feature_local_id), job_name, e.start_s, e.end_s, k)
        names[e.entry_id] = name
    return names


def map_states(states: list[OperationalStateRecord], entry_names: dict[str, str], repo: SKLRepository,
               machine_key: str, job_name: str) -> dict[str, str]:
    """Asserts the SPCM states as individuals with provenance; returns state_id -> individual name."""
    names: dict[str, str] = {}
    for s in states:
        during = [entry_names[o["entry_id"]] for o in s.overlaps if o["entry_id"] in entry_names]
        names[s.state_id] = repo.assert_state(s.state_id, STATE_KIND_TO_CLASS[s.kind], s.label, s.start_s, s.end_s,
                                              s.anomaly_flag, s.anomaly_score, s.window_count, s.method_id, s.method_config,
                                              s.derived_from_series, machine_key, job_name, during)
    for s in states:
        if s.transitions_to and s.transitions_to in names:
            repo.assert_transition(names[s.state_id], names[s.transitions_to])
    return names


def assert_evidence(features: list[ReconciledFeature], state_names: dict[str, str], repo: SKLRepository) -> int:
    """Marks features whose deposition overlapped an anomalous state. Returns how many were marked."""
    n = 0
    for f in features:
        if f.individual and f.evidence_state_ids:
            repo.assert_evidence(f.individual, [state_names[s] for s in f.evidence_state_ids if s in state_names])
            n += 1
    return n


def to_dicts(features: list[ReconciledFeature]) -> list[dict]:
    return [asdict(f) for f in features]
