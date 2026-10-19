"""As etapas do diagnostico, uma funcao por fronteira. Cada etapa devolve um dicionario com
``etapa``, ``recebeu``, ``entregou``, ``erros`` e ``se_falhar`` (por onde comecar)."""
from __future__ import annotations

import json
from pathlib import Path

import avaliacao
import cad_features
import grafo as mod_grafo
import raciocinio
import regimes
import sensores
from processo import base_fdm_pla

CONFIG = {"largura_janela_s": 10.0, "k": 4, "semente": 0, "fator_anomalia": 2.0, "percentil_distancia": 99.0}


def diagnosticar(raiz_dados: str | Path, job_id: str | None = None, config: dict = CONFIG) -> list[dict]:
    raiz = Path(raiz_dados)
    rel: list[dict] = []
    ctx: dict = {}

    def etapa(nome: str, recebeu: str, fn, se_falhar: str) -> bool:
        try:
            entregou = fn()
            rel.append({"etapa": nome, "recebeu": recebeu, "entregou": entregou, "erros": [], "se_falhar": se_falhar})
            return True
        except Exception as e:  # noqa: BLE001 - o diagnostico existe para capturar qualquer falha
            rel.append({"etapa": nome, "recebeu": recebeu, "entregou": None, "erros": [f"{type(e).__name__}: {e}"], "se_falhar": se_falhar})
            return False

    def e_bateria():
        ctx["bateria"] = json.loads((raiz / "bateria.json").read_text(encoding="utf-8"))
        ctx["gabarito"] = json.loads((raiz / "gabarito.json").read_text(encoding="utf-8"))
        jobs = ctx["bateria"]["jobs"]
        ctx["job"] = job_id or next(j for j, i in jobs.items() if i["conjunto"] == "avaliacao")
        if ctx["job"] not in jobs:
            raise KeyError(f"job {ctx['job']} nao esta na bateria")
        ctx["calib"] = [j for j, i in jobs.items() if i["conjunto"] == "calibracao"]
        return f"{len(jobs)} jobs; alvo {ctx['job']} ({jobs[ctx['job']]['conjunto']}); {len(ctx['calib'])} de calibracao"

    def e_ficha():
        info = ctx["bateria"]["jobs"][ctx["job"]]
        ctx["produto"] = cad_features.carregar_ficha(raiz / info["ficha"])
        p = ctx["produto"]
        return f"{p.produto_id}@{p.versao_design}: {len(p.features)} features ({', '.join(f.id for f in p.features)})"

    def e_base():
        ctx["base"] = base_fdm_pla()
        b = ctx["base"]
        return f"{b.processo}/{b.material}: {len(b.parametros)} parametros, {len(b.regras)} regras, {len(b.impactos)} impactos"

    def e_serie():
        info = ctx["bateria"]["jobs"][ctx["job"]]
        ctx["serie"] = sensores.carregar(raiz / info["caso"])
        s = ctx["serie"]
        return f"{len(s.t)} amostras x {len(s.canais)} canais a {s.taxa_hz} Hz; {len(s.operacoes)} operacoes; parametros {s.parametros_usados}"

    def e_regimes():
        calib = [sensores.carregar(raiz / ctx["bateria"]["jobs"][j]["caso"]) for j in ctx["calib"]]
        modelo = regimes.ajustar(calib, largura_s=config["largura_janela_s"], k=config["k"], semente=config["semente"],
                                 fator_anomalia=config["fator_anomalia"], percentil_distancia=config["percentil_distancia"])
        ctx["estados"] = regimes.aplicar(modelo, ctx["serie"])
        e = ctx["estados"]
        return (f"{len(e.janelas)} janelas; estados {modelo.nomes_estado}; cluster de anomalia: {modelo.estado_anomalia}; "
                f"janelas anomalas: {list(e.indices_anomalos())}")

    def e_grafo():
        ctx["grafo"] = mod_grafo.construir(ctx["produto"], ctx["base"], ctx["serie"], ctx["estados"])
        r = mod_grafo.resumo(ctx["grafo"])
        m = mod_grafo.metricas_integracao(ctx["grafo"], ctx["produto"], ctx["serie"], ctx["estados"])
        return f"{m['n_nos']} nos {r['nos_por_tipo']}; {m['n_arestas']} arestas; cobertura {m['cobertura_pct']:.0f} %; proveniencia {m['proveniencia_pct']:.0f} %"

    def e_raciocinio():
        ctx["rec"] = raciocinio.recomendar(ctx["grafo"], ctx["job"])
        r = ctx["rec"]
        return (f"anomalia={r.anomalia_detectada}; causa={r.causa_feature}; regras={list(r.regras_violadas)}; "
                f"ajustes={[(a.parametro, a.de, a.para) for a in r.ajustes]}; viavel={r.viavel}; tradeoffs={r.tradeoffs}")

    def e_avaliacao():
        gj = ctx["gabarito"][ctx["job"]]
        e = avaliacao.avaliar_estados(ctx["estados"], gj)
        r = avaliacao.avaliar_recomendacao(ctx["rec"], gj, None)
        return (f"gabarito: causa={gj['causa_feature']}, regras={gj['regras_violadas']}; "
                f"anomalia F1={e['f1']:.2f} (vp={e['vp']}, fp={e['fp']}, fn={e['fn']}); pureza={e['pureza']:.2f}; causa correta={r['causa_correta']}")

    passos = [
        ("0 bateria", "dados/sintetico/bateria.json + gabarito.json", e_bateria, "rode python -m dados.sintetico.gerador"),
        ("1 cad_features", "ficha JSON do produto", e_ficha, "contracts/produto.py: ids, tipos e dimensoes da ficha"),
        ("2 processo", "base FDM/PLA embutida", e_base, "contracts/processo.py: faixas e regras da base"),
        ("3 sensores", "serie.csv + meta.json do job", e_serie, "contracts/sensores.py: tempo, canais, operacoes dentro da duracao"),
        ("4 regimes", "SerieMultivariada (calibracao + alvo)", e_regimes, "regimes.caracteristicas e nomes dos canais (temperatura, vibracao)"),
        ("5 grafo", "Produto + Base + Serie + Estados", e_grafo, "contracts/grafo.py: vocabulario de tipos/relacoes e proveniencia"),
        ("6 raciocinio", "GrafoConhecimento", e_raciocinio, "arestas requer/usa_parametro/ocorre_durante/imprime do job"),
        ("7 avaliacao", "Estados + Recomendacao + gabarito", e_avaliacao, "alinhamento das janelas (largura) e campos do gabarito"),
    ]
    for nome, recebeu, fn, se_falhar in passos:
        if not etapa(nome, recebeu, fn, se_falhar):
            break
    return rel
