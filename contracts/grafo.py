"""Fronteira grafo -> raciocinio: o grafo de conhecimento.

Vocabulario fechado de tipos de no e de relacoes, com dominio e contradominio. Toda aresta
carrega ``proveniencia`` (de onde veio: ficha de CAD, regra de processo, meta do job, metodo
de regimes). O que nao passa: tipo ou relacao fora do vocabulario, aresta entre tipos nao
permitidos, aresta para no inexistente, proveniencia vazia.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TIPOS_NO = ("produto", "feature", "parametro", "objetivo", "regra", "job", "operacao", "estado", "maquina")

# relacao -> pares (tipo_origem, tipo_destino) permitidos
RELACOES: dict[str, tuple[tuple[str, str], ...]] = {
    "tem_feature": (("produto", "feature"),),
    "adjacente_a": (("feature", "feature"),),
    "requer": (("feature", "parametro"),),
    "aplica_a": (("regra", "feature"),),
    "restringe": (("regra", "parametro"),),
    "impacta": (("parametro", "objetivo"), ("estado", "objetivo")),
    "executa": (("job", "produto"),),
    "executado_em": (("job", "maquina"),),
    "usa_parametro": (("job", "parametro"),),
    "tem_operacao": (("job", "operacao"),),
    "imprime": (("operacao", "feature"),),
    "observado_como": (("job", "estado"),),
    "ocorre_durante": (("estado", "operacao"),),
}


@dataclass(frozen=True)
class No:
    id: str
    tipo: str
    atributos: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Aresta:
    origem: str
    destino: str
    relacao: str
    atributos: dict[str, Any] = field(default_factory=dict)
    proveniencia: str = ""


@dataclass
class GrafoConhecimento:
    nos: dict[str, No] = field(default_factory=dict)
    arestas: list[Aresta] = field(default_factory=list)

    # construcao -----------------------------------------------------------
    def adicionar_no(self, no: No) -> No:
        existente = self.nos.get(no.id)
        if existente is not None:
            if existente.tipo != no.tipo:
                raise ValueError(f"no {no.id!r} ja existe com tipo {existente.tipo!r}")
            return existente
        self.nos[no.id] = no
        return no

    def adicionar_aresta(self, aresta: Aresta) -> Aresta:
        self.arestas.append(aresta)
        return aresta

    # consulta -------------------------------------------------------------
    def no(self, id_: str) -> No:
        return self.nos[id_]

    def arestas_de(self, origem: str, relacao: str | None = None) -> list[Aresta]:
        return [a for a in self.arestas if a.origem == origem and (relacao is None or a.relacao == relacao)]

    def arestas_para(self, destino: str, relacao: str | None = None) -> list[Aresta]:
        return [a for a in self.arestas if a.destino == destino and (relacao is None or a.relacao == relacao)]

    def nos_do_tipo(self, tipo: str) -> list[No]:
        return [n for n in self.nos.values() if n.tipo == tipo]

    # contrato -------------------------------------------------------------
    def validar(self) -> list[str]:
        erros: list[str] = []
        for n in self.nos.values():
            if n.tipo not in TIPOS_NO:
                erros.append(f"no {n.id}: tipo desconhecido {n.tipo!r}")
        for a in self.arestas:
            if a.relacao not in RELACOES:
                erros.append(f"aresta {a.origem}->{a.destino}: relacao desconhecida {a.relacao!r}")
                continue
            o, d = self.nos.get(a.origem), self.nos.get(a.destino)
            if o is None or d is None:
                erros.append(f"aresta {a.relacao} {a.origem}->{a.destino}: no inexistente")
                continue
            if (o.tipo, d.tipo) not in RELACOES[a.relacao]:
                erros.append(f"aresta {a.relacao}: {o.tipo}->{d.tipo} nao permitido")
            if not a.proveniencia:
                erros.append(f"aresta {a.relacao} {a.origem}->{a.destino}: sem proveniencia")
        return erros

    # serializacao ---------------------------------------------------------
    def para_dict(self) -> dict[str, Any]:
        return {
            "nos": [{"id": n.id, "tipo": n.tipo, "atributos": n.atributos} for n in self.nos.values()],
            "arestas": [
                {"origem": a.origem, "destino": a.destino, "relacao": a.relacao, "atributos": a.atributos, "proveniencia": a.proveniencia}
                for a in self.arestas
            ],
        }

    @classmethod
    def de_dict(cls, d: dict[str, Any]) -> "GrafoConhecimento":
        g = cls()
        for n in d["nos"]:
            g.adicionar_no(No(n["id"], n["tipo"], dict(n.get("atributos", {}))))
        for a in d["arestas"]:
            g.adicionar_aresta(Aresta(a["origem"], a["destino"], a["relacao"], dict(a.get("atributos", {})), a.get("proveniencia", "")))
        return g
