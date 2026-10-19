"""Fronteira sensores -> regimes / grafo: a serie temporal multivariada de um job.

O que passa: tempo estritamente crescente, matriz (n, canais) finita e alinhada ao tempo,
parametros usados nao vazios, operacoes do job (o que a maquina executava em cada trecho)
dentro da duracao. O que nao passa: NaN, tempo fora de ordem, canal sem nome, operacao
fora da janela de tempo ou com inicio >= fim.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class OperacaoJob:
    """Trecho do job em que a maquina executava uma operacao (vem do log/fatiador)."""

    id: str
    feature_id: str | None
    inicio_s: float
    fim_s: float
    descricao: str = ""


@dataclass
class SerieMultivariada:
    job_id: str
    produto_id: str
    versao_design: str
    canais: tuple[str, ...]
    t: np.ndarray
    valores: np.ndarray
    parametros_usados: dict[str, float]
    operacoes: tuple[OperacaoJob, ...]
    taxa_hz: float

    @property
    def duracao_s(self) -> float:
        return float(len(self.t) / self.taxa_hz) if self.taxa_hz > 0 else 0.0

    def validar(self) -> list[str]:
        erros: list[str] = []
        if not self.job_id:
            erros.append("job_id vazio")
        if not self.canais or any(not c for c in self.canais):
            erros.append("canais vazios ou sem nome")
        if len(set(self.canais)) != len(self.canais):
            erros.append("canais com nome repetido")
        if self.taxa_hz <= 0:
            erros.append("taxa_hz deve ser > 0")
        t = np.asarray(self.t)
        v = np.asarray(self.valores)
        if t.ndim != 1 or len(t) < 2:
            erros.append("t deve ser vetor com pelo menos 2 amostras")
        elif not np.all(np.diff(t) > 0):
            erros.append("t nao e estritamente crescente")
        if v.ndim != 2 or v.shape[0] != t.shape[0]:
            erros.append("valores deve ter forma (n, canais) alinhada a t")
        elif v.shape[1] != len(self.canais):
            erros.append("numero de colunas difere do numero de canais")
        if v.size and not np.all(np.isfinite(v)):
            erros.append("valores com NaN ou inf")
        if not self.parametros_usados:
            erros.append("parametros_usados vazio")
        ids = [o.id for o in self.operacoes]
        if len(ids) != len(set(ids)):
            erros.append("operacoes com id repetido")
        if t.ndim == 1 and len(t) >= 2 and self.taxa_hz > 0:
            t0, tf = float(t[0]), float(t[0]) + self.duracao_s + 1e-6
            for o in self.operacoes:
                if not o.inicio_s < o.fim_s:
                    erros.append(f"operacao {o.id}: inicio >= fim")
                if o.inicio_s < t0 - 1e-6 or o.fim_s > tf:
                    erros.append(f"operacao {o.id}: fora da duracao da serie")
        return erros
