"""exp01: pipeline completo sobre a bateria sintetica; proposto vs baselines pela regua unica.

Calibra regimes nos jobs de calibracao, aplica nos de avaliacao, constroi o grafo, gera a
recomendacao pelo grafo e pelos dois baselines de atribuicao, avalia tudo com ``avaliacao.regua``
e grava o JSON com proveniencia. Rodar: ``python -m experimentos.exp01_pipeline_sintetico``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import avaliacao
import cad_features
import grafo as mod_grafo
import raciocinio
import regimes
import sensores
from contracts.base import ErroContrato
from experimentos import proveniencia
from processo import base_fdm_pla, violacoes

RAIZ = Path(__file__).resolve().parents[1]
NOME = "exp01_pipeline_sintetico"
CONFIG = {"largura_janela_s": 10.0, "k": 4, "semente": 0, "fator_anomalia": 2.0, "percentil_distancia": 99.0,
          "n_desvios_baseline": 3.0, "baseline_robusto": True}
METODOS = ("proposto", "baseline_limiar", "baseline_geometrico", "baseline_temporal")


def executar(raiz_dados: Path = RAIZ / "dados" / "sintetico", config: dict = CONFIG) -> dict:
    bateria = json.loads((raiz_dados / "bateria.json").read_text(encoding="utf-8"))
    gabarito = json.loads((raiz_dados / "gabarito.json").read_text(encoding="utf-8"))
    base = base_fdm_pla()
    contratos_violados: list[str] = []
    series, produtos = {}, {}
    for job, info in bateria["jobs"].items():
        try:
            series[job] = sensores.carregar(raiz_dados / info["caso"])
            produtos[job] = cad_features.carregar_ficha(raiz_dados / info["ficha"])
        except ErroContrato as e:
            contratos_violados.append(f"{job}: {e}")
    calib = [j for j, i in bateria["jobs"].items() if i["conjunto"] == "calibracao" and j in series]
    aval = [j for j, i in bateria["jobs"].items() if i["conjunto"] == "avaliacao" and j in series]
    L = config["largura_janela_s"]
    modelo = regimes.ajustar([series[j] for j in calib], largura_s=L, k=config["k"], semente=config["semente"],
                             fator_anomalia=config["fator_anomalia"], percentil_distancia=config["percentil_distancia"])
    limiar = regimes.calibrar_limiar([series[j] for j in calib], largura_s=L, n_desvios=config["n_desvios_baseline"],
                                     robusto=config.get("baseline_robusto", True))

    por_metodo: dict[str, dict] = {m: {} for m in METODOS}
    integ_prov, integ_cob, explicacoes = [], [], {}
    for j in aval:
        s, p = series[j], produtos[j]
        try:
            est_p = regimes.aplicar(modelo, s)
            est_b = regimes.baseline_limiar(s, L, limiar)
            g = mod_grafo.construir(p, base, s, est_p)
            recs = {
                "proposto": raciocinio.recomendar(g, j),
                "baseline_geometrico": raciocinio.baseline_geometrico(g, j),
                "baseline_temporal": raciocinio.baseline_temporal(g, j),
            }
        except ErroContrato as e:
            contratos_violados.append(f"{j}: {e}")
            continue
        m = mod_grafo.metricas_integracao(g, p, s, est_p)
        integ_prov.append(m["proveniencia_pct"])
        integ_cob.append(m["cobertura_pct"])
        for nome, rec in recs.items():
            v_apos = len(violacoes(base, p, avaliacao.parametros_apos(s.parametros_usados, rec)))
            por_metodo[nome][j] = {"estados": est_p, "recomendacao": rec, "violacoes_apos": v_apos}
        por_metodo["baseline_limiar"][j] = {"estados": est_b, "recomendacao": None, "violacoes_apos": None}
        explicacoes[j] = {
            "causa": recs["proposto"].causa_feature,
            "regras": list(recs["proposto"].regras_violadas),
            "ajustes": [vars(a) for a in recs["proposto"].ajustes],
            "tradeoffs": recs["proposto"].tradeoffs,
            "passos": [f"{x.origem} -{x.relacao}-> {x.destino}: {x.detalhe} [{x.proveniencia}]" for x in recs["proposto"].explicacao],
        }

    resultado: dict = {m: avaliacao.regua(m, d, gabarito) for m, d in por_metodo.items()}
    resultado["proposto"].update({
        "contratos_violados": len(contratos_violados),
        "detalhe_contratos_violados": contratos_violados,
        "grafo_proveniencia_pct": sum(integ_prov) / len(integ_prov) if integ_prov else None,
        "grafo_cobertura_pct": sum(integ_cob) / len(integ_cob) if integ_cob else None,
    })
    resultado["config"] = {
        **config,
        "jobs_calibracao": calib,
        "jobs_avaliacao": aval,
        "modelo_regimes": {"nomes_estado": {str(k): v for k, v in modelo.nomes_estado.items()},
                           "estado_anomalia": modelo.estado_anomalia, "limiar_distancia": modelo.limiar_distancia},
        "limiar_baseline_vibracao": limiar,
    }
    resultado["explicacoes_proposto"] = explicacoes
    resultado["rotulo"] = "SINTETICO"
    return resultado


def _fmt(x) -> str:
    return "-" if x is None else (f"{x:.3f}" if isinstance(x, float) else str(x))


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    r = executar()
    caminho = proveniencia.registrar(NOME, r, comando=f"python -m experimentos.{NOME}", dados=[RAIZ / "dados" / "sintetico"])
    colunas = ("anomalia_f1", "pureza_media", "acuracia_causa", "taxa_viavel", "taxa_resolve", "taxa_tradeoffs", "taxa_explicacao_completa")
    print(f"[{r['rotulo']}] jobs de avaliacao: {len(r['config']['jobs_avaliacao'])} | regimes: {r['config']['modelo_regimes']['nomes_estado']}")
    print("metodo".ljust(22) + "".join(c[:14].ljust(16) for c in colunas))
    for m in METODOS:
        print(m.ljust(22) + "".join(_fmt(r[m].get(c)).ljust(16) for c in colunas))
    p = r["proposto"]
    print(f"contratos violados: {p['contratos_violados']} | cobertura grafo: {_fmt(p['grafo_cobertura_pct'])} % | proveniencia: {_fmt(p['grafo_proveniencia_pct'])} %")
    reg = json.loads(caminho.read_text(encoding="utf-8"))
    print(f"gravado em {caminho.relative_to(RAIZ)} | execucao {reg['execucao_numero_para_estes_dados']} para estes dados | fora da amostra: {reg['vale_como_fora_da_amostra']}")
    for a in reg["avisos"]:
        print("AVISO:", a)


if __name__ == "__main__":
    main()
