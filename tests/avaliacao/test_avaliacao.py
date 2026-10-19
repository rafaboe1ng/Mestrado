import pytest

from avaliacao import avaliar_estados, metricas_binarias, parametros_apos, pureza, regua
from contracts.recomendacao import Ajuste, PassoExplicacao, Recomendacao
from tests.conftest import estados_gabarito

pytestmark = pytest.mark.avaliacao


def test_metricas_binarias():
    m = metricas_binarias([True, True, False, False], [True, False, True, False])
    assert (m["vp"], m["fp"], m["fn"], m["vn"]) == (1, 1, 1, 1)
    assert m["precisao"] == 0.5 and m["revocacao"] == 0.5 and m["f1"] == 0.5
    assert metricas_binarias([False], [False])["f1"] == 0.0


def test_pureza():
    assert pureza([0, 0, 1, 1], ["a", "a", "b", "b"]) == 1.0
    assert pureza([0, 0, 0, 0], ["a", "a", "b", "b"]) == 0.5


def test_parametros_apos():
    rec = Recomendacao("j", "m", True, (1,), None, (), (), (Ajuste("velocidade", 80, 45, "R1"),), True, {})
    assert parametros_apos({"velocidade": 80.0, "fluxo": 100.0}, rec) == {"velocidade": 45, "fluxo": 100.0}
    assert parametros_apos({"velocidade": 80.0}, None) == {"velocidade": 80.0}


def test_regua_agrega_pela_mesma_funcao():
    anom = [(300.0, 420.0, "parede", "x")]
    gabarito = {
        "j1": {"causa_feature": "parede", "regras_violadas": ["R1"], "janelas": [{"indice": j.indice, "estado": "x", "anomalia": j.anomalia} for j in estados_gabarito("j1", anom).janelas]},
        "j2": {"causa_feature": None, "regras_violadas": [], "janelas": [{"indice": j.indice, "estado": "x", "anomalia": j.anomalia} for j in estados_gabarito("j2", []).janelas]},
    }
    passo = PassoExplicacao("a", "r", "b", "d", "prov")
    rec1 = Recomendacao("j1", "m", True, (30,), "parede", ("R1",), (passo,), (Ajuste("velocidade", 80, 45, "R1"),), True,
                        {"tempo_pct": 77.8, "material_pct": 0.0, "qualidade_pontos": 0.0})
    rec2 = Recomendacao("j2", "m", False, (), None, (), (), (), True, {"tempo_pct": 0.0, "material_pct": 0.0, "qualidade_pontos": 0.0})
    r = regua("m", {"j1": {"estados": estados_gabarito("j1", anom), "recomendacao": rec1, "violacoes_apos": 0},
                    "j2": {"estados": estados_gabarito("j2", []), "recomendacao": rec2, "violacoes_apos": 0}}, gabarito)
    assert r["anomalia_f1"] == 1.0 and r["acuracia_causa"] == 1.0 and r["taxa_resolve"] == 1.0
    assert r["taxa_viavel"] == 1.0 and r["taxa_tradeoffs"] == 1.0 and r["taxa_explicacao_completa"] == 1.0
    assert r["n_jobs"] == 2 and r["por_job"][0]["job"] == "j1"
    e = avaliar_estados(estados_gabarito("j1", []), gabarito["j1"])
    assert e["fn"] == 12 and e["f1"] == 0.0
