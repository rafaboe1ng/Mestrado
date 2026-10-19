import pytest

from grafo import construir
from raciocinio import baseline_geometrico, baseline_temporal, recomendar
from tests.conftest import estados_gabarito

pytestmark = pytest.mark.raciocinio


def _grafo(base, job):
    produto, serie, anomalias = job
    return construir(produto, base, serie, estados_gabarito(serie.job_id, anomalias)), serie.job_id


def test_atribui_parede_fina_com_regras_e_ajustes(base, job_fino):
    g, job = _grafo(base, job_fino)
    rec = recomendar(g, job)
    assert rec.validar() == []
    assert rec.anomalia_detectada and rec.causa_feature == "parede"
    assert set(rec.regras_violadas) == {"R1", "R2"}
    ajustes = {a.parametro: (a.de, a.para) for a in rec.ajustes}
    assert ajustes == {"velocidade": (80.0, 45.0), "resfriamento": (40.0, 60.0)}
    assert rec.viavel
    assert set(rec.tradeoffs) == {"tempo_pct", "material_pct", "qualidade_pontos"}
    assert rec.tradeoffs["tempo_pct"] > 0 and rec.tradeoffs["qualidade_pontos"] > 0
    relacoes = [p.relacao for p in rec.explicacao]
    assert relacoes[:3] == ["observado_como", "ocorre_durante", "imprime"] and "requer" in relacoes and "usa_parametro" in relacoes
    assert all(p.proveniencia for p in rec.explicacao)


def test_sem_anomalia_nao_ha_causa_nem_ajuste(base, job_limpo):
    g, job = _grafo(base, job_limpo)
    rec = recomendar(g, job)
    assert not rec.anomalia_detectada and rec.causa_feature is None and rec.ajustes == ()
    assert baseline_geometrico(g, job).causa_feature is None
    assert baseline_temporal(g, job).causa_feature is None


def test_anomalia_sem_regra_violada_fica_sem_causa(base, job_espontaneo):
    g, job = _grafo(base, job_espontaneo)
    rec = recomendar(g, job)
    assert rec.anomalia_detectada and rec.causa_feature is None and rec.ajustes == ()
    assert len(rec.explicacao) == 1  # o passo que diz por que nao atribuiu
    assert baseline_temporal(g, job).causa_feature == "base"  # o baseline temporal culpa a feature ativa
    assert baseline_geometrico(g, job).causa_feature == "parede"  # o geometrico culpa sempre a parede


def test_baselines_passam_pelo_mesmo_contrato(base, job_fino):
    g, job = _grafo(base, job_fino)
    for rec in (baseline_geometrico(g, job), baseline_temporal(g, job)):
        assert rec.validar() == [] and rec.causa_feature == "parede" and rec.regras_violadas == ()
        assert {a.parametro for a in rec.ajustes} == {"velocidade", "resfriamento"}  # volta ao padrao
        assert set(rec.tradeoffs) == {"tempo_pct", "material_pct", "qualidade_pontos"}
