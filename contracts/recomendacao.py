"""Fronteira raciocinio -> avaliacao: a recomendacao de reconfiguracao e sua explicacao.

O que passa: metodo identificado; se ha causa atribuida, ha caminho de explicacao com
proveniencia em todo passo; ajustes com valor de origem diferente do destino; trade-offs
com as chaves conhecidas. O que nao passa: causa sem explicacao, passo sem proveniencia,
ajuste nulo, causa presente sem anomalia detectada.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

CHAVES_TRADEOFF = ("tempo_pct", "material_pct", "qualidade_pontos")


@dataclass(frozen=True)
class PassoExplicacao:
    origem: str
    relacao: str
    destino: str
    detalhe: str
    proveniencia: str


@dataclass(frozen=True)
class Ajuste:
    parametro: str
    de: float
    para: float
    regra_id: str


@dataclass(frozen=True)
class Recomendacao:
    job_id: str
    metodo: str
    anomalia_detectada: bool
    janelas_anomalas: tuple[int, ...]
    causa_feature: str | None
    regras_violadas: tuple[str, ...]
    explicacao: tuple[PassoExplicacao, ...]
    ajustes: tuple[Ajuste, ...]
    viavel: bool
    tradeoffs: dict[str, float] = field(default_factory=dict)

    def validar(self) -> list[str]:
        erros: list[str] = []
        if not self.metodo:
            erros.append("metodo vazio")
        if not self.anomalia_detectada and (self.causa_feature or self.janelas_anomalas):
            erros.append("sem anomalia detectada nao pode haver causa nem janelas anomalas")
        if self.causa_feature and not self.explicacao:
            erros.append("causa atribuida sem explicacao")
        for p in self.explicacao:
            if not p.proveniencia:
                erros.append(f"passo {p.origem} -{p.relacao}-> {p.destino} sem proveniencia")
        for a in self.ajustes:
            if a.de == a.para:
                erros.append(f"ajuste nulo em {a.parametro}")
        for k in self.tradeoffs:
            if k not in CHAVES_TRADEOFF:
                erros.append(f"trade-off desconhecido {k!r}")
        return erros

    def para_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "metodo": self.metodo,
            "anomalia_detectada": self.anomalia_detectada,
            "janelas_anomalas": list(self.janelas_anomalas),
            "causa_feature": self.causa_feature,
            "regras_violadas": list(self.regras_violadas),
            "explicacao": [vars(p) for p in self.explicacao],
            "ajustes": [vars(a) for a in self.ajustes],
            "viavel": self.viavel,
            "tradeoffs": dict(self.tradeoffs),
        }
