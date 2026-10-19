import pytest

from diagnostico.etapas import diagnosticar

pytestmark = pytest.mark.diagnostico


def test_diagnostico_passa_na_bateria_mini(bateria_mini):
    rel = diagnosticar(bateria_mini)
    assert [r["etapa"][0] for r in rel] == [str(i) for i in range(8)]
    assert all(r["erros"] == [] for r in rel), [r for r in rel if r["erros"]]
    assert "cobertura 100 %" in rel[5]["entregou"]


def test_diagnostico_para_na_primeira_falha(bateria_mini):
    rel = diagnosticar(bateria_mini, job_id="job_999")
    assert len(rel) == 1 and rel[0]["erros"] and "gerador" in rel[0]["se_falhar"]
