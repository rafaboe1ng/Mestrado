"""Gerador da bateria sintetica com gabarito fixado.

Simula jobs de impressao FDM de um suporte em L com variacoes de design (espessura da parede,
angulo da aba) e de parametros (temperatura, velocidade, resfriamento). Quando o job viola uma
regra da base de processo, a peca "empena" ou "oscila" no trecho em que aquela feature e
impressa, com probabilidade alta; isso aparece como pico de vibracao e ondulacao de corrente.
Ha tambem anomalias espontaneas (sem causa de design) com probabilidade baixa.

O gabarito registra, por job: janelas (estado e anomalia), regras violadas, causa (feature) e
anomalias injetadas. E deterministico para a semente; depois de gerado, nao se altera
(CONTRIBUTING, regra 6). O aviso de circularidade esta no PLANO (P3).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from cad_features import ficha_exemplo, salvar_ficha
from contracts.sensores import OperacaoJob, SerieMultivariada
from processo import base_fdm_pla, violacoes
from sensores import salvar

SEMENTE = 20261019
DATA_FIXACAO = "2026-10-19"
TAXA_HZ = 2.0
DURACAO_S = 600.0
LARGURA_JANELA_S = 10.0
CANAIS = ("temperatura", "corrente", "vibracao")
FASES = (
    ("aquecimento", 0.0, 60.0, None),
    ("base", 60.0, 260.0, "base"),
    ("parede", 260.0, 460.0, "parede"),
    ("aba", 460.0, 560.0, "aba"),
    ("resfriamento", 560.0, 600.0, None),
)
ESPESSURAS = (0.6, 0.8, 1.0, 1.2, 1.6, 2.0, 3.0)
ANGULOS = (30.0, 45.0, 60.0, 70.0)
VELOCIDADES = (35.0, 45.0, 60.0, 80.0)
RESFRIAMENTOS = (40.0, 60.0, 100.0)
TEMPERATURAS = (200.0, 210.0, 220.0)

README = f"""# Bateria sintetica

Gerada por `python -m dados.sintetico.gerador` com semente {SEMENTE}. Gabarito fixado em {DATA_FIXACAO}.
Nao editar `gabarito.json` nem os casos a mao. Se o gerador mudar, a bateria muda de hash e a proxima
execucao do experimento volta a contar como "primeira execucao" (ver `experimentos/proveniencia.py`).

