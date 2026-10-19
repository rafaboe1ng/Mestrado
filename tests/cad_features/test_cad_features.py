import pytest

from cad_features import carregar_ficha, extrair_de_malha, ficha_exemplo, salvar_ficha, variar

pytestmark = pytest.mark.cad_features


def test_ficha_exemplo_valida(produto):
    assert produto.validar() == []
    assert {f.tipo for f in produto.features} >= {"base", "parede", "furo", "nervura", "aba"}


def test_variar_cria_nova_versao_sem_alterar_original(produto):
    novo = variar(produto, "parede", "v2", espessura_mm=0.8)
    assert novo.versao_design == "v2"
    assert novo.por_id()["parede"].dimensoes["espessura_mm"] == 0.8
    assert produto.por_id()["parede"].dimensoes["espessura_mm"] == 2.0
    with pytest.raises(KeyError):
        variar(produto, "inexistente", "v3", x=1)


def test_salvar_e_carregar_ficha(tmp_path, produto):
    caminho = salvar_ficha(produto, tmp_path / "ficha.json")
    lido = carregar_ficha(caminho)
    assert lido == produto


def test_extracao_de_malha_pendente():
    with pytest.raises(NotImplementedError):
        extrair_de_malha("peca.stl")
