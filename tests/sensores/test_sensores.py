import numpy as np
import pytest

from sensores import carregar, janelar, operacao_em, salvar

pytestmark = pytest.mark.sensores


def test_salvar_e_carregar(tmp_path, job_limpo):
    _, serie, _ = job_limpo
    pasta = salvar(serie, tmp_path / "job")
    lida = carregar(pasta)
    assert lida.job_id == serie.job_id and lida.canais == serie.canais
    assert lida.parametros_usados == serie.parametros_usados
    assert lida.operacoes == serie.operacoes
    assert np.allclose(lida.valores, serie.valores, atol=1e-5)


def test_janelar_cobre_a_serie(job_limpo):
    _, serie, _ = job_limpo
    jan = janelar(serie, 10.0)
    assert len(jan) == 60
    assert jan[0][1] == 0.0 and jan[-1][2] == 600.0
    assert sum(len(idx) for *_, idx in jan) == len(serie.t)


def test_operacao_em(job_limpo):
    _, serie, _ = job_limpo
    assert operacao_em(serie, 300.0).feature_id == "parede"
    assert operacao_em(serie, 10.0).feature_id is None
    assert operacao_em(serie, 999.0) is None
