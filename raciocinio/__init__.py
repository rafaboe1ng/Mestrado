"""Modulo raciocinio: do grafo para a ``Recomendacao``.

Metodo proposto (``recomendar``): percorre o grafo
  job -observado_como-> estado(anomalia) -ocorre_durante-> operacao -imprime-> feature
      -requer-> parametro  (x)  job -usa_parametro-> parametro
e, onde o valor usado viola a restricao, atribui a causa a feature, propoe o ajuste que
satisfaz a restricao dentro da faixa do parametro e calcula os trade-offs pelas arestas
``impacta``. Cada passo vira um ``PassoExplicacao`` com a proveniencia da aresta.

Baselines (mesma saida, mesma regua): ``baseline_geometrico`` (a parede mais fina e sempre a
causa; ajustes = voltar ao padrao) e ``baseline_temporal`` (a feature impressa durante a
primeira anomalia, sem regras; ajustes = voltar ao padrao).
"""
from __future__ import annotations

from contracts.base import comparar, garantir
from contracts.grafo import Aresta, GrafoConhecimento, No
from contracts.recomendacao import Ajuste, PassoExplicacao, Recomendacao
from grafo import id_job

__all__ = ["atribuir", "recomendar", "baseline_geometrico", "baseline_temporal", "viavel", "tradeoffs"]


# --- consultas auxiliares ------------------------------------------------------

def _estados_anomalos(g: GrafoConhecimento, job: str) -> list[No]:
    nos = [g.nos[a.destino] for a in g.arestas_de(job, "observado_como") if g.nos[a.destino].atributos.get("anomalia")]
    return sorted(nos, key=lambda n: n.atributos.get("inicio_s", 0.0))


def _parametros_usados(g: GrafoConhecimento, job: str) -> dict[str, tuple[float, Aresta]]:
    return {a.destino: (float(a.atributos["valor"]), a) for a in g.arestas_de(job, "usa_parametro")}


def _janelas(estados: list[No]) -> tuple[int, ...]:
    return tuple(sorted({int(i) for e in estados for i in e.atributos.get("janelas", [])}))


def _nome_param(id_param: str) -> str:
    return id_param.split(":", 1)[1]


def _features_do_produto(g: GrafoConhecimento, job: str) -> list[No]:
    exec_ = g.arestas_de(job, "executa")
    if not exec_:
        return []
    return [g.nos[a.destino] for a in g.arestas_de(exec_[0].destino, "tem_feature")]


# --- metodo proposto --------------------------------------------------------------

