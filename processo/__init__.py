"""Modulo processo: a base de conhecimento de processo e sua aplicacao a um produto.

Fornece a base FDM/PLA inicial (parametros, regras feature->parametro, impactos sobre
objetivos), leitura/escrita em JSON e as consultas ``regras_aplicaveis`` e ``violacoes``.
As regras R1..R5 sao praticas comuns escritas por nos; o campo ``fonte`` marca
"a confirmar" ate que haja fonte ou ensaio (PLANO, ameaca transversal 3).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from contracts.base import comparar, garantir
from contracts.processo import Condicao, ConhecimentoProcesso, Impacto, Parametro, RegraProcesso, Restricao
from contracts.produto import Feature, ProdutoFeatures

__all__ = ["base_fdm_pla", "carregar_base", "salvar_base", "regras_aplicaveis", "violacoes", "Violacao"]

A_CONFIRMAR = "pratica comum FDM; a confirmar com ensaio ou fonte antes de P9"


def base_fdm_pla() -> ConhecimentoProcesso:
    parametros = (
        Parametro("temp_bico", "C", 190.0, 230.0, 210.0),
        Parametro("velocidade", "mm/s", 20.0, 100.0, 50.0),
        Parametro("altura_camada", "mm", 0.1, 0.3, 0.2),
        Parametro("resfriamento", "%", 0.0, 100.0, 100.0),
        Parametro("fluxo", "%", 85.0, 115.0, 100.0),
        Parametro("retracao", "mm", 0.0, 8.0, 5.0),
    )
    regras = (
        RegraProcesso("R1", Condicao("parede", "espessura_mm", "<", 1.2), Restricao("velocidade", "<=", 45.0),
                      "paredes finas oscilam e empenam em velocidade alta", A_CONFIRMAR),
        RegraProcesso("R2", Condicao("parede", "espessura_mm", "<", 1.2), Restricao("resfriamento", ">=", 60.0),
                      "parede fina precisa solidificar antes da proxima camada", A_CONFIRMAR),
        RegraProcesso("R3", Condicao("aba", "angulo_graus", ">", 50.0), Restricao("velocidade", "<=", 50.0),
                      "balanco acentuado cai ou empena em velocidade alta", A_CONFIRMAR),
        RegraProcesso("R4", Condicao("furo", "diametro_mm", "<", 3.0), Restricao("fluxo", "<=", 100.0),
                      "furos pequenos fecham com sobre-extrusao", A_CONFIRMAR),
        RegraProcesso("R5", Condicao("nervura", "espessura_mm", "<", 1.0), Restricao("velocidade", "<=", 40.0),
                      "nervura fina oscila em velocidade alta", A_CONFIRMAR),
    )
    impactos = (
        Impacto("velocidade", "tempo", -1, "tempo ~ 1/velocidade"),
        Impacto("altura_camada", "tempo", -1, "tempo ~ 1/altura_camada"),
        Impacto("altura_camada", "qualidade", -1, "camada mais alta piora o acabamento"),
        Impacto("fluxo", "material", 1, "material ~ fluxo"),
        Impacto("resfriamento", "qualidade", 1, "mais resfriamento define melhor detalhes finos"),
    )
    base = ConhecimentoProcesso("FDM", "PLA", parametros, regras, impactos)
    garantir(base)
    return base


def carregar_base(caminho: str | Path) -> ConhecimentoProcesso:
    base = ConhecimentoProcesso.de_dict(json.loads(Path(caminho).read_text(encoding="utf-8")))
    garantir(base)
    return base


def salvar_base(base: ConhecimentoProcesso, caminho: str | Path) -> Path:
    garantir(base)
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(base.para_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return caminho


def regras_aplicaveis(base: ConhecimentoProcesso, produto: ProdutoFeatures) -> list[tuple[RegraProcesso, Feature]]:
    """Pares (regra, feature) em que a condicao da regra vale para a feature do produto."""
    pares = []
    for regra in base.regras:
        c = regra.condicao
        for f in produto.features:
            if f.tipo != c.tipo_feature or c.atributo not in f.dimensoes:
                continue
            if comparar(float(f.dimensoes[c.atributo]), c.operador, c.valor):
                pares.append((regra, f))
    return pares


@dataclass(frozen=True)
class Violacao:
    regra: RegraProcesso
    feature: Feature
    valor_usado: float


def violacoes(base: ConhecimentoProcesso, produto: ProdutoFeatures, parametros_usados: dict[str, float]) -> list[Violacao]:
    """Regras aplicaveis ao produto cuja restricao o job nao respeitou."""
    saida = []
    for regra, feature in regras_aplicaveis(base, produto):
        r = regra.restricao
        valor = parametros_usados.get(r.parametro)
        if valor is None:
            continue
        if not comparar(float(valor), r.operador, r.valor):
            saida.append(Violacao(regra, feature, float(valor)))
    return saida
