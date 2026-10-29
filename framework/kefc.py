"""KEFC: Knowledge Extension and Feedback Controller.

Sole owner of validation. Builds one step per (feature, inferred operation), runs a fixed sequence of
gates that accumulate (reason_code, detail) exceptions, and only then decides ``validation_status``
through the expert-validation store: no exceptions means ``auto_approved``; an exception counts as
resolved only when an ``expert_approved`` request already exists for the same (feature, operation,
reason code) and the code is approvable without new data; anything else opens or reuses a request and
leaves the step in ``requires_review``. Only ``auto_approved`` and ``expert_approved`` steps reach the RAL.

Gates, in order (the first eight follow the group's controller; the last two are this repository's):

 1. machine_incompatible         machine does not support the operation
 2. missing_knowledge            sensor evidence enabled but no operation log to align states with
 3. missing_knowledge            no parameter set inferred for (feature, operation)
 4. rule_conflict                more than one parameter set with differing values
 5. missing_knowledge            parameter set lacks one of the six FDM parameters
 6. unsafe_value                 a value outside the machine's declared safety limits
 7. low_confidence_mapping       combined mapping confidence below threshold
 8. (feature level, before steps) unresolved_mapping, low_confidence_mapping, missing_knowledge (no operation)
 9. anomalous_operational_state  an anomalous state was observed during the deposition of this feature
10. parameter_adjustment_suggested  a rule conditioned on that evidence recommends another parameter set

Gates 9 and 10 are inert when no evidence is attached to the feature, so a run without the sensor module
behaves exactly like the group's controller. A recommendation never replaces the approved parameter
records: it is attached to the step with its rule identifier, ontology sources and the evidence states,
and the expert decides.
"""
from __future__ import annotations

from framework.cfrm import ReconciledFeature
from framework.expert_validation import APPROVABLE_WITHOUT_NEW_DATA, ExpertValidationStore
from framework.skl.build_ontologies import PARAMETER_NAMES
from framework.skl.repository import SKLRepository

VALUE_TOLERANCE = 1e-6
LIMIT_CHECKS = (
    ("nozzle_temp", "hasSafetyMaxNozzleTemp", "max"), ("nozzle_temp", "hasSafetyMinNozzleTemp", "min"),
    ("print_speed", "hasSafetyMaxPrintSpeed", "max"), ("layer_height", "hasSafetyMaxLayerHeight", "max"),
    ("layer_height", "hasSafetyMinLayerHeight", "min"), ("flow_rate", "hasSafetyMaxFlowRate", "max"),
    ("retraction", "hasSafetyMaxRetraction", "max"),
)
APPROVED_STATUSES = ("auto_approved", "expert_approved")