def atribuir(g: GrafoConhecimento, job_id: str) -> dict:
    """Atribuicao de causa por caminho no grafo. Retorna dict(causa, regras, passos, ajustes, janelas)."""
    job = id_job(job_id)
    anomalos = _estados_anomalos(g, job)
    vazio = {"causa": None, "regras": (), "passos": (), "ajustes": (), "janelas": _janelas(anomalos)}
    if not anomalos:
        return vazio
    usados = _parametros_usados(g, job)
    melhor: dict | None = None
    for est in anomalos:
        for a_oc in g.arestas_de(est.id, "ocorre_durante"):
            op = a_oc.destino
            for a_imp in g.arestas_de(op, "imprime"):
                feat = a_imp.destino
                violadas = []
                for a_req in g.arestas_de(feat, "requer"):
                    info = usados.get(a_req.destino)
                    if info is None:
                        continue
                    valor, a_usa = info
                    if not comparar(valor, a_req.atributos["operador"], float(a_req.atributos["valor"])):
                        violadas.append((a_req, valor, a_usa))
                if violadas and (melhor is None or len(violadas) > len(melhor["violadas"])):
                    melhor = {"est": est, "a_oc": a_oc, "op": op, "a_imp": a_imp, "feat": feat, "violadas": violadas}
        if melhor is not None:
            break
    if melhor is None:
        e = anomalos[0]
        obs = g.arestas_de(job, "observado_como")
        prov = next((a.proveniencia for a in obs if a.destino == e.id), "regimes")
        passo = PassoExplicacao(job, "observado_como", e.id,
                                f"anomalia entre {e.atributos.get('inicio_s', 0):.0f} e {e.atributos.get('fim_s', 0):.0f} s sem regra violada nas features impressas",
                                prov)
        return {**vazio, "passos": (passo,)}

    est, a_oc, op, a_imp, feat = melhor["est"], melhor["a_oc"], melhor["op"], melhor["a_imp"], melhor["feat"]
    prov_obs = next((a.proveniencia for a in g.arestas_de(job, "observado_como") if a.destino == est.id), "regimes")
    passos = [
        PassoExplicacao(job, "observado_como", est.id,
                        f"estado '{est.atributos.get('nome')}' com anomalia entre {est.atributos.get('inicio_s', 0):.0f} e {est.atributos.get('fim_s', 0):.0f} s", prov_obs),
        PassoExplicacao(est.id, "ocorre_durante", op, f"sobreposicao de {a_oc.atributos.get('sobreposicao_s', 0):.0f} s com a operacao", a_oc.proveniencia),
        PassoExplicacao(op, "imprime", feat, f"a operacao imprime a feature '{g.nos[feat].atributos.get('feature_id')}'", a_imp.proveniencia),
    ]
    for a_req, valor, a_usa in melhor["violadas"]:
        nome = _nome_param(a_req.destino)
        passos.append(PassoExplicacao(feat, "requer", a_req.destino,
                                      f"regra {a_req.atributos['regra_id']} exige {nome} {a_req.atributos['operador']} {a_req.atributos['valor']}", a_req.proveniencia))
        passos.append(PassoExplicacao(job, "usa_parametro", a_req.destino, f"o job usou {nome} = {valor}", a_usa.proveniencia))
    regras = tuple(sorted({a_req.atributos["regra_id"] for a_req, _, _ in melhor["violadas"]}))
    return {"causa": g.nos[feat].atributos.get("feature_id"), "regras": regras, "passos": tuple(passos),
            "ajustes": _ajustes(g, melhor["violadas"]), "janelas": _janelas(anomalos)}


def _ajustes(g: GrafoConhecimento, violadas) -> tuple[Ajuste, ...]:
    """Um ajuste por parametro, no valor mais restritivo entre as regras violadas."""
    por_param: dict[str, list] = {}
    for a_req, valor, _ in violadas:
        par = a_req.destino
        op = a_req.atributos["operador"]
        lim = float(a_req.atributos["valor"])
        attrs = g.nos[par].atributos
        faixa = float(attrs.get("maximo", lim)) - float(attrs.get("minimo", lim)) or 1.0
        passo = 0.01 * faixa
        alvo = lim if op in ("<=", ">=", "==") else (lim - passo if op == "<" else lim + passo)
        superior = op in ("<", "<=")
        if par not in por_param:
            por_param[par] = [valor, alvo, a_req.atributos["regra_id"]]
        else:
            atual = por_param[par]
            atual[1] = min(atual[1], alvo) if superior else max(atual[1], alvo)
            atual[2] = atual[2] + "+" + a_req.atributos["regra_id"]
    return tuple(Ajuste(_nome_param(p), de, para, rid) for p, (de, para, rid) in por_param.items() if de != para)


def viavel(g: GrafoConhecimento, ajustes: tuple[Ajuste, ...]) -> bool:
    for a in ajustes:
        no = g.nos.get(f"parametro:{a.parametro}")
        if no is None or "minimo" not in no.atributos:
            continue
        if not float(no.atributos["minimo"]) <= a.para <= float(no.atributos["maximo"]):
            return False
    return True


