"""Modulo grafo: constroi o ``GrafoConhecimento`` a partir das tres fontes.

Entradas (todas por contrato): ProdutoFeatures, ConhecimentoProcesso, SerieMultivariada,
EstadosOperacionais. Toda aresta recebe ``proveniencia`` dizendo qual fonte a gerou.
Exporta para JSON e GraphML (inspecao visual em ferramentas externas).
"""
from __future__ import annotations

import json
from pathlib import Path
from xml.sax.saxutils import escape

from contracts.base import garantir
from contracts.estados import EstadosOperacionais
from contracts.grafo import Aresta, GrafoConhecimento, No
from contracts.processo import OBJETIVOS, ConhecimentoProcesso
from contracts.produto import ProdutoFeatures
from contracts.sensores import SerieMultivariada
from processo import regras_aplicaveis

__all__ = ["construir", "segmentos", "metricas_integracao", "exportar_json", "exportar_graphml", "resumo",
           "id_produto", "id_feature", "id_parametro", "id_objetivo", "id_regra", "id_job", "id_operacao", "id_estado"]


def id_produto(p: ProdutoFeatures) -> str:
    return f"produto:{p.produto_id}@{p.versao_design}"


def id_feature(p: ProdutoFeatures, feature_id: str) -> str:
    return f"feature:{p.produto_id}@{p.versao_design}:{feature_id}"


def id_parametro(nome: str) -> str:
    return f"parametro:{nome}"


def id_objetivo(nome: str) -> str:
    return f"objetivo:{nome}"


def id_regra(regra_id: str) -> str:
    return f"regra:{regra_id}"


def id_job(job_id: str) -> str:
    return f"job:{job_id}"


def id_operacao(job_id: str, op_id: str) -> str:
    return f"operacao:{job_id}:{op_id}"


def id_estado(job_id: str, n: int) -> str:
    return f"estado:{job_id}:{n}"


def segmentos(estados: EstadosOperacionais) -> list[dict]:
    """Agrupa janelas contiguas com o mesmo (estado, anomalia) em segmentos."""
    segs: list[dict] = []
    for j in estados.janelas:
        chave = (j.estado, j.anomalia)
        if segs and segs[-1]["chave"] == chave:
            segs[-1]["fim_s"] = j.fim_s
            segs[-1]["janelas"].append(j.indice)
            segs[-1]["score_max"] = max(segs[-1]["score_max"], j.score)
        else:
            segs.append({"n": len(segs), "chave": chave, "estado": j.estado, "nome": estados.nomes_estado[j.estado],
                         "anomalia": j.anomalia, "inicio_s": j.inicio_s, "fim_s": j.fim_s, "janelas": [j.indice], "score_max": j.score})
    for s in segs:
        del s["chave"]
    return segs