Circularidade (PLANO, P3): a anomalia e injetada como pico de vibracao e ondulacao de corrente, que e
o que os metodos procuram. Esta bateria prova que o pipeline fecha; nao prova o metodo na impressora.
"""


def _fase_em(t: float) -> str:
    for nome, ini, fim, _ in FASES:
        if ini <= t < fim:
            return nome
    return FASES[-1][0]


def simular_sinais(rng: np.random.Generator, params: dict[str, float], anomalias: list[tuple]) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(0.0, DURACAO_S, 1.0 / TAXA_HZ)
    T_set, v = params["temp_bico"], params["velocidade"]
    temp = np.empty_like(t)
    cor = np.empty_like(t)
    vib = np.empty_like(t)
    for i, ti in enumerate(t):
        fase = _fase_em(ti)
        if fase == "aquecimento":
            temp[i] = 25.0 + (T_set - 25.0) * (1.0 - np.exp(-ti / 15.0))
            cor[i], vib[i] = 0.3, 0.02
        elif fase == "resfriamento":
            temp[i] = 25.0 + (T_set - 25.0) * np.exp(-(ti - 560.0) / 40.0)
            cor[i], vib[i] = 0.2, 0.02
        else:
            temp[i] = T_set + 0.8 * np.sin(2 * np.pi * ti / 90.0)
            cor[i] = 0.8 + 0.004 * v
            vib[i] = 0.05 + 0.0005 * v
    temp = temp + rng.normal(0.0, 0.5, t.size)
    cor = cor + rng.normal(0.0, 0.05, t.size)
    vib = vib + rng.normal(0.0, 0.01, t.size)
    for ini, fim, _, tipo in anomalias:
        m = (t >= ini) & (t < fim)
        cor[m] += 0.15 * np.sin(2 * np.pi * 0.4 * t[m]) + rng.normal(0.0, 0.08, int(m.sum()))
        vib[m] += 0.12 + np.abs(rng.normal(0.0, 0.04, int(m.sum())))
        if tipo == "empeno_aba":
            temp[m] += rng.normal(0.0, 1.0, int(m.sum()))
    vib = np.clip(vib, 0.0, None)
    return t, np.column_stack([temp, cor, vib])


def gerar_job(rng: np.random.Generator, numero: int, conjunto: str, base):
    esp = float(rng.choice(ESPESSURAS))
    ang = float(rng.choice(ANGULOS))
    produto = ficha_exemplo(versao=f"v{numero:03d}", espessura_parede_mm=esp, angulo_aba_graus=ang)
    params = {
        "temp_bico": float(rng.choice(TEMPERATURAS)),
        "velocidade": float(rng.choice(VELOCIDADES)),
        "altura_camada": 0.2,
        "resfriamento": float(rng.choice(RESFRIAMENTOS)),
        "fluxo": 100.0,
        "retracao": 5.0,
    }
    viol = violacoes(base, produto, params)
    anomalias: list[tuple] = []
    if any(v.feature.id == "parede" for v in viol) and rng.random() < 0.9:
        anomalias.append((300.0, 420.0, "parede", "oscilacao_parede"))
    if any(v.feature.id == "aba" for v in viol) and rng.random() < 0.85:
        anomalias.append((490.0, 550.0, "aba", "empeno_aba"))
    if not anomalias and rng.random() < 0.08:
        ini = float(rng.choice([120.0, 180.0, 340.0]))
        anomalias.append((ini, ini + 40.0, None, "espontanea"))
    t, X = simular_sinais(rng, params, anomalias)
    operacoes = tuple(OperacaoJob(f"op{k}_{nome}", feat, ini, fim, f"fase {nome}") for k, (nome, ini, fim, feat) in enumerate(FASES))
    job_id = f"job_{numero:03d}"
    serie = SerieMultivariada(job_id, produto.produto_id, produto.versao_design, CANAIS, t, X, params, operacoes, TAXA_HZ)
    janelas = []
    for i in range(int(DURACAO_S / LARGURA_JANELA_S)):
        ini, fim = i * LARGURA_JANELA_S, (i + 1) * LARGURA_JANELA_S
        anom = any(a_ini <= ini and fim <= a_fim for a_ini, a_fim, _, _ in anomalias)
        fase = _fase_em(ini)
        nome = "anomalia" if anom else ("impressao" if fase in ("base", "parede", "aba") else fase)
        janelas.append({"indice": i, "inicio_s": ini, "fim_s": fim, "estado": nome, "anomalia": anom})
    gab = {
        "job_id": job_id,
        "conjunto": conjunto,
        "produto_id": produto.produto_id,
        "versao_design": produto.versao_design,
        "parametros_usados": params,
        "regras_violadas": sorted({v.regra.id for v in viol}),
        "causa_feature": anomalias[0][2] if anomalias else None,
        "anomalias": [{"inicio_s": a, "fim_s": b, "feature": f, "tipo": tp} for a, b, f, tp in anomalias],
        "largura_janela_s": LARGURA_JANELA_S,
        "janelas": janelas,
    }
    return produto, serie, gab


def gerar_bateria(destino: str | Path = "dados/sintetico", n_jobs: int = 24, n_calibracao: int = 8, semente: int = SEMENTE) -> dict:
    rng = np.random.default_rng(semente)
    base = base_fdm_pla()
    destino = Path(destino)
    (destino / "casos").mkdir(parents=True, exist_ok=True)
    (destino / "fichas").mkdir(parents=True, exist_ok=True)
    gabarito: dict = {}
    bateria: dict = {"semente": semente, "n_jobs": n_jobs, "n_calibracao": n_calibracao, "largura_janela_s": LARGURA_JANELA_S, "jobs": {}}
    for n in range(1, n_jobs + 1):
        conjunto = "calibracao" if n <= n_calibracao else "avaliacao"
        produto, serie, gab = gerar_job(rng, n, conjunto, base)
        ficha = destino / "fichas" / f"{produto.produto_id}@{produto.versao_design}.json"
        salvar_ficha(produto, ficha)
        salvar(serie, destino / "casos" / serie.job_id)
        gabarito[serie.job_id] = gab
        bateria["jobs"][serie.job_id] = {"conjunto": conjunto, "ficha": f"fichas/{ficha.name}", "caso": f"casos/{serie.job_id}"}
    (destino / "gabarito.json").write_text(json.dumps(gabarito, indent=2, ensure_ascii=False), encoding="utf-8")
    (destino / "bateria.json").write_text(json.dumps(bateria, indent=2, ensure_ascii=False), encoding="utf-8")
    (destino / "README.md").write_text(README, encoding="utf-8")
    return bateria


def main() -> None:
    ap = argparse.ArgumentParser(description="gera a bateria sintetica com gabarito")
    ap.add_argument("--destino", default="dados/sintetico")
    ap.add_argument("--n-jobs", type=int, default=24)
    ap.add_argument("--n-calibracao", type=int, default=8)
    ap.add_argument("--semente", type=int, default=SEMENTE)
    args = ap.parse_args()
    b = gerar_bateria(args.destino, args.n_jobs, args.n_calibracao, args.semente)
    gab = json.loads((Path(args.destino) / "gabarito.json").read_text(encoding="utf-8"))
    com_anomalia = sum(1 for g in gab.values() if any(j["anomalia"] for j in g["janelas"]))
    print(f"bateria: {b['n_jobs']} jobs ({b['n_calibracao']} calibracao), {com_anomalia} com anomalia, destino={args.destino}")


if __name__ == "__main__":
    main()
