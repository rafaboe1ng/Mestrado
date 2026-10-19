"""Fixtures pequenas e deterministicas. Nada aqui depende de dados/sintetico/ versionado:
cada fixture constroi o que precisa a partir do gerador com semente fixa."""
from __future__ import annotations

import numpy as np
import pytest

from cad_features import ficha_exemplo
from contracts.estados import EstadosOperacionais, Janela
from contracts.sensores import OperacaoJob, SerieMultivariada
from dados.sintetico.gerador import CANAIS, FASES, LARGURA_JANELA_S, TAXA_HZ, gerar_bateria, simular_sinais
from processo import base_fdm_pla


def serie_de(produto, params: dict, anomalias: list[tuple], job_id: str, semente: int = 1) -> SerieMultivariada:
    rng = np.random.default_rng(semente)
    t, X = simular_sinais(rng, params, anomalias)
    ops = tuple(OperacaoJob(f"op{k}_{nome}", feat, ini, fim, f"fase {nome}") for k, (nome, ini, fim, feat) in enumerate(FASES))
    return SerieMultivariada(job_id, produto.produto_id, produto.versao_design, CANAIS, t, X, dict(params), ops, TAXA_HZ)


def estados_gabarito(job_id: str, anomalias: list[tuple]) -> EstadosOperacionais:
    """Estados 'perfeitos' (como o gabarito), para isolar o raciocinio do modulo de regimes."""
    nomes = {0: "aquecimento", 1: "impressao", 2: "anomalia", 3: "resfriamento"}
    jan = []
    n = int(600.0 / LARGURA_JANELA_S)
    for i in range(n):
        ini, fim = i * LARGURA_JANELA_S, (i + 1) * LARGURA_JANELA_S
        anom = any(a <= ini and fim <= b for a, b, _, _ in anomalias)
        if anom:
            estado = 2
        elif ini < 60:
            estado = 0
        elif ini >= 560:
            estado = 3
        else:
            estado = 1
        jan.append(Janela(i, ini, fim, estado, anom, 1.5 if anom else 0.3))
    return EstadosOperacionais(job_id, tuple(jan), nomes, metodo="gabarito_teste")


@pytest.fixture
def base():
    return base_fdm_pla()


@pytest.fixture
def produto():
    return ficha_exemplo()


@pytest.fixture
def params_padrao():
    return {"temp_bico": 210.0, "velocidade": 45.0, "altura_camada": 0.2, "resfriamento": 100.0, "fluxo": 100.0, "retracao": 5.0}


@pytest.fixture
def job_fino(params_padrao):
    """Parede fina (0.8 mm) impressa a 80 mm/s com resfriamento 40 %: viola R1 e R2; anomalia na parede."""
    produto = ficha_exemplo("vfino", espessura_parede_mm=0.8, angulo_aba_graus=30.0)
    params = {**params_padrao, "velocidade": 80.0, "resfriamento": 40.0}
    anomalias = [(300.0, 420.0, "parede", "oscilacao_parede")]
    return produto, serie_de(produto, params, anomalias, "job_fino", 11), anomalias


@pytest.fixture
def job_limpo(params_padrao):
    produto = ficha_exemplo("vlimpo", espessura_parede_mm=2.0, angulo_aba_graus=30.0)
    return produto, serie_de(produto, params_padrao, [], "job_limpo", 12), []


@pytest.fixture
def job_espontaneo(params_padrao):
    """Anomalia na base, sem regra violada: a causa correta e 'nenhuma'."""
    produto = ficha_exemplo("vesp", espessura_parede_mm=2.0, angulo_aba_graus=30.0)
    anomalias = [(120.0, 160.0, None, "espontanea")]
    return produto, serie_de(produto, params_padrao, anomalias, "job_esp", 13), anomalias


@pytest.fixture(scope="session")
def bateria_mini(tmp_path_factory):
    destino = tmp_path_factory.mktemp("bateria")
    gerar_bateria(destino, n_jobs=8, n_calibracao=4, semente=7)
    return destino
