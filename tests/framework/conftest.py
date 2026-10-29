"""Fixtures for the framework tests: a Python-engine SKL repository, an SPCM model fitted on the mini
battery, and a helper that runs the pipeline pieces up to reasoning without touching the disk."""
from __future__ import annotations

from pathlib import Path

import pytest

import sensores
from framework import cfrm, kinm, spcm
from framework.main import RunConfig, run_job
from framework.skl.repository import SKLRepository


@pytest.fixture
def repo_python():
    return SKLRepository(reasoner="python", case_id="test")


@pytest.fixture(scope="session")
def spcm_model(bateria_mini):
    import json
    bat = json.loads((Path(bateria_mini) / "bateria.json").read_text(encoding="utf-8"))
    calib = [sensores.carregar(Path(bateria_mini) / i["caso"]) for j, i in bat["jobs"].items() if i["conjunto"] == "calibracao"]
    return spcm.fit(calib, {"method": "kmeans_windows"})


@pytest.fixture
def pieces(spcm_model):
    """KINM -> SPCM -> CFRM -> reasoning in memory. Returns a dict with repo, features, log, states, reconciled."""
    def _run(produto, serie, sensor_evidence=True, drop_log=False, reasoner="python"):
        repo = SKLRepository(reasoner=reasoner, case_id=serie.job_id)
        features = kinm.normalise_product(produto)
        log = [] if drop_log else kinm.normalise_operation_log(serie)
        states = spcm.characterise(spcm_model, serie, log) if sensor_evidence else []
        evidence = spcm.evidence_by_feature(states) if sensor_evidence else {}
        job = repo.assert_job(serie.job_id)
        reconciled = cfrm.map_features(features, repo, "PLA", "fdm_printer_lab", evidence)
        entry_names = cfrm.map_operation_log(log, reconciled, repo, job)
        state_names = cfrm.map_states(states, entry_names, repo, "fdm_printer_lab", job)
        cfrm.assert_evidence(reconciled, state_names, repo)
        repo.reason()
        return {"repo": repo, "features": features, "log": log, "states": states, "reconciled": reconciled,
                "entry_names": entry_names, "state_names": state_names}
    return _run


@pytest.fixture
def run_one(spcm_model, tmp_path):
    def _run(produto, serie, sensor_evidence=True, out=None, **cfg_kwargs):
        cfg_kwargs.setdefault("reasoner", "python")
        cfg = RunConfig(output_dir=str(tmp_path), sensor_evidence=sensor_evidence, **cfg_kwargs)
        out_dir = Path(out) if out else tmp_path / serie.job_id
        return run_job(serie.job_id, produto, serie, "", spcm_model if sensor_evidence else None, cfg, out_dir), out_dir
    return _run
