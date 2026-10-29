import json
from pathlib import Path

import pytest

from framework import spcm
from framework.main import RunConfig, run

pytestmark = pytest.mark.framework


def test_run_reference_and_ablation_on_mini_battery(bateria_mini, tmp_path):
    ref = run(RunConfig(output_dir=str(tmp_path / "ref"), data_root=str(bateria_mini), reasoner="python", label="reference"))
    abl = run(RunConfig(output_dir=str(tmp_path / "abl"), data_root=str(bateria_mini), reasoner="python", sensor_evidence=False, label="ablation"))
    assert ref["jobs"] == abl["jobs"] == 4 and ref["steps"] == abl["steps"] == 24
    assert abl["halt_summary"] == {} and abl["approved_steps"] == 24
    assert ref["sparql_failed"] == 0 and abl["sparql_failed"] == 0
    assert (tmp_path / "ref" / "run_summary.json").exists() and (tmp_path / "ref" / "config.json").exists()
    cfg = json.loads((tmp_path / "ref" / "config.json").read_text(encoding="utf-8"))
    assert cfg["spcm_model"]["method"] == "kmeans_windows" and len(cfg["calibration_jobs_used"]) == 4
    assert ref["reasoner"] == ["python_forward_chaining"]


def test_spcm_label_translation_and_evidence(bateria_mini, spcm_model):
    import sensores
    from framework import kinm
    bat = json.loads((Path(bateria_mini) / "bateria.json").read_text(encoding="utf-8"))
    gab = json.loads((Path(bateria_mini) / "gabarito.json").read_text(encoding="utf-8"))
    for j, info in bat["jobs"].items():
        serie = sensores.carregar(Path(bateria_mini) / info["caso"])
        states = spcm.characterise(spcm_model, serie, kinm.normalise_operation_log(serie))
        assert all(s.label.isascii() for s in states)
        assert sum(s.window_count for s in states) == len(gab[j]["janelas"])
        assert all(a.transitions_to == b.state_id for a, b in zip(states, states[1:]))
    assert spcm.translate_label("impressao_2") == "printing_2"
