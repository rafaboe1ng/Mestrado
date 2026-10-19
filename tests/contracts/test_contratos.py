"""Os contratos precisam rejeitar o que nao passa (PLANO, P0: contratos frouxos passam sempre)."""
import numpy as np
import pytest

from contracts.base import ErroContrato, comparar, garantir
from contracts.estados import EstadosOperacionais, Janela
from contracts.grafo import Aresta, GrafoConhecimento, No
from contracts.processo import Condicao, ConhecimentoProcesso, Parametro, RegraProcesso, Restricao
from contracts.produto import Feature, ProdutoFeatures
from contracts.recomendacao import Ajuste, PassoExplicacao, Recomendacao
from contracts.sensores import OperacaoJob, SerieMultivariada

pytestmark = pytest.mark.contracts


def test_comparar_operadores():
    assert comparar(1, "<", 2) and comparar(2, "<=", 2) and comparar(3, ">", 2) and comparar(2, ">=", 2) and comparar(2.0, "==", 2.0)
    with pytest.raises(ValueError):
        comparar(1, "!=", 2)


def test_produto_rejeita_invalidos():
    dup = ProdutoFeatures("p", "v1", (Feature("a", "base"), Feature("a", "parede")))
    assert any("repetidos" in e for e in dup.validar())
    tipo = ProdutoFeatures("p", "v1", (Feature("a", "engrenagem"),))
    assert any("tipo desconhecido" in e for e in tipo.validar())
    dim = ProdutoFeatures("p", "v1", (Feature("a", "parede", {"espessura_mm": -1}),))
    assert any("> 0" in e for e in dim.validar())
    adj = ProdutoFeatures("p", "v1", (Feature("a", "parede", adjacentes=("zz",)),))
    assert any("nao existe" in e for e in adj.validar())
    with pytest.raises(ErroContrato):
        garantir(adj)


def test_processo_rejeita_invalidos():
    p = (Parametro("velocidade", "mm/s", 20, 100, 150),)
    base = ConhecimentoProcesso("FDM", "PLA", p, ())
    assert any("padrao fora da faixa" in e for e in base.validar())
    regra = RegraProcesso("R", Condicao("parede", "espessura_mm", "<", 1), Restricao("fluxo", "<=", 1), "j", "f")
    base2 = ConhecimentoProcesso("FDM", "PLA", (Parametro("velocidade", "mm/s", 20, 100, 50),), (regra,))
    assert any("nao existe" in e for e in base2.validar())


def test_serie_rejeita_invalidos():
    t = np.array([0.0, 1.0, 0.5])
    v = np.zeros((3, 1))
    s = SerieMultivariada("j", "p", "v", ("x",), t, v, {"a": 1.0}, (), 1.0)
    assert any("crescente" in e for e in s.validar())
    v2 = np.array([[0.0], [np.nan], [1.0]])
    s2 = SerieMultivariada("j", "p", "v", ("x",), np.array([0.0, 1.0, 2.0]), v2, {"a": 1.0}, (), 1.0)
    assert any("NaN" in e for e in s2.validar())
    s3 = SerieMultivariada("j", "p", "v", ("x",), np.array([0.0, 1.0, 2.0]), np.zeros((3, 1)), {"a": 1.0},
                           (OperacaoJob("o", None, 0.0, 99.0),), 1.0)
    assert any("fora da duracao" in e for e in s3.validar())


def test_estados_rejeita_invalidos():
    jan = (Janela(0, 0, 10, 0, False), Janela(1, 20, 30, 0, False))
    e = EstadosOperacionais("j", jan, {0: "a"}, metodo="m")
    assert any("contigua" in x for x in e.validar())
    e2 = EstadosOperacionais("j", (Janela(0, 0, 10, 5, False),), {0: "a"}, metodo="m")
    assert any("sem nome" in x for x in e2.validar())


def test_grafo_rejeita_invalidos():
    g = GrafoConhecimento()
    g.adicionar_no(No("job:1", "job"))
    g.adicionar_no(No("feature:f", "feature"))
    g.adicionar_no(No("parametro:v", "parametro"))
    g.adicionar_aresta(Aresta("job:1", "feature:f", "requer", {}, "x"))  # job->feature nao permitido em requer
    assert any("nao permitido" in e for e in g.validar())
    g2 = GrafoConhecimento()
    g2.adicionar_no(No("feature:f", "feature"))
    g2.adicionar_no(No("parametro:v", "parametro"))
    g2.adicionar_aresta(Aresta("feature:f", "parametro:v", "requer", {}, ""))
    assert any("sem proveniencia" in e for e in g2.validar())
    g3 = GrafoConhecimento()
    g3.adicionar_no(No("feature:f", "feature"))
    g3.adicionar_aresta(Aresta("feature:f", "parametro:zz", "requer", {}, "x"))
    assert any("inexistente" in e for e in g3.validar())
    with pytest.raises(ValueError):
        g3.adicionar_no(No("feature:f", "job"))


def test_recomendacao_rejeita_invalidos():
    r = Recomendacao("j", "m", True, (1,), "parede", ("R1",), (), (), True, {})
    assert any("sem explicacao" in e for e in r.validar())
    passo = PassoExplicacao("a", "r", "b", "d", "prov")
    r2 = Recomendacao("j", "m", True, (1,), "parede", ("R1",), (passo,), (Ajuste("v", 50, 50, "R1"),), True, {})
    assert any("ajuste nulo" in e for e in r2.validar())
    r3 = Recomendacao("j", "m", False, (), "parede", (), (passo,), (), True, {})
    assert any("sem anomalia" in e for e in r3.validar())
