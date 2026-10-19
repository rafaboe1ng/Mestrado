"""Modulo sensores: leitura e escrita da ``SerieMultivariada`` de um job e janelamento.

Formato em disco (uma pasta por job): ``serie.csv`` (t_s, canais...) e ``meta.json``
(job, produto, canais, taxa, parametros usados, operacoes). Quando os dados reais chegarem,
e aqui que entra o adaptador do log da impressora (docs/modulos/sensores.md).
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from contracts.base import garantir
from contracts.sensores import OperacaoJob, SerieMultivariada

__all__ = ["salvar", "carregar", "janelar", "operacao_em"]


def salvar(serie: SerieMultivariada, pasta: str | Path) -> Path:
    garantir(serie)
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    with open(pasta / "serie.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["t_s", *serie.canais])
        for ti, linha in zip(serie.t, serie.valores):
            w.writerow([f"{float(ti):.3f}", *[f"{float(x):.6f}" for x in linha]])
    meta = {
        "job_id": serie.job_id,
        "produto_id": serie.produto_id,
        "versao_design": serie.versao_design,
        "canais": list(serie.canais),
        "taxa_hz": serie.taxa_hz,
        "parametros_usados": dict(serie.parametros_usados),
        "operacoes": [vars(o) for o in serie.operacoes],
    }
    (pasta / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    return pasta


def carregar(pasta: str | Path) -> SerieMultivariada:
    pasta = Path(pasta)
    meta = json.loads((pasta / "meta.json").read_text(encoding="utf-8"))
    dados = np.loadtxt(pasta / "serie.csv", delimiter=",", skiprows=1, ndmin=2)
    serie = SerieMultivariada(
        job_id=meta["job_id"],
        produto_id=meta["produto_id"],
        versao_design=meta["versao_design"],
        canais=tuple(meta["canais"]),
        t=dados[:, 0],
        valores=dados[:, 1:],
        parametros_usados={k: float(v) for k, v in meta["parametros_usados"].items()},
        operacoes=tuple(OperacaoJob(**o) for o in meta["operacoes"]),
        taxa_hz=float(meta["taxa_hz"]),
    )
    garantir(serie)
    return serie


def janelar(serie: SerieMultivariada, largura_s: float) -> list[tuple[int, float, float, np.ndarray]]:
    """Janelas contiguas de ``largura_s`` a partir de t[0]: (indice, inicio, fim, indices das amostras)."""
    t0 = float(serie.t[0])
    n = int(round(serie.duracao_s / largura_s))
    saida = []
    for i in range(n):
        ini, fim = t0 + i * largura_s, t0 + (i + 1) * largura_s
        idx = np.nonzero((serie.t >= ini - 1e-9) & (serie.t < fim - 1e-9))[0]
        if idx.size:
            saida.append((len(saida), ini, fim, idx))
    return saida


def operacao_em(serie: SerieMultivariada, instante_s: float) -> OperacaoJob | None:
    for o in serie.operacoes:
        if o.inicio_s <= instante_s < o.fim_s:
            return o
    return None
