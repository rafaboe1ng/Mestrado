import json

import networkx as nx
import pytest
from rdflib import Graph

from framework.expert_validation import ExpertValidationStore
from framework.kg import UnknownNodeTypeError, export_rdf
from framework.ral import PrintProfileSerialiser
from framework.sparql_suite import PREFIXES, SUITE, run_suite

pytestmark = pytest.mark.framework


def test_ral_refuses_steps_without_required_geometry(tmp_path):
    store = ExpertValidationStore(tmp_path / "e.json")
    step = {"step_number": 1, "feature_id": 1, "feature_local_id": "parede", "feature_type": "ThinWall", "operation": "WallDepositionOp",
            "dimensions": {"height_mm": 30.0}, "validation_status": "auto_approved",
            "parameters": {p: {"value": 1.0, "unit": "u", "rule_id": "r"} for p in ("nozzle_temp", "print_speed", "layer_height", "cooling_fan", "flow_rate", "retraction")}}
    plan = {"job_id": "j", "material": "PLA", "machine": "m", "skl_version": "v", "reasoner": "python", "approved_steps": [step]}
    acc = PrintProfileSerialiser(store).serialise(plan, tmp_path)
    assert acc["handed"] == 1 and acc["serialised"] == 0 and acc["refused"] == 1
    assert acc["refusals"][0]["request_id"] and store.all_requests()[0].reason_code == "serialisation_input_missing"
    assert json.loads((tmp_path / "print_profile.json").read_text())["steps"] == []


def test_run_job_passes_suite_and_writes_all_files(run_one, job_fino):
    produto, serie, _ = job_fino
    summary, out = run_one(produto, serie, sensor_evidence=True)
    assert summary["sparql"]["failed"] == 0 and summary["steps_retained_by_evidence"] == ["parede"]
    for name in ("manufacturing_plan.json", "unified_graph.ttl", "sparql_results.json", "print_profile.json", "print_profile.ini",
                 "case_ontology.owl", "reasoning_report.json", "expert_validation_requests.json", "operational_states.json"):
        assert (out / name).exists(), name
    assert summary["ral"] == {"handed": 5, "serialised": 5, "refused": 0}
    g = Graph().parse(str(out / "unified_graph.ttl"), format="turtle")
    rows = list(g.query(PREFIXES + "SELECT ?s WHERE { ?s mfg:haltReason \"anomalous_operational_state\" ; mfg:evidenceState ?st . }"))
    assert len(rows) == 1
    # the cross-check to the case ontology: the step's parameter set is the one the SKL inferred
    q11 = next(r for r in json.loads((out / "sparql_results.json").read_text())["results"] if r["id"] == "Q11")
    assert q11["passed"] is True and q11["rows"] == 6


def test_ablation_run_has_no_evidence_artifacts(run_one, job_fino):
    produto, serie, _ = job_fino
    summary, out = run_one(produto, serie, sensor_evidence=False)
    assert summary["halt_summary"] == {} and summary["approved_steps"] == 6
    res = json.loads((out / "sparql_results.json").read_text())["results"]
    q22 = next(r for r in res if r["id"] == "Q22")
    assert q22["expected"] == "empty" and q22["passed"] is True
    assert not (out / "operational_states.json").exists()


def test_unknown_node_type_is_not_dropped_silently():
    G = nx.DiGraph()
    G.add_node("sensor_1", node_type="sensor", name="x")
    with pytest.raises(UnknownNodeTypeError):
        export_rdf(G)


def test_suite_ids_are_unique_and_ordered():
    ids = [q.id for q in SUITE]
    assert ids == sorted(ids) and len(set(ids)) == len(ids)
    results = run_suite(Graph(), {"sensor_evidence": False, "operation_log_present": False})
    assert all(r["passed"] in (True, False, None) for r in results)