def construir(produto: ProdutoFeatures, base: ConhecimentoProcesso, serie: SerieMultivariada,
              estados: EstadosOperacionais, maquina_id: str = "impressora_lab") -> GrafoConhecimento:
    for obj in (produto, base, serie, estados):
        garantir(obj)
    g = GrafoConhecimento()

    # --- produto e features (fonte: cad_features)
    prov_cad = f"cad_features/{produto.origem}"
    g.adicionar_no(No(id_produto(produto), "produto", {"produto_id": produto.produto_id, "versao_design": produto.versao_design}))
    for f in produto.features:
        attrs = {"feature_id": f.id, "tipo_feature": f.tipo, **{f"dim_{k}": float(v) for k, v in f.dimensoes.items()}}
        g.adicionar_no(No(id_feature(produto, f.id), "feature", attrs))
        g.adicionar_aresta(Aresta(id_produto(produto), id_feature(produto, f.id), "tem_feature", {}, prov_cad))
    for f in produto.features:
        for a in f.adjacentes:
            g.adicionar_aresta(Aresta(id_feature(produto, f.id), id_feature(produto, a), "adjacente_a", {}, prov_cad))

    # --- parametros, objetivos, impactos e regras aplicaveis (fonte: processo)
    prov_base = f"processo/base:{base.processo}-{base.material}"
    for p in base.parametros:
        g.adicionar_no(No(id_parametro(p.nome), "parametro", {"unidade": p.unidade, "minimo": p.minimo, "maximo": p.maximo, "padrao": p.padrao}))
    for o in OBJETIVOS:
        g.adicionar_no(No(id_objetivo(o), "objetivo", {}))
    for imp in base.impactos:
        g.adicionar_aresta(Aresta(id_parametro(imp.parametro), id_objetivo(imp.objetivo), "impacta", {"sentido": imp.sentido, "modelo": imp.modelo}, prov_base))
    for regra, feature in regras_aplicaveis(base, produto):
        prov_regra = f"processo/regra:{regra.id}"
        g.adicionar_no(No(id_regra(regra.id), "regra", {"condicao": regra.condicao.texto(), "restricao": regra.restricao.texto(),
                                                        "justificativa": regra.justificativa, "fonte": regra.fonte}))
        g.adicionar_aresta(Aresta(id_regra(regra.id), id_feature(produto, feature.id), "aplica_a", {}, prov_regra))
        g.adicionar_aresta(Aresta(id_regra(regra.id), id_parametro(regra.restricao.parametro), "restringe",
                                  {"operador": regra.restricao.operador, "valor": regra.restricao.valor}, prov_regra))
        g.adicionar_aresta(Aresta(id_feature(produto, feature.id), id_parametro(regra.restricao.parametro), "requer",
                                  {"operador": regra.restricao.operador, "valor": regra.restricao.valor, "regra_id": regra.id}, prov_regra))

    # --- job, maquina, parametros usados, operacoes (fonte: sensores/meta)
    job = id_job(serie.job_id)
    prov_job = f"sensores/meta:{serie.job_id}"
    g.adicionar_no(No(job, "job", {"job_id": serie.job_id, "taxa_hz": serie.taxa_hz, "duracao_s": serie.duracao_s, "canais": list(serie.canais)}))
    g.adicionar_no(No(f"maquina:{maquina_id}", "maquina", {}))
    g.adicionar_aresta(Aresta(job, f"maquina:{maquina_id}", "executado_em", {}, prov_job))
    g.adicionar_aresta(Aresta(job, id_produto(produto), "executa", {}, prov_job))
    for nome, valor in serie.parametros_usados.items():
        if id_parametro(nome) not in g.nos:
            g.adicionar_no(No(id_parametro(nome), "parametro", {"fora_da_base": True}))
        g.adicionar_aresta(Aresta(job, id_parametro(nome), "usa_parametro", {"valor": float(valor)}, prov_job))
    for op in serie.operacoes:
        g.adicionar_no(No(id_operacao(serie.job_id, op.id), "operacao", {"inicio_s": op.inicio_s, "fim_s": op.fim_s, "descricao": op.descricao}))
        g.adicionar_aresta(Aresta(job, id_operacao(serie.job_id, op.id), "tem_operacao", {}, prov_job))
        if op.feature_id and id_feature(produto, op.feature_id) in g.nos:
            g.adicionar_aresta(Aresta(id_operacao(serie.job_id, op.id), id_feature(produto, op.feature_id), "imprime", {}, prov_job))

    # --- estados observados (fonte: regimes)
    prov_est = f"regimes/{estados.metodo}"
    for seg in segmentos(estados):
        eid = id_estado(serie.job_id, seg["n"])
        g.adicionar_no(No(eid, "estado", {"nome": seg["nome"], "anomalia": seg["anomalia"], "inicio_s": seg["inicio_s"],
                                           "fim_s": seg["fim_s"], "janelas": seg["janelas"], "score_max": seg["score_max"]}))
        g.adicionar_aresta(Aresta(job, eid, "observado_como", {"inicio_s": seg["inicio_s"], "fim_s": seg["fim_s"], "janelas": seg["janelas"]}, prov_est))
        for op in serie.operacoes:
            sobre = min(seg["fim_s"], op.fim_s) - max(seg["inicio_s"], op.inicio_s)
            if sobre > 0:
                g.adicionar_aresta(Aresta(eid, id_operacao(serie.job_id, op.id), "ocorre_durante", {"sobreposicao_s": float(sobre)}, prov_est))
        if seg["anomalia"]:
            g.adicionar_aresta(Aresta(eid, id_objetivo("qualidade"), "impacta", {"sentido": -1, "modelo": "anomalia observada"}, prov_est))

    garantir(g)
    return g


