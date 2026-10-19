"""Modulo regimes: de ``SerieMultivariada`` para ``EstadosOperacionais``.

Metodo proposto: caracteristicas por janela (media, desvio e inclinacao de cada canal),
padronizacao, k-means (implementado aqui, sem dependencias) ajustado nos jobs de calibracao,
nomeacao dos clusters por heuristica declarada e anomalia por (a) pertencer ao cluster de
anomalia ou (b) distancia ao centroide acima do percentil de calibracao.
Baseline: limiar fixo sobre o desvio da vibracao por janela, calibrado nos mesmos jobs.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from contracts.base import garantir
from contracts.estados import EstadosOperacionais, Janela
from contracts.sensores import SerieMultivariada
from sensores import janelar

__all__ = ["caracteristicas", "kmeans", "ModeloRegimes", "ajustar", "aplicar", "calibrar_limiar", "baseline_limiar"]

ESTATISTICAS = ("media", "desvio", "inclinacao")


def caracteristicas(serie: SerieMultivariada, largura_s: float):
    """Por janela: media, desvio e inclinacao de cada canal. Retorna (janelas, X, nomes)."""
    janelas = janelar(serie, largura_s)
    linhas = []
    for _, _, _, idx in janelas:
        v = serie.valores[idx]
        t = serie.t[idx]
        feats: list[float] = []
        for c in range(v.shape[1]):
            x = v[:, c]
            if len(t) > 1 and np.ptp(t) > 0:
                incl = float(np.polyfit(t - t[0], x, 1)[0])
            else:
                incl = 0.0
            feats.extend([float(x.mean()), float(x.std()), incl])
        linhas.append(feats)
    nomes = [f"{c}_{e}" for c in serie.canais for e in ESTATISTICAS]
    X = np.asarray(linhas, dtype=float).reshape(len(janelas), -1)
    return janelas, X, nomes


def kmeans(X: np.ndarray, k: int, semente: int = 0, iteracoes: int = 100):
    """k-means com inicializacao k-means++ e semente fixa. Retorna (centroides, rotulos)."""
    X = np.asarray(X, dtype=float)
    n = len(X)
    if n < k:
        raise ValueError(f"k-means: {n} amostras para k={k}")
    rng = np.random.default_rng(semente)
    centros = [X[rng.integers(n)]]
    for _ in range(1, k):
        C = np.asarray(centros)
        d2 = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1).min(1)
        soma = d2.sum()
        prob = d2 / soma if soma > 0 else np.full(n, 1.0 / n)
        centros.append(X[rng.choice(n, p=prob)])
    C = np.asarray(centros, dtype=float).copy()
    rot = np.full(n, -1)
    for _ in range(iteracoes):
        d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1)
        novo = d.argmin(1)
        if np.array_equal(novo, rot):
            break
        rot = novo
        for j in range(k):
            m = rot == j
            C[j] = X[m].mean(0) if m.any() else X[d.min(1).argmax()]
    return C, rot


@dataclass
class ModeloRegimes:
    largura_s: float
    k: int
    semente: int
    canais: tuple[str, ...]
    nomes_carac: list[str]
    media: np.ndarray
    desvio: np.ndarray
    centroides: np.ndarray
    nomes_estado: dict[int, str]
    estado_anomalia: int | None
    limiar_distancia: float
    config: dict = field(default_factory=dict)


def _nomear(centro_orig: np.ndarray, nomes_carac: list[str], canal_temp: str, canal_vib: str, fator_anomalia: float):
    """Heuristica declarada: aquecimento = maior inclinacao de temperatura; resfriamento = inclinacao
    mais negativa; anomalia = maior desvio de vibracao entre os restantes, se for > fator x o menor."""
    k = len(centro_orig)
    nomes: dict[int, str] = {}
    restantes = set(range(k))
    estado_anomalia = None
    if f"{canal_temp}_inclinacao" in nomes_carac:
        incl = centro_orig[:, nomes_carac.index(f"{canal_temp}_inclinacao")]
        aq = int(np.argmax(incl))
        if incl[aq] > 0:
            nomes[aq] = "aquecimento"
            restantes.discard(aq)
            if restantes:
                rf = min(restantes, key=lambda j: incl[j])
                if incl[rf] < -0.1 * incl[aq]:
                    nomes[rf] = "resfriamento"
                    restantes.discard(rf)
    if f"{canal_vib}_desvio" in nomes_carac and len(restantes) >= 2:
        vib = centro_orig[:, nomes_carac.index(f"{canal_vib}_desvio")]
        an = max(restantes, key=lambda j: vib[j])
        outros = [vib[j] for j in restantes if j != an]
        if vib[an] > fator_anomalia * max(min(outros), 1e-9):
            estado_anomalia = an
            nomes[an] = "anomalia"
            restantes.discard(an)
    for n_, j in enumerate(sorted(restantes)):
        nomes[j] = "impressao" if n_ == 0 else f"impressao_{n_ + 1}"
    return nomes, estado_anomalia


def ajustar(series: list[SerieMultivariada], largura_s: float = 10.0, k: int = 4, semente: int = 0,
            canal_temperatura: str = "temperatura", canal_vibracao: str = "vibracao",
            fator_anomalia: float = 2.0, percentil_distancia: float = 99.0) -> ModeloRegimes:
    """Ajusta o modelo nos jobs de calibracao (nao supervisionado)."""
    if not series:
        raise ValueError("ajustar: nenhuma serie de calibracao")
    Xs, nomes, canais = [], None, None
    for s in series:
        _, X, nomes = caracteristicas(s, largura_s)
        Xs.append(X)
        canais = s.canais
    X = np.vstack(Xs)
    media = X.mean(0)
    desvio = X.std(0)
    desvio[desvio == 0] = 1.0
    Z = (X - media) / desvio
    C, rot = kmeans(Z, k, semente)
    centro_orig = C * desvio + media
    nomes_estado, est_an = _nomear(centro_orig, nomes, canal_temperatura, canal_vibracao, fator_anomalia)
    d = np.sqrt(((Z - C[rot]) ** 2).sum(1))
    limiar = float(np.percentile(d, percentil_distancia))
    config = {"largura_s": largura_s, "k": k, "semente": semente, "fator_anomalia": fator_anomalia,
              "percentil_distancia": percentil_distancia, "n_janelas_calibracao": int(len(X))}
    return ModeloRegimes(largura_s, k, semente, tuple(canais), list(nomes), media, desvio, C, nomes_estado, est_an, limiar, config)


def aplicar(modelo: ModeloRegimes, serie: SerieMultivariada) -> EstadosOperacionais:
    janelas, X, nomes = caracteristicas(serie, modelo.largura_s)
    if nomes != modelo.nomes_carac:
        raise ValueError("canais da serie diferem dos canais do modelo")
    Z = (X - modelo.media) / modelo.desvio
    d = np.sqrt(((Z[:, None, :] - modelo.centroides[None, :, :]) ** 2).sum(-1))
    rot = d.argmin(1)
    dmin = d.min(1)
    nomes_estado = dict(modelo.nomes_estado)
    fora = dmin > modelo.limiar_distancia
    if modelo.estado_anomalia is not None:
        anomalia = fora | (rot == modelo.estado_anomalia)
    else:
        anomalia = fora
        if fora.any():
            nomes_estado[modelo.k] = "fora_do_padrao"
            rot = np.where(fora, modelo.k, rot)
    jan = tuple(
        Janela(i, ini, fim, int(rot[n]), bool(anomalia[n]), float(dmin[n] / modelo.limiar_distancia) if modelo.limiar_distancia > 0 else 0.0)
        for n, (i, ini, fim, _) in enumerate(janelas)
    )
    trans = tuple((jan[n - 1].estado, jan[n].estado, jan[n].inicio_s) for n in range(1, len(jan)) if jan[n].estado != jan[n - 1].estado)
    centroides = tuple(tuple(float(x) for x in linha) for linha in (modelo.centroides * modelo.desvio + modelo.media))
    config = {**modelo.config, "limiar_distancia": modelo.limiar_distancia, "estado_anomalia": modelo.estado_anomalia}
    est = EstadosOperacionais(serie.job_id, jan, nomes_estado, centroides, trans, "kmeans_janelas", config)
    garantir(est)
    return est


def calibrar_limiar(series: list[SerieMultivariada], largura_s: float = 10.0, canal_vibracao: str = "vibracao",
                    n_desvios: float = 3.0, robusto: bool = True) -> float:
    """Baseline: limiar sobre o desvio-padrao da vibracao por janela, calibrado nos jobs de calibracao.

    ``robusto=True`` usa mediana + n * MAD (escalado), que nao e inflado pelas janelas anomalas presentes
    na calibracao. ``robusto=False`` usa media + n desvios (primeira execucao do exp01; ver docs/modulos/regimes.md).
    """
    vals = []
    for s in series:
        _, X, nomes = caracteristicas(s, largura_s)
        vals.append(X[:, nomes.index(f"{canal_vibracao}_desvio")])
    v = np.concatenate(vals)
    if robusto:
        med = float(np.median(v))
        mad = 1.4826 * float(np.median(np.abs(v - med)))
        return med + n_desvios * mad
    return float(v.mean() + n_desvios * v.std())


def baseline_limiar(serie: SerieMultivariada, largura_s: float, limiar_vibracao: float,
                    canal_vibracao: str = "vibracao", canal_temperatura: str = "temperatura",
                    inclinacao_aquecimento: float = 0.5) -> EstadosOperacionais:
    """Baseline: anomalia se o desvio da vibracao na janela passa do limiar; estados por inclinacao de temperatura."""
    janelas, X, nomes = caracteristicas(serie, largura_s)
    vib = X[:, nomes.index(f"{canal_vibracao}_desvio")]
    incl = X[:, nomes.index(f"{canal_temperatura}_inclinacao")]
    nomes_estado = {0: "aquecimento", 1: "impressao", 2: "anomalia", 3: "resfriamento"}
    jan = []
    for n, (i, ini, fim, _) in enumerate(janelas):
        if vib[n] > limiar_vibracao:
            estado, anom = 2, True
        elif incl[n] > inclinacao_aquecimento:
            estado, anom = 0, False
        elif incl[n] < -inclinacao_aquecimento:
            estado, anom = 3, False
        else:
            estado, anom = 1, False
        jan.append(Janela(i, ini, fim, estado, anom, float(vib[n] / limiar_vibracao) if limiar_vibracao > 0 else 0.0))
    jan_t = tuple(jan)
    trans = tuple((jan_t[n - 1].estado, jan_t[n].estado, jan_t[n].inicio_s) for n in range(1, len(jan_t)) if jan_t[n].estado != jan_t[n - 1].estado)
    est = EstadosOperacionais(serie.job_id, jan_t, nomes_estado, (), trans, "baseline_limiar_vibracao",
                              {"largura_s": largura_s, "limiar_vibracao": limiar_vibracao, "inclinacao_aquecimento": inclinacao_aquecimento})
    garantir(est)
    return est
