import numpy as np
import pytest

from regimes import ajustar, aplicar, baseline_limiar, calibrar_limiar, caracteristicas, kmeans

pytestmark = pytest.mark.regimes


def test_caracteristicas_forma_e_nomes(job_limpo):
    _, serie, _ = job_limpo
    janelas, X, nomes = caracteristicas(serie, 10.0)
    assert X.shape == (60, 9) and len(janelas) == 60
    assert nomes[:3] == ["temperatura_media", "temperatura_desvio", "temperatura_inclinacao"]


def test_kmeans_deterministico():
    rng = np.random.default_rng(0)
    X = np.vstack([rng.normal(0, 0.1, (20, 2)), rng.normal(5, 0.1, (20, 2))])
    C1, r1 = kmeans(X, 2, semente=3)
    C2, r2 = kmeans(X, 2, semente=3)
    assert np.array_equal(r1, r2) and C1.shape == (2, 2)
    assert len(set(r1[:20])) == 1 and len(set(r1[20:])) == 1 and r1[0] != r1[-1]
    with pytest.raises(ValueError):
        kmeans(X[:1], 2)


def test_ajustar_aplicar_detecta_mais_no_job_anomalo(job_fino, job_limpo, job_espontaneo):
    series = [job_fino[1], job_limpo[1], job_espontaneo[1]]
    modelo = ajustar(series, largura_s=10.0, k=4, semente=0)
    assert set(modelo.nomes_estado.values()) >= {"aquecimento"}
    est_fino = aplicar(modelo, job_fino[1])
    est_limpo = aplicar(modelo, job_limpo[1])
    assert est_fino.validar() == [] and est_limpo.validar() == []
    assert len(est_fino.janelas) == 60
    assert len(est_fino.indices_anomalos()) > len(est_limpo.indices_anomalos())
    # a maior parte das janelas anomalas detectadas deve cair no trecho injetado (300-420 s = janelas 30..41)
    dentro = [i for i in est_fino.indices_anomalos() if 30 <= i <= 41]
    assert len(dentro) >= len(est_fino.indices_anomalos()) / 2


def test_baseline_limiar(job_fino, job_limpo):
    limiar = calibrar_limiar([job_limpo[1]], 10.0, n_desvios=3.0, robusto=False)
    est_fino = baseline_limiar(job_fino[1], 10.0, limiar)
    est_limpo = baseline_limiar(job_limpo[1], 10.0, limiar)
    assert est_fino.validar() == [] and est_fino.metodo == "baseline_limiar_vibracao"
    assert len(est_fino.indices_anomalos()) > len(est_limpo.indices_anomalos())


def test_limiar_robusto_nao_e_inflado_pelas_anomalias(job_fino, job_limpo):
    # calibrando num conjunto que contem o job anomalo, media+3sd sobe; mediana+3MAD quase nao muda
    classico = calibrar_limiar([job_fino[1], job_limpo[1]], 10.0, robusto=False)
    robusto = calibrar_limiar([job_fino[1], job_limpo[1]], 10.0, robusto=True)
    so_limpo = calibrar_limiar([job_limpo[1]], 10.0, robusto=True)
    assert robusto < classico
    assert abs(robusto - so_limpo) < abs(classico - so_limpo)
    detectadas = baseline_limiar(job_fino[1], 10.0, robusto).indices_anomalos()
    assert sum(1 for i in detectadas if 30 <= i <= 41) >= 10