def metricas_integracao(g: GrafoConhecimento, produto: ProdutoFeatures, serie: SerieMultivariada, estados: EstadosOperacionais) -> dict:
    """Cobertura (entidades esperadas presentes) e proveniencia (arestas com origem declarada)."""
    esperados = [id_produto(produto), id_job(serie.job_id)]
    esperados += [id_feature(produto, f.id) for f in produto.features]
    esperados += [id_parametro(n) for n in serie.parametros_usados]
    esperados += [id_operacao(serie.job_id, o.id) for o in serie.operacoes]
    esperados += [id_estado(serie.job_id, s["n"]) for s in segmentos(estados)]
    presentes = sum(1 for e in esperados if e in g.nos)
    com_prov = sum(1 for a in g.arestas if a.proveniencia)
    return {
        "cobertura_pct": 100.0 * presentes / len(esperados),
        "proveniencia_pct": 100.0 * com_prov / len(g.arestas) if g.arestas else 0.0,
        "n_nos": len(g.nos),
        "n_arestas": len(g.arestas),
    }


def resumo(g: GrafoConhecimento) -> dict:
    por_tipo: dict[str, int] = {}
    for n in g.nos.values():
        por_tipo[n.tipo] = por_tipo.get(n.tipo, 0) + 1
    por_rel: dict[str, int] = {}
    for a in g.arestas:
        por_rel[a.relacao] = por_rel.get(a.relacao, 0) + 1
    return {"nos_por_tipo": por_tipo, "arestas_por_relacao": por_rel}


def exportar_json(g: GrafoConhecimento, caminho: str | Path) -> Path:
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(g.para_dict(), indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return caminho


def exportar_graphml(g: GrafoConhecimento, caminho: str | Path) -> Path:
    """GraphML minimo (tipo/atributos do no, relacao/proveniencia da aresta) para inspecao visual."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    linhas = ['<?xml version="1.0" encoding="UTF-8"?>',
              '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
              '  <key id="tipo" for="node" attr.name="tipo" attr.type="string"/>',
              '  <key id="atributos" for="node" attr.name="atributos" attr.type="string"/>',
              '  <key id="relacao" for="edge" attr.name="relacao" attr.type="string"/>',
              '  <key id="proveniencia" for="edge" attr.name="proveniencia" attr.type="string"/>',
              '  <graph id="G" edgedefault="directed">']
    for n in g.nos.values():
        linhas.append(f'    <node id="{escape(n.id, {chr(34): "&quot;"})}"><data key="tipo">{escape(n.tipo)}</data>'
                      f'<data key="atributos">{escape(json.dumps(n.atributos, ensure_ascii=False, default=str))}</data></node>')
    for i, a in enumerate(g.arestas):
        linhas.append(f'    <edge id="e{i}" source="{escape(a.origem, {chr(34): "&quot;"})}" target="{escape(a.destino, {chr(34): "&quot;"})}">'
                      f'<data key="relacao">{escape(a.relacao)}</data><data key="proveniencia">{escape(a.proveniencia)}</data></edge>')
    linhas += ["  </graph>", "</graphml>"]
    caminho.write_text("\n".join(linhas), encoding="utf-8")
    return caminho
