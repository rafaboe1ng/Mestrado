"""Modulo cad_features: do design do produto para ``ProdutoFeatures``.

Hoje le e escreve uma *ficha* JSON de features (escrita a mao ou exportada do CAD) e gera
variacoes de design a partir dela. A extracao automatica de STEP/STL esta pendente
(``extrair_de_malha`` levanta NotImplementedError; ver docs/modulos/cad_features.md).
"""
from __future__ import annotations

import json
from pathlib import Path

from contracts.base import garantir
from contracts.produto import Feature, ProdutoFeatures

__all__ = ["ficha_exemplo", "carregar_ficha", "salvar_ficha", "variar", "extrair_de_malha"]


def ficha_exemplo(versao: str = "v1", espessura_parede_mm: float = 2.0, angulo_aba_graus: float = 30.0) -> ProdutoFeatures:
    """Suporte em L usado na bateria sintetica: base, parede, dois furos, nervura e aba."""
    feats = (
        Feature("base", "base", {"comprimento_mm": 60.0, "largura_mm": 40.0, "espessura_mm": 3.0}, ("parede", "furo_a", "nervura")),
        Feature("parede", "parede", {"altura_mm": 30.0, "espessura_mm": float(espessura_parede_mm)}, ("base", "nervura", "furo_b", "aba")),
        Feature("furo_a", "furo", {"diametro_mm": 5.0}, ("base",)),
        Feature("nervura", "nervura", {"espessura_mm": 1.5, "altura_mm": 10.0}, ("base", "parede")),
        Feature("furo_b", "furo", {"diametro_mm": 4.0}, ("parede",)),
        Feature("aba", "aba", {"comprimento_mm": 15.0, "angulo_graus": float(angulo_aba_graus), "espessura_mm": 2.0}, ("parede",)),
    )
    produto = ProdutoFeatures("suporte_L", versao, feats, origem="ficha_exemplo")
    garantir(produto)
    return produto


def carregar_ficha(caminho: str | Path) -> ProdutoFeatures:
    d = json.loads(Path(caminho).read_text(encoding="utf-8"))
    produto = ProdutoFeatures.de_dict(d)
    garantir(produto)
    return produto


def salvar_ficha(produto: ProdutoFeatures, caminho: str | Path) -> Path:
    garantir(produto)
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(produto.para_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
    return caminho


def variar(produto: ProdutoFeatures, feature_id: str, nova_versao: str, **dimensoes: float) -> ProdutoFeatures:
    """Nova versao do design alterando dimensoes de uma feature (o 'delta de design')."""
    if feature_id not in produto.por_id():
        raise KeyError(f"feature {feature_id!r} nao existe em {produto.produto_id}")
    novas = []
    for f in produto.features:
        if f.id == feature_id:
            dims = dict(f.dimensoes)
            dims.update({k: float(v) for k, v in dimensoes.items()})
            novas.append(Feature(f.id, f.tipo, dims, f.adjacentes))
        else:
            novas.append(f)
    novo = ProdutoFeatures(produto.produto_id, nova_versao, tuple(novas), origem=produto.origem)
    garantir(novo)
    return novo


def extrair_de_malha(caminho_stl: str | Path) -> ProdutoFeatures:
    """Pendente: extrair features a partir de malha/STEP. Ver docs/modulos/cad_features.md."""
    raise NotImplementedError("extracao automatica de features ainda nao implementada; use uma ficha JSON")
