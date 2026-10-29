"""P14: without knowledge, no plan. Each injection checks the exception AND the folder."""
import shutil

import pytest

from framework.skl.build_ontologies import KNOWLEDGE_DIR, file_name
from framework.skl.repository import SKLReasonerError

pytestmark = pytest.mark.framework

PLAN_FILES = ("manufacturing_plan.json", "print_profile.json", "unified_graph.ttl")


def _nothing_written(out):
    return not out.exists() or not any((out / f).exists() for f in PLAN_FILES)


def test_missing_rules_writes_nothing(run_one, job_limpo, tmp_path):
    produto, serie, _ = job_limpo
    with pytest.raises(SKLReasonerError):
        run_one(produto, serie, sensor_evidence=False, rules_path=str(tmp_path / "missing.swrl"))
    assert _nothing_written(tmp_path / serie.job_id)


def test_missing_ontology_writes_nothing(run_one, job_limpo, tmp_path):
    produto, serie, _ = job_limpo
    kd = tmp_path / "k"
    shutil.copytree(KNOWLEDGE_DIR, kd)
    (kd / file_name("additive_process")).unlink()
    with pytest.raises(SKLReasonerError):
        run_one(produto, serie, sensor_evidence=False, knowledge_dir=str(kd))
    assert _nothing_written(tmp_path / serie.job_id)


def test_malformed_rule_writes_nothing(run_one, job_limpo, tmp_path):
    produto, serie, _ = job_limpo
    bad = tmp_path / "bad.swrl"
    bad.write_text("r1: Wall(?f) ^ greaterThan(?t, 1.2) -> requiresOperation(?f, WallDepositionOp)\n", encoding="utf-8")
    with pytest.raises(SKLReasonerError):
        run_one(produto, serie, sensor_evidence=False, rules_path=str(bad))
    assert _nothing_written(tmp_path / serie.job_id)


def test_pellet_without_java_writes_nothing(run_one, job_limpo, tmp_path):
    if shutil.which("java"):
        pytest.skip("Java present")
    produto, serie, _ = job_limpo
    with pytest.raises(SKLReasonerError):
        run_one(produto, serie, sensor_evidence=False, reasoner="pellet")
    assert _nothing_written(tmp_path / serie.job_id)


def test_missing_operation_log_halts_every_step(run_one, job_fino, tmp_path):
    produto, serie, _ = job_fino
    summary, out = run_one(produto, serie, sensor_evidence=True, drop_operation_log=True)
    assert summary["approved_steps"] == 0 and summary["halt_summary"]["missing_knowledge"] == summary["steps"]
    assert summary["ral"] == {"handed": 0, "serialised": 0, "refused": 0}
