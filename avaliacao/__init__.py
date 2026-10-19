"""Modulo avaliacao: a regua unica.

Nenhum metodo calcula o proprio valor. ``regua()`` recebe, por job, os objetos de contrato
(EstadosOperacionais, Recomendacao) produzidos por um metodo e o gabarito, e devolve as
mesmas metricas para qualquer metodo: anomalia (precisao, revocacao, F1 micro), pureza dos
estados, acuracia da causa, viabilidade, resolucao de violacoes, trade-offs informados,
explicacao completa.
"""
from __future__ import annotations

from contracts.estados import EstadosOperacionais
from contracts.recomendacao import CHAVES_TRADEOFF, Recomendacao

__all__ = ["metricas_binarias", "pureza", "avaliar_estados", "avaliar_recomendacao", "parametros_apos", "regua"]


def metricas_binarias(pred: list[bool], real: list[bool]) -> dict:
    vp = sum(1 for p, r in zip(pred, real) if p and r)
    fp = sum(1 for p, r in zip(pred, real) if p and not r)
    fn = sum(1 for p, r in zip(pred, real) if not p and r)
    vn = sum(1 for p, r in zip(pred, real) if not p and not r)
    precisao = vp / (vp + fp) if (vp + fp) else 0.0
    revocacao = vp / (vp + fn) if (vp + fn) else 0.0
    f1 = 2 * precisao * revocacao / (precisao + revocacao) if (precisao + revocacao) else 0.0
    return {"vp": vp, "fp": fp, "fn": fn, "vn": vn, "precisao": precisao, "revocacao": revocacao, "f1": f1}


def pureza(pred: list, real: list) -> float:
    """Pureza dos clusters previstos em relacao aos rotulos reais."""
    if not pred:
        return 0.0
    grupos: dict = {}
    for p, r in zip(pred, real):
        grupos.setdefault(p, {}).setdefault(r, 0)
        grupos[p][r] += 1
    return sum(max(c.values()) for c in grupos.values()) / len(pred)


def avaliar_estados(estados: EstadosOperacionais, gabarito_job: dict) -> dict:
    gab = gabarito_job["janelas"]
    n = min(len(gab), len(estados.janelas))
    pred_an = [bool(j.anomalia) for j in estados.janelas[:n]]
    real_an = [bool(j["anomalia"]) for j in gab[:n]]
    m = metricas_binarias(pred_an, real_an)
    m["pureza"] = pureza([j.estado for j in estados.janelas[:n]], [j["estado"] for j in gab[:n]])
    m["janelas_descasadas"] = abs(len(gab) - len(estados.janelas))
    return m


def parametros_apos(parametros_usados: dict[str, float], rec: Recomendacao | None) -> dict[str, float]:
    """Parametros do job depois de aplicar os ajustes da recomendacao."""
    novos = dict(parametros_usados)
    if rec is not None:
        for a in rec.ajustes:
            novos[a.parametro] = a.para
    return novos


def avaliar_recomendacao(rec: Recomendacao, gabarito_job: dict, violacoes_apos: int | None) -> dict:
    anomalia_real = any(j["anomalia"] for j in gabarito_job["janelas"])
    causa_real = gabarito_job.get("causa_feature")
    regras_gab = list(gabarito_job.get("regras_violadas", []))
    aplicavel_resolve = anomalia_real and bool(regras_gab)
    return {
        "anomalia_real": anomalia_real,
        "anomalia_detectada": rec.anomalia_detectada,
        "causa_real": causa_real,
        "causa_prevista": rec.causa_feature,
        "causa_correta": rec.causa_feature == causa_real,
        "tem_ajustes": bool(rec.ajustes),
        "viavel": rec.viavel,
        "resolve_violacoes": (violacoes_apos == 0) if (aplicavel_resolve and violacoes_apos is not None) else None,
        "explicacao_completa": (bool(rec.explicacao) and all(p.proveniencia for p in rec.explicacao)) if rec.causa_feature else None,
        "tradeoffs_informados": all(k in rec.tradeoffs for k in CHAVES_TRADEOFF),
        "delta_tempo_pct": rec.tradeoffs.get("tempo_pct"),
        "delta_material_pct": rec.tradeoffs.get("material_pct"),
        "delta_qualidade_pontos": rec.tradeoffs.get("qualidade_pontos"),
    }


def _media(valores: list) -> float | None:
    v = [x for x in valores if x is not None]
    return sum(v) / len(v) if v else None


def regua(nome_metodo: str, por_job: dict[str, dict], gabarito: dict) -> dict:
    """Agrega as metricas de um metodo sobre os jobs. ``por_job[job] = {estados, recomendacao, violacoes_apos}``."""
    linhas = []
    vp = fp = fn = 0
    purezas: list[float] = []
    for job, d in por_job.items():
        gj = gabarito[job]
        linha: dict = {"job": job}
        est = d.get("estados")
        if est is not None:
            e = avaliar_estados(est, gj)
            vp, fp, fn = vp + e["vp"], fp + e["fp"], fn + e["fn"]
            purezas.append(e["pureza"])
            linha.update({"anomalia_f1_job": e["f1"], "pureza": e["pureza"], "janelas_descasadas": e["janelas_descasadas"]})
        rec = d.get("recomendacao")
        if rec is not None:
            linha.update(avaliar_recomendacao(rec, gj, d.get("violacoes_apos")))
        linhas.append(linha)
    precisao = vp / (vp + fp) if (vp + fp) else 0.0
    revocacao = vp / (vp + fn) if (vp + fn) else 0.0
    f1 = 2 * precisao * revocacao / (precisao + revocacao) if (precisao + revocacao) else 0.0
    com_rec = [l for l in linhas if "causa_correta" in l]
    com_ajustes = [l for l in com_rec if l["tem_ajustes"]]
    return {
        "metodo": nome_metodo,
        "n_jobs": len(linhas),
        "anomalia_precisao": precisao if purezas else None,
        "anomalia_revocacao": revocacao if purezas else None,
        "anomalia_f1": f1 if purezas else None,
        "pureza_media": _media(purezas),
        "acuracia_causa": _media([l["causa_correta"] for l in com_rec]),
        "acuracia_causa_com_anomalia": _media([l["causa_correta"] for l in com_rec if l["anomalia_real"]]),
        "taxa_viavel": _media([l["viavel"] for l in com_ajustes]),
        "taxa_resolve": _media([l["resolve_violacoes"] for l in com_rec]),
        "taxa_explicacao_completa": _media([l["explicacao_completa"] for l in com_rec]),
        "taxa_tradeoffs": _media([l["tradeoffs_informados"] for l in com_rec]),
        "delta_tempo_medio_pct": _media([l["delta_tempo_pct"] for l in com_ajustes]),
        "por_job": linhas,
    }
