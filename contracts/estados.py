"""Fronteira regimes -> grafo / avaliacao: estados operacionais por janela de tempo.

O que passa: janelas contiguas e ordenadas, cada uma com um estado nomeado, a marca de
anomalia e um score finito; o metodo que produziu. O que nao passa: janelas com buraco
ou sobreposicao, estado sem nome, score NaN, metodo vazio.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Janela:
    indice: int
    inicio_s: float
    fim_s: float
    estado: int
    anomalia: bool
    score: float = 0.0


@dataclass(frozen=True)
class EstadosOperacionais:
    job_id: str
    janelas: tuple[Janela, ...]
    nomes_estado: dict[int, str]
    centroides: tuple[tuple[float, ...], ...] = ()
    transicoes: tuple[tuple[int, int, float], ...] = ()
    metodo: str = ""
    config: dict = field(default_factory=dict)

    def validar(self) -> list[str]:
        erros: list[str] = []
        if not self.job_id:
            erros.append("job_id vazio")
        if not self.metodo:
            erros.append("metodo vazio")
        if not self.janelas:
            erros.append("sem janelas")
        anterior: Janela | None = None
        for i, j in enumerate(self.janelas):
            if j.indice != i:
                erros.append(f"janela {i}: indice {j.indice} fora de ordem")
            if not j.fim_s > j.inicio_s:
                erros.append(f"janela {i}: fim <= inicio")
            if anterior is not None and abs(j.inicio_s - anterior.fim_s) > 1e-6:
                erros.append(f"janela {i}: nao e contigua a anterior")
            if j.estado not in self.nomes_estado:
                erros.append(f"janela {i}: estado {j.estado} sem nome")
            if not math.isfinite(j.score):
                erros.append(f"janela {i}: score nao finito")
            anterior = j
        return erros

    def indices_anomalos(self) -> tuple[int, ...]:
        return tuple(j.indice for j in self.janelas if j.anomalia)

    def rotulos(self) -> list[int]:
        return [j.estado for j in self.janelas]
