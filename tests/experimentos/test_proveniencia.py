import json

import pytest

from experimentos.proveniencia import hash_dados, registrar, ultimo_resultado

pytestmark = pytest.mark.experimentos


def test_registrar_grava_proveniencia(tmp_path):
    dados = tmp_path / "dados"
    dados.mkdir()
    (dados / "a.txt").write_text("1", encoding="utf-8")
    p1 = registrar("exp_teste", {"x": 1.0}, comando="cmd", dados=[dados], pasta=tmp_path / "res")
    reg = json.loads(p1.read_text(encoding="utf-8"))
    for chave in ("experimento", "executado_em", "comando", "git", "versoes", "dados", "execucao_numero_para_estes_dados", "vale_como_fora_da_amostra", "resultado"):
        assert chave in reg
    assert reg["execucao_numero_para_estes_dados"] == 1 and reg["vale_como_fora_da_amostra"] is True
    assert reg["dados"]["n_arquivos"] == 1 and reg["resultado"] == {"x": 1.0}
    import time
    time.sleep(1.1)  # nome do arquivo tem resolucao de segundo
    p2 = registrar("exp_teste", {"x": 2.0}, comando="cmd", dados=[dados], pasta=tmp_path / "res")
    reg2 = json.loads(p2.read_text(encoding="utf-8"))
    assert reg2["execucao_numero_para_estes_dados"] == 2 and reg2["vale_como_fora_da_amostra"] is False
    assert ultimo_resultado("exp_teste", tmp_path / "res")["resultado"] == {"x": 2.0}


def test_hash_dados_muda_com_o_conteudo(tmp_path):
    f = tmp_path / "d.csv"
    f.write_text("a", encoding="utf-8")
    h1 = hash_dados([f])["sha256"]
    assert h1 == hash_dados([f])["sha256"]
    f.write_text("b", encoding="utf-8")
    assert hash_dados([f])["sha256"] != h1
