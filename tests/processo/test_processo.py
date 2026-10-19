import pytest

from cad_features import ficha_exemplo
from processo import carregar_base, regras_aplicaveis, salvar_base, violacoes

pytestmark = pytest.mark.processo


def test_base_valida(base):
    assert base.validar() == []
    assert {r.id for r in base.regras} == {"R1", "R2", "R3", "R4", "R5"}


def test_regras_aplicaveis_dependem_da_geometria(base):
    fino = ficha_exemplo("f", espessura_parede_mm=0.8, angulo_aba_graus=30)
    ids = {(r.id, f.id) for r, f in regras_aplicaveis(base, fino)}
    assert ("R1", "parede") in ids and ("R2", "parede") in ids
    assert not any(r == "R3" for r, _ in ids)
    grosso = ficha_exemplo("g", espessura_parede_mm=2.0, angulo_aba_graus=70)
    ids_g = {(r.id, f.id) for r, f in regras_aplicaveis(base, grosso)}
    assert ("R3", "aba") in ids_g and not any(f == "parede" for _, f in ids_g)


def test_violacoes(base, params_padrao):
    fino = ficha_exemplo("f", espessura_parede_mm=0.8)
    assert violacoes(base, fino, params_padrao) == []  # 45 mm/s e 100 % respeitam R1 e R2
    v = violacoes(base, fino, {**params_padrao, "velocidade": 60.0})
    assert [x.regra.id for x in v] == ["R1"] and v[0].valor_usado == 60.0


def test_salvar_e_carregar_base(tmp_path, base):
    caminho = salvar_base(base, tmp_path / "base.json")
    assert carregar_base(caminho) == base
