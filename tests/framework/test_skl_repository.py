import shutil

import pytest

from framework.skl.build_ontologies import KNOWLEDGE_DIR, file_name
from framework.skl.repository import SKLReasonerError, SKLRepository

pytestmark = pytest.mark.framework


def test_loads_five_ontologies_and_rules(repo_python):
    assert len(repo_python.ontologies) == 5
    assert len(repo_python.rules) >= 19
    assert repo_python.reasoner == "python_forward_chaining"
    assert len(repo_python.skl_version) == 12


def test_missing_rule_file_fails_loud(tmp_path):
    with pytest.raises(SKLReasonerError):
        SKLRepository(rules_path=tmp_path / "nope.swrl", reasoner="python")


def test_rule_with_unknown_entity_fails_loud(tmp_path):
    rules = tmp_path / "r.swrl"
    rules.write_text("ghost: Wall(?f) -> requiresOperation(?f, LaserOp)\n", encoding="utf-8")
    with pytest.raises(SKLReasonerError, match="LaserOp"):
        SKLRepository(rules_path=rules, reasoner="python")


def test_missing_ontology_fails_loud(tmp_path):
    dest = tmp_path / "knowledge"
    shutil.copytree(KNOWLEDGE_DIR, dest)
    (dest / file_name("additive_parameters")).unlink()
    with pytest.raises(SKLReasonerError, match="ontology missing"):
        SKLRepository(knowledge_dir=dest, reasoner="python")


def test_pellet_without_java_fails_loud():
    if shutil.which("java"):
        pytest.skip("Java present; the Pellet path is exercised elsewhere")
    with pytest.raises(SKLReasonerError, match="Java"):
        SKLRepository(reasoner="pellet")


def test_thin_wall_gets_exactly_one_parameter_set_with_rule_id(repo_python):
    f = repo_python.assert_feature(1, "Wall", "ThinWall", "PLA", "fdm_printer_lab", "Q1")
    rep = repo_python.reason()
    assert rep["reasoning_status"] == "completed"
    ops = repo_python.get_operations(f)
    assert [o["operation"] for o in ops] == ["WallDepositionOp"] and ops[0]["rule_ids"] == ["wall_requires_wall_deposition"]
    sets = repo_python.get_parameter_sets(f)
    assert [s["name"] for s in sets] == ["PLA_ThinWall_Params"]
    assert sets[0]["rule_ids"] == ["pla_thin_wall_params"]
    assert any(src.endswith("additive-parameters") for src in sets[0]["ontology_sources"])
    assert sets[0]["values"]["print_speed"] == {"value": 45.0, "unit": "mm/s"}
    assert repo_python.get_recommended_sets(f) == []


def test_recommendation_only_with_evidence(repo_python):
    f = repo_python.assert_feature(1, "Wall", "ThinWall", "PLA", "fdm_printer_lab", "Q1")
    job = repo_python.assert_job("j")
    op = repo_python.assert_operation_instance("opinst_1", f, job, 0.0, 10.0, 1)
    st = repo_python.assert_state("state_j_1", "Anomaly", "anomaly", 2.0, 8.0, True, 1.5, 1, "m", {}, "j", "fdm_printer_lab", job, [op])
    repo_python.assert_evidence(f, [st])
    repo_python.reason()
    recs = repo_python.get_recommended_sets(f)
    assert [r["name"] for r in recs] == ["PLA_ThinWall_Recovery_Params"] and recs[0]["rule_ids"] == ["thin_wall_anomaly_recovery"]
    assert [s["name"] for s in repo_python.get_parameter_sets(f)] == ["PLA_ThinWall_Params"], "evidence never changes the required set"
    assert repo_python.evidence_states(f) == ["state_j_1"]


def test_feature_without_leaf_class_gets_no_parameter_set(repo_python):
    f = repo_python.assert_feature(1, "Wall", None, "PLA", "fdm_printer_lab", None)
    repo_python.reason()
    assert repo_python.get_operations(f) and repo_python.get_parameter_sets(f) == []


def test_machine_queries(repo_python):
    assert repo_python.machine_supports_operation("fdm_printer_lab", "WallDepositionOp")
    assert repo_python.machine_limits("fdm_printer_lab")["hasSafetyMaxPrintSpeed"] == 100.0
    with pytest.raises(KeyError):
        repo_python.machine_supports_operation("cnc_lathe", "WallDepositionOp")


def test_version_tracks_rule_file(tmp_path, repo_python):
    rules = tmp_path / "r.swrl"
    rules.write_text(repo_python.rules_path.read_text(encoding="utf-8") + "\nextra_rule: Base(?f) -> requiresOperation(?f, BaseDepositionOp)\n", encoding="utf-8")
    other = SKLRepository(rules_path=rules, reasoner="python")
    assert other.skl_version != repo_python.skl_version
