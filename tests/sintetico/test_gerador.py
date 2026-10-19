import json

import pytest

from dados.sintetico.gerador import gerar_bateria

pytestmark = pytest.mark.sintetico


def test_bateria_deterministica(tmp_path):
    a = tmp_path / "a"
    b = tmp_path / "b"
    gerar_bateria(a, n_jobs=5, n_calibracao=2, semente=42)
    gerar_bateria(b, n_jobs=5, n_calibracao=2, semente=42)
    assert (a / "gabarito.json").read_text(encoding="utf-8") == (b / "gabarito.json").read_text(encoding="utf-8")
    assert (a / "casos" / "job_003" / "serie.csv").read_bytes() == (b / "casos" / "job_003" / "serie.csv").read_bytes()


def test_estrutura_e_gabarito(bateria_mini):
    bateria = json.loads((bateria_mini / "bateria.json").read_text(encoding="utf-8"))
    gab = json.loads((bateria_mini / "gabarito.json").read_text(encoding="utf-8"))
    assert set(bateria["jobs"]) == set(gab) and len(gab) == 8
    conjuntos = [i["conjunto"] for i in bateria["jobs"].values()]
    assert conjuntos.count("calibracao") == 4 and conjuntos.count("avaliacao") == 4
    for job, g in gab.items():
        assert len(g["janelas"]) == 60
        assert (bateria_mini / bateria["jobs"][job]["ficha"]).exists()
        assert (bateria_mini / bateria["jobs"][job]["caso"] / "serie.csv").exists()
        if g["causa_feature"] is not None:
            assert g["causa_feature"] in {"parede", "aba"} and g["regras_violadas"]
        anom = [j for j in g["janelas"] if j["anomalia"]]
        assert bool(anom) == bool(g["anomalias"])
