import json

import pytest

from framework.expert_validation import ExpertValidationStore
from framework.kefc import KEFCController
from framework.skl.build_ontologies import PARAMETER_NAMES

pytestmark = pytest.mark.framework


def _plan(p, store, sensor=True, log_present=True, machine="fdm_printer_lab"):
    c = KEFCController(p["repo"], store, machine, sensor_evidence_enabled=sensor)
    return c, c.build_manufacturing_plan(p["reconciled"], "PLA", p["repo"].case_id, operation_log_present=log_present)


def test_without_sensor_module_all_steps_auto_approved(pieces, job_fino, tmp_path):
    produto, serie, _ = job_fino
    p = pieces(produto, serie, sensor_evidence=False)
    _, plan = _plan(p, ExpertValidationStore(tmp_path / "e.json"), sensor=False)
    assert len(plan["steps"]) == 6 and len(plan["approved_steps"]) == 6
    assert plan["halt_summary"] == {} and plan["expert_validation_summary"]["total_requests"] == 0
    for s in plan["steps"]:
        assert set(s["parameters"]) == set(PARAMETER_NAMES)
        for rec in s["parameters"].values():
            assert rec["source"] == "swrl_rule" and rec["rule_id"] and rec["ontology_sources"]


def test_evidence_retains_only_the_affected_feature(pieces, job_fino, tmp_path):
    produto, serie, _ = job_fino
    p = pieces(produto, serie, sensor_evidence=True)
    _, plan = _plan(p, ExpertValidationStore(tmp_path / "e.json"))
    retained = {s["feature_local_id"]: s for s in plan["steps"] if s["validation_status"] == "requires_review"}
    assert set(retained) == {"parede"}
    codes = [e["reason_code"] for e in retained["parede"]["exceptions"]]
    assert codes == ["anomalous_operational_state", "parameter_adjustment_suggested"]
    adj = retained["parede"]["recommended_adjustments"][0]
    assert adj["rule_id"] == "thin_wall_anomaly_recovery" and adj["evidence_state_ids"] and adj["request_id"]
    assert retained["parede"]["parameters"]["print_speed"]["value"] == 45.0, "approved records untouched by the recommendation"
    assert len(plan["approved_steps"]) == 5


def test_parameter_records_identical_with_and_without_sensors(pieces, job_fino, tmp_path):
    produto, serie, _ = job_fino
    a = _plan(pieces(produto, serie, sensor_evidence=True), ExpertValidationStore(tmp_path / "a.json"))[1]
    b = _plan(pieces(produto, serie, sensor_evidence=False), ExpertValidationStore(tmp_path / "b.json"), sensor=False)[1]
    ka = {(s["feature_local_id"], s["operation"]): s["parameters"] for s in a["steps"]}
    kb = {(s["feature_local_id"], s["operation"]): s["parameters"] for s in b["steps"]}
    assert ka == kb


def test_expert_approval_unblocks_only_approvable_codes(pieces, job_espontaneo, job_fino, tmp_path):
    # spontaneous anomaly during the base: evidence halt without a recovery rule -> approvable without new data
    produto, serie, _ = job_espontaneo
    store = ExpertValidationStore(tmp_path / "e.json")
    p = pieces(produto, serie)
    _, plan = _plan(p, store)
    base = next(s for s in plan["steps"] if s["feature_local_id"] == "base")
    assert [e["reason_code"] for e in base["exceptions"]] == ["anomalous_operational_state"]
    store.apply_feedback(base["expert_request_ids"][0], "expert_approved", "inspected the part")
    store.save()
    _, plan2 = _plan(pieces(produto, serie), ExpertValidationStore(tmp_path / "e.json"))
    base2 = next(s for s in plan2["steps"] if s["feature_local_id"] == "base")
    assert base2["validation_status"] == "expert_approved"
    # thin wall: the adjustment request is not approvable without new data, so the step stays in review
    produto, serie, _ = job_fino
    store = ExpertValidationStore(tmp_path / "f.json")
    _, plan = _plan(pieces(produto, serie), store)
    wall = next(s for s in plan["steps"] if s["feature_local_id"] == "parede")
    for rid in wall["expert_request_ids"]:
        store.apply_feedback(rid, "expert_approved")
    store.save()
    _, plan2 = _plan(pieces(produto, serie), ExpertValidationStore(tmp_path / "f.json"))
    wall2 = next(s for s in plan2["steps"] if s["feature_local_id"] == "parede")
    assert wall2["validation_status"] == "requires_review"


def test_missing_operation_log_halts_everything_when_sensors_enabled(pieces, job_fino, tmp_path):
    produto, serie, _ = job_fino
    p = pieces(produto, serie, sensor_evidence=True, drop_log=True)
    _, plan = _plan(p, ExpertValidationStore(tmp_path / "e.json"), log_present=False)
    assert plan["approved_steps"] == []
    assert all(any(e["reason_code"] == "missing_knowledge" for e in s["exceptions"]) for s in plan["steps"])
    # the same absence is irrelevant to the pipeline without sensors
    p = pieces(produto, serie, sensor_evidence=False, drop_log=True)
    _, plan = _plan(p, ExpertValidationStore(tmp_path / "f.json"), sensor=False, log_present=False)
    assert len(plan["approved_steps"]) == 6


def test_unsafe_value_gate(pieces, job_limpo, tmp_path):
    produto, serie, _ = job_limpo
    p = pieces(produto, serie, sensor_evidence=False)
    c = KEFCController(p["repo"], ExpertValidationStore(tmp_path / "e.json"), sensor_evidence_enabled=False)
    c.limits["hasSafetyMaxPrintSpeed"] = 48.0
    plan = c.build_manufacturing_plan(p["reconciled"], "PLA", "j", True)
    unsafe = [s for s in plan["steps"] if any(e["reason_code"] == "unsafe_value" for e in s["exceptions"])]
    assert unsafe and all(s["parameters"]["print_speed"]["value"] > 48.0 for s in unsafe)
    assert all(s["validation_status"] == "requires_review" for s in unsafe)


def test_plan_carries_reasoner_and_version(pieces, job_limpo, tmp_path):
    produto, serie, _ = job_limpo
    p = pieces(produto, serie, sensor_evidence=False)
    _, plan = _plan(p, ExpertValidationStore(tmp_path / "e.json"), sensor=False)
    assert plan["reasoner"] == "python_forward_chaining" and plan["skl_version"] == p["repo"].skl_version
    json.dumps(plan)  # serialisable