def tradeoffs(g: GrafoConhecimento, ajustes: tuple[Ajuste, ...]) -> dict[str, float]:
    """Mesma funcao para todos os metodos: le as arestas ``impacta`` parametro->objetivo."""
    out = {"tempo_pct": 0.0, "material_pct": 0.0, "qualidade_pontos": 0.0}
    for a in ajustes:
        if a.de == 0:
            continue
        for ar in g.arestas_de(f"parametro:{a.parametro}", "impacta"):
            objetivo = ar.destino.split(":", 1)[1]
            modelo = str(ar.atributos.get("modelo", ""))
            sentido = int(ar.atributos.get("sentido", 0))
            if objetivo == "tempo":
                out["tempo_pct"] += (a.de / a.para - 1.0) * 100.0 if "1/" in modelo else (a.para / a.de - 1.0) * 100.0
            elif objetivo == "material":
                out["material_pct"] += (a.para / a.de - 1.0) * 100.0
            elif objetivo == "qualidade":
                out["qualidade_pontos"] += sentido * (1.0 if a.para > a.de else -1.0)
    return {k: round(v, 2) for k, v in out.items()}


def recomendar(g: GrafoConhecimento, job_id: str) -> Recomendacao:
    job = id_job(job_id)
    r = atribuir(g, job_id)
    anomalia = bool(_estados_anomalos(g, job))
    rec = Recomendacao(job_id, "grafo", anomalia, r["janelas"], r["causa"], r["regras"], r["passos"], r["ajustes"],
                       viavel(g, r["ajustes"]), tradeoffs(g, r["ajustes"]))
    garantir(rec)
    return rec


# --- baselines ---------------------------------------------------------------------

def _reset_padrao(g: GrafoConhecimento, job: str) -> tuple[Ajuste, ...]:
    ajustes = []
    for par, (valor, _) in _parametros_usados(g, job).items():
        padrao = g.nos[par].atributos.get("padrao")
        if padrao is not None and float(padrao) != valor:
            ajustes.append(Ajuste(_nome_param(par), valor, float(padrao), "padrao"))
    return tuple(ajustes)


def baseline_geometrico(g: GrafoConhecimento, job_id: str) -> Recomendacao:
    """Heuristica: se houve anomalia, a causa e a parede mais fina; ajustes = voltar ao padrao."""
    job = id_job(job_id)
    anomalos = _estados_anomalos(g, job)
    causa, passos = None, ()
    if anomalos:
        paredes = [f for f in _features_do_produto(g, job) if f.atributos.get("tipo_feature") == "parede" and "dim_espessura_mm" in f.atributos]
        if paredes:
            f = min(paredes, key=lambda n: float(n.atributos["dim_espessura_mm"]))
            causa = f.atributos["feature_id"]
            passos = (PassoExplicacao(job, "heuristica", f.id, "feature de parede mais fina do produto", "raciocinio/baseline_geometrico"),)
    ajustes = _reset_padrao(g, job) if anomalos else ()
    rec = Recomendacao(job_id, "baseline_geometrico", bool(anomalos), _janelas(anomalos), causa, (), passos, ajustes,
                       viavel(g, ajustes), tradeoffs(g, ajustes))
    garantir(rec)
    return rec


def baseline_temporal(g: GrafoConhecimento, job_id: str) -> Recomendacao:
    """Heuristica: a causa e a feature impressa durante a primeira anomalia; sem regras; ajustes = padrao."""
    job = id_job(job_id)
    anomalos = _estados_anomalos(g, job)
    causa, passos = None, ()
    if anomalos:
        est = anomalos[0]
        ocs = sorted(g.arestas_de(est.id, "ocorre_durante"), key=lambda a: -float(a.atributos.get("sobreposicao_s", 0)))
        for a_oc in ocs:
            imps = g.arestas_de(a_oc.destino, "imprime")
            if imps:
                causa = g.nos[imps[0].destino].atributos.get("feature_id")
                passos = (PassoExplicacao(est.id, "ocorre_durante", a_oc.destino, "operacao ativa durante a primeira anomalia", a_oc.proveniencia),
                          PassoExplicacao(a_oc.destino, "imprime", imps[0].destino, "feature impressa por essa operacao", imps[0].proveniencia))
                break
    ajustes = _reset_padrao(g, job) if anomalos else ()
    rec = Recomendacao(job_id, "baseline_temporal", bool(anomalos), _janelas(anomalos), causa, (), passos, ajustes,
                       viavel(g, ajustes), tradeoffs(g, ajustes))
    garantir(rec)
    return rec