class KEFCController:
    def __init__(self, repo: SKLRepository, expert_store: ExpertValidationStore, machine_key: str = "fdm_printer_lab",
                 sensor_evidence_enabled: bool = True):
        self.repo = repo
        self.store = expert_store
        self.machine_key = machine_key
        self.sensor_evidence_enabled = sensor_evidence_enabled
        self.limits = repo.machine_limits(machine_key)

    # ------------------------------------------------------------------ plan
    def build_manufacturing_plan(self, features: list[ReconciledFeature], material: str, job_id: str,
                                 operation_log_present: bool) -> dict:
        if self.repo.reasoning_report is None:
            raise RuntimeError("KEFC needs a reasoned repository")
        feature_requests: list[dict] = []
        candidates: list[tuple[int, int, ReconciledFeature, dict]] = []
        for rf in features:
            if rf.unmapped:
                req = self.store.create_request(rf.feature_id, rf.type, "unresolved_mapping",
                                                f"feature {rf.local_id}: {rf.mapping_note}")
                feature_requests.append({"feature_id": rf.feature_id, "reason_code": "unresolved_mapping", "request_id": req.request_id})
                continue
            if rf.low_confidence:
                req = self.store.create_request(rf.feature_id, rf.type, "low_confidence_mapping",
                                                f"feature {rf.local_id}: combined confidence {rf.combined_confidence:.2f}")
                feature_requests.append({"feature_id": rf.feature_id, "reason_code": "low_confidence_mapping", "request_id": req.request_id})
            ops = self.repo.get_operations(rf.individual)
            if not ops:
                req = self.store.create_request(rf.feature_id, rf.type, "missing_knowledge",
                                                f"feature {rf.local_id} ({rf.owl_class}): no operation inferred")
                feature_requests.append({"feature_id": rf.feature_id, "reason_code": "missing_knowledge", "request_id": req.request_id})
                continue
            for op in ops:
                candidates.append((op["precedence"], rf.feature_id, rf, op))
        candidates.sort(key=lambda c: (c[0], c[1], c[3]["operation"]))
        steps = [self._build_step(n, rf, op, material, operation_log_present) for n, (_, _, rf, op) in enumerate(candidates, start=1)]
        self.store.save()
        halt: dict[str, int] = {}
        for s in steps:
            for e in s["exceptions"]:
                halt[e["reason_code"]] = halt.get(e["reason_code"], 0) + 1
        return {
            "job_id": job_id, "material": material, "machine": self.machine_key,
            "sensor_evidence_enabled": self.sensor_evidence_enabled, "operation_log_present": operation_log_present,
            "steps": steps, "approved_steps": [s for s in steps if s["validation_status"] in APPROVED_STATUSES],
            "feature_level_requests": feature_requests,
            "skl_version": self.repo.skl_version, "reasoner": self.repo.reasoning_report["reasoner"],
            "reasoning_status": self.repo.reasoning_report["reasoning_status"],
            "expert_validation_summary": self.store.summary(), "halt_summary": halt,
        }

    # ------------------------------------------------------------------ one step
    def _build_step(self, number: int, rf: ReconciledFeature, op: dict, material: str, operation_log_present: bool) -> dict:
        operation = op["operation"]
        exceptions: list[dict] = []
        ftype = rf.leaf_class or rf.owl_class or rf.type

        if not self.repo.machine_supports_operation(self.machine_key, operation):
            exceptions.append({"reason_code": "machine_incompatible", "detail": f"{self.machine_key} does not support {operation}"})
        if self.sensor_evidence_enabled and not operation_log_present:
            exceptions.append({"reason_code": "missing_knowledge",
                               "detail": "operation log absent: sensor states cannot be aligned with this step"})

        sets = [s for s in self.repo.get_parameter_sets(rf.individual) if s["operation"] == operation]
        parameters: dict[str, dict] = {}
        chosen = None
        if not sets:
            exceptions.append({"reason_code": "missing_knowledge", "detail": f"no parameter set inferred for {ftype} with {material} on {operation}"})
        else:
            conflict = self._detect_conflict(sets)
            if conflict:
                exceptions.append({"reason_code": "rule_conflict", "detail": conflict})
            chosen = sorted(sets, key=lambda s: s["name"])[0]
            missing = [p for p in PARAMETER_NAMES if p not in chosen["values"]]
            if missing:
                exceptions.append({"reason_code": "missing_knowledge", "detail": f"parameter set {chosen['name']} lacks {missing}"})
            parameters = self._assemble_parameters(chosen, rf, material)
            for unsafe in self._check_unsafe(parameters):
                exceptions.append({"reason_code": "unsafe_value", "detail": unsafe})
        if rf.low_confidence:
            exceptions.append({"reason_code": "low_confidence_mapping", "detail": f"combined confidence {rf.combined_confidence:.2f}"})

        adjustments: list[dict] = []
        if rf.evidence_state_ids:
            exceptions.append({"reason_code": "anomalous_operational_state",
                               "detail": f"anomalous state(s) {rf.evidence_state_ids} observed during the deposition of feature {rf.local_id}"})
            for rec in self.repo.get_recommended_sets(rf.individual):
                if rec["operation"] != operation:
                    continue
                changes = {p: {"from": parameters.get(p, {}).get("value"), "to": v["value"], "unit": v["unit"]}
                           for p, v in rec["values"].items()
                           if parameters.get(p) is None or abs(parameters[p]["value"] - v["value"]) > VALUE_TOLERANCE}
                adj = {"parameter_set": rec["name"], "rule_id": rec["rule_ids"][0] if rec["rule_ids"] else None,
                       "rule_ids": rec["rule_ids"], "ontology_sources": rec["ontology_sources"], "values": rec["values"],
                       "changes": changes, "evidence_state_ids": list(rf.evidence_state_ids), "request_id": None}
                adjustments.append(adj)
                exceptions.append({"reason_code": "parameter_adjustment_suggested",
                                   "detail": f"rule {adj['rule_id']} recommends {rec['name']} ({', '.join(f'{p} {c['from']}->{c['to']}' for p, c in changes.items()) or 'no value change'}) "
                                             f"on evidence {rf.evidence_state_ids}"})

        status, request_ids = self._resolve_exceptions(rf, operation, exceptions)
        for adj in adjustments:
            req = self.store.find_resolution(rf.feature_id, operation, "parameter_adjustment_suggested")
            adj["request_id"] = req.request_id if req else None
        return {
            "step_number": number, "feature_id": rf.feature_id, "feature_local_id": rf.local_id, "feature_individual": rf.individual,
            "feature_type": ftype, "feature_classes": self.repo.feature_classes(rf.individual), "operation": operation,
            "precedence": op["precedence"], "operation_rule_ids": op["rule_ids"], "operation_ontology_sources": op["ontology_sources"],
            "machine": self.machine_key, "material": material, "parameter_set": chosen["name"] if chosen else None,
            "parameters": parameters, "dimensions": dict(rf.dimensions), "mapping_confidence": rf.combined_confidence,
            "exceptions": exceptions, "validation_status": status, "expert_request_ids": request_ids,
            "evidence_state_ids": list(rf.evidence_state_ids), "recommended_adjustments": adjustments,
        }

    def _detect_conflict(self, sets: list[dict]) -> str | None:
        if len(sets) < 2:
            return None
        first = sets[0]
        for other in sets[1:]:
            for p in PARAMETER_NAMES:
                a, b = first["values"].get(p), other["values"].get(p)
                if a is None or b is None or abs(a["value"] - b["value"]) > VALUE_TOLERANCE:
                    return (f"parameter sets {first['name']} (rules {first['rule_ids']}) and {other['name']} (rules {other['rule_ids']}) "
                            f"disagree on {p}")
        return None

    def _assemble_parameters(self, ps: dict, rf: ReconciledFeature, material: str) -> dict[str, dict]:
        input_facts = {"feature_id": rf.feature_id, "feature_type": rf.leaf_class or rf.owl_class, "material": material,
                       "qualifier_rule_id": rf.qualifier_rule_id, "mapping_confidence": rf.combined_confidence,
                       "parameter_set": ps["name"]}
        out = {}
        for p, v in ps["values"].items():
            out[p] = {"value": v["value"], "unit": v["unit"], "source": "swrl_rule",
                      "rule_id": ps["rule_ids"][0] if ps["rule_ids"] else "unattributed", "rule_ids": list(ps["rule_ids"]),
                      "ontology_sources": list(ps["ontology_sources"]), "input_facts": input_facts}
        return out

    def _check_unsafe(self, parameters: dict[str, dict]) -> list[str]:
        out = []
        for p, limit, kind in LIMIT_CHECKS:
            if p not in parameters or limit not in self.limits:
                continue
            v, lim = parameters[p]["value"], self.limits[limit]
            if (kind == "max" and v > lim + VALUE_TOLERANCE) or (kind == "min" and v < lim - VALUE_TOLERANCE):
                out.append(f"{p}={v} {parameters[p]['unit']} violates {limit}={lim} of {self.machine_key}")
        return out

    def _resolve_exceptions(self, rf: ReconciledFeature, operation: str, exceptions: list[dict]) -> tuple[str, list[str]]:
        if not exceptions:
            return "auto_approved", []
        ftype = rf.leaf_class or rf.owl_class or rf.type
        all_resolved = True
        ids: list[str] = []
        for e in exceptions:
            code = e["reason_code"]
            req = self.store.find_resolution(rf.feature_id, operation, code)
            if req is not None and req.status == "expert_approved" and code in APPROVABLE_WITHOUT_NEW_DATA:
                ids.append(req.request_id)
                continue
            req = self.store.create_request(rf.feature_id, ftype, code, e["detail"], operation=operation)
            ids.append(req.request_id)
            all_resolved = False
        return ("expert_approved" if all_resolved else "requires_review"), sorted(set(ids))
