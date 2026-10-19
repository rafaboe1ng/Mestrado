import pytest

from contracts.grafo import GrafoConhecimento
from grafo import construir, exportar_graphml, exportar_json, id_feature, id_job, id_parametro, id_produto, metricas_integracao, segmentos
from tests.conftest import estados_gabarito

pytestmark = pytest.mark.grafo


def test_construir_grafo_valido_e_completo(base, job_fino):
    produto, serie, anomalias = job_fino
    estados = estados_gabarito(serie.job_id, anomalias)
    g = construir(produto, base, serie, estados)
    assert g.validar() == []
    assert id_produto(produto) in g.nos and id_job(serie.job_id) in g.nos
    assert id_feature(produto, "parede") in g.nos and id_parametro("velocidade") in g.nos
    requer = g.arestas_de(id_feature(produto, "parede"), "requer")
    assert {a.atributos["regra_id"] for a in requer} == {"R1", "R2"}
    assert all(a.proveniencia.startswith("processo/regra:") for a in requer)
    m = metricas_integracao(g, produto, serie, estados)
    assert m["cobertura_pct"] == 100.0 and m["proveniencia_pct"] == 100.0
    anomalos = [n for n in g.nos_do_tipo("estado") if n.atributos["anomalia"]]
    assert len(anomalos) == 1 and anomalos[0].atributos["inicio_s"] == 300.0
    ops = [g.nos[a.destino].atributos["descricao"] for a in g.arestas_de(anomalos[0].id, "ocorre_durante")]
    assert ops == ["fase parede"]


def test_segmentos_agrupa_janelas_contiguas(job_fino):
    _, serie, anomalias = job_fino
    segs = segmentos(estados_gabarito(serie.job_id, anomalias))
    nomes = [(s["nome"], s["anomalia"]) for s in segs]
    assert nomes == [("aquecimento", False), ("impressao", False), ("anomalia", True), ("impressao", False), ("resfriamento", False)]


def test_exportacoes(tmp_path, base, job_limpo):
    produto, serie, anomalias = job_limpo
    g = construir(produto, base, serie, estados_gabarito(serie.job_id, anomalias))
    caminho = exportar_json(g, tmp_path / "g.json")
    import json
    g2 = GrafoConhecimento.de_dict(json.loads(caminho.read_text(encoding="utf-8")))
    assert len(g2.nos) == len(g.nos) and len(g2.arestas) == len(g.arestas) and g2.validar() == []
    gm = exportar_graphml(g, tmp_path / "g.graphml")
    assert gm.read_text(encoding="utf-8").count("<node ") == len(g.nos)
