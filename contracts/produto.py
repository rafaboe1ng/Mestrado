"""Fronteira cad_features -> grafo: o produto como conjunto de features geometricas.

O que passa: features com tipo conhecido, dimensoes positivas e adjacencias que apontam
para features existentes. O que nao passa: ids repetidos, tipos fora do vocabulario,
dimensoes nulas ou negativas, adjacencia para feature inexistente.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TIPOS_FEATURE = ("base", "parede", "furo", "nervura", "aba", "outro")


@dataclass(frozen=True)
class Feature:
    id: str
    tipo: str
    dimensoes: dict[str, float] = field(default_factory=dict)
    adjacentes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProdutoFeatures:
    produto_id: str
    versao_design: str
    features: tuple[Feature, ...]
    origem: str = "ficha_json"

    def por_id(self) -> dict[str, Feature]:
        return {f.id: f for f in self.features}

    def validar(self) -> list[str]:
        erros: list[str] = []
        if not self.produto_id:
            erros.append("produto_id vazio")
        if not self.versao_design:
            erros.append("versao_design vazia")
        if not self.features:
            erros.append("produto sem features")
        ids = [f.id for f in self.features]
        if len(ids) != len(set(ids)):
            erros.append("ids de feature repetidos")
        for f in self.features:
            if f.tipo not in TIPOS_FEATURE:
                erros.append(f"feature {f.id}: tipo desconhecido {f.tipo!r}")
            for k, v in f.dimensoes.items():
                if isinstance(v, bool) or not isinstance(v, (int, float)) or not v > 0:
                    erros.append(f"feature {f.id}: dimensao {k!r} deve ser numero > 0")
            for a in f.adjacentes:
                if a == f.id:
                    erros.append(f"feature {f.id}: adjacente a si mesma")
                elif a not in ids:
                    erros.append(f"feature {f.id}: adjacente {a!r} nao existe")
        return erros

    def para_dict(self) -> dict[str, Any]:
        return {
            "produto_id": self.produto_id,
            "versao_design": self.versao_design,
            "origem": self.origem,
            "features": [
                {"id": f.id, "tipo": f.tipo, "dimensoes": dict(f.dimensoes), "adjacentes": list(f.adjacentes)}
                for f in self.features
            ],
        }

    @classmethod
    def de_dict(cls, d: dict[str, Any]) -> "ProdutoFeatures":
        feats = tuple(
            Feature(x["id"], x["tipo"], dict(x.get("dimensoes", {})), tuple(x.get("adjacentes", ())))
            for x in d["features"]
        )
        return cls(d["produto_id"], d["versao_design"], feats, d.get("origem", "ficha_json"))
