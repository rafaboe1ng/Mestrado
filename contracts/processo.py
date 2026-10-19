"""Fronteira processo -> grafo / raciocinio: conhecimento de processo explicito.

O que passa: parametros com faixa valida, regras cuja restricao aponta para um parametro
existente e cuja condicao usa um tipo de feature do vocabulario, impactos sobre objetivos
conhecidos. O que nao passa: faixa invertida, padrao fora da faixa, regra sobre parametro
inexistente, operador desconhecido, objetivo fora de (material, tempo, qualidade), regra sem fonte.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.base import OPERADORES
from contracts.produto import TIPOS_FEATURE

OBJETIVOS = ("material", "tempo", "qualidade")


@dataclass(frozen=True)
class Parametro:
    nome: str
    unidade: str
    minimo: float
    maximo: float
    padrao: float


@dataclass(frozen=True)
class Condicao:
    """Condicao sobre uma feature: ``<tipo_feature>.<atributo> <operador> <valor>``."""

    tipo_feature: str
    atributo: str
    operador: str
    valor: float

    def texto(self) -> str:
        return f"{self.tipo_feature}.{self.atributo} {self.operador} {self.valor}"


@dataclass(frozen=True)
class Restricao:
    """Restricao sobre um parametro: ``<parametro> <operador> <valor>``."""

    parametro: str
    operador: str
    valor: float

    def texto(self) -> str:
        return f"{self.parametro} {self.operador} {self.valor}"


@dataclass(frozen=True)
class RegraProcesso:
    id: str
    condicao: Condicao
    restricao: Restricao
    justificativa: str
    fonte: str


@dataclass(frozen=True)
class Impacto:
    """Como um parametro move um objetivo. ``sentido`` +1: aumentar o parametro aumenta o objetivo."""

    parametro: str
    objetivo: str
    sentido: int
    modelo: str


@dataclass(frozen=True)
class ConhecimentoProcesso:
    processo: str
    material: str
    parametros: tuple[Parametro, ...]
    regras: tuple[RegraProcesso, ...]
    impactos: tuple[Impacto, ...] = ()

    def parametro(self, nome: str) -> Parametro | None:
        for p in self.parametros:
            if p.nome == nome:
                return p
        return None

    def validar(self) -> list[str]:
        erros: list[str] = []
        nomes = [p.nome for p in self.parametros]
        if not nomes:
            erros.append("base sem parametros")
        if len(nomes) != len(set(nomes)):
            erros.append("parametros com nome repetido")
        for p in self.parametros:
            if not p.minimo < p.maximo:
                erros.append(f"parametro {p.nome}: minimo deve ser < maximo")
            if not p.minimo <= p.padrao <= p.maximo:
                erros.append(f"parametro {p.nome}: padrao fora da faixa")
        ids = [r.id for r in self.regras]
        if len(ids) != len(set(ids)):
            erros.append("regras com id repetido")
        for r in self.regras:
            if r.restricao.parametro not in nomes:
                erros.append(f"regra {r.id}: parametro {r.restricao.parametro!r} nao existe")
            if r.restricao.operador not in OPERADORES or r.condicao.operador not in OPERADORES:
                erros.append(f"regra {r.id}: operador desconhecido")
            if r.condicao.tipo_feature not in TIPOS_FEATURE:
                erros.append(f"regra {r.id}: tipo de feature {r.condicao.tipo_feature!r} desconhecido")
            if not r.fonte:
                erros.append(f"regra {r.id}: sem fonte")
        for i in self.impactos:
            if i.parametro not in nomes:
                erros.append(f"impacto sobre parametro inexistente {i.parametro!r}")
            if i.objetivo not in OBJETIVOS:
                erros.append(f"impacto sobre objetivo desconhecido {i.objetivo!r}")
            if i.sentido not in (-1, 1):
                erros.append(f"impacto {i.parametro}->{i.objetivo}: sentido deve ser -1 ou +1")
        return erros

    def para_dict(self) -> dict[str, Any]:
        return {
            "processo": self.processo,
            "material": self.material,
            "parametros": [vars(p) for p in self.parametros],
            "regras": [
                {
                    "id": r.id,
                    "condicao": vars(r.condicao),
                    "restricao": vars(r.restricao),
                    "justificativa": r.justificativa,
                    "fonte": r.fonte,
                }
                for r in self.regras
            ],
            "impactos": [vars(i) for i in self.impactos],
        }

    @classmethod
    def de_dict(cls, d: dict[str, Any]) -> "ConhecimentoProcesso":
        return cls(
            d["processo"],
            d["material"],
            tuple(Parametro(**p) for p in d["parametros"]),
            tuple(
                RegraProcesso(r["id"], Condicao(**r["condicao"]), Restricao(**r["restricao"]), r["justificativa"], r["fonte"])
                for r in d["regras"]
            ),
            tuple(Impacto(**i) for i in d.get("impactos", [])),
        )
