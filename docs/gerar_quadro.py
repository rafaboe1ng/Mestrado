"""Gera docs/quadro_validacao.md e docs/guia_avaliador.md a partir de experimentos/obrigacoes.json
e do ultimo JSON de cada experimento em resultados/. Nao se edita o que sai daqui a mao.

Rodar: ``python docs/gerar_quadro.py``.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from experimentos.proveniencia import PASTA_RESULTADOS  # noqa: E402


def buscar(d, caminho: str):
    for parte in caminho.split("."):
        if not isinstance(d, dict) or parte not in d:
            return None
        d = d[parte]
    return d


def fmt(v) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.3f}"
    return str(v)


def avaliar(crit: dict, valor, base) -> tuple[str, str]:
    t = crit["tipo"]
    if t == "a_fixar":
        return "pendente", crit.get("nota", "critério a fixar")
    if t == "max":
        texto = f"≤ {crit['valor']}"
        return ("pendente" if valor is None else ("atendida" if valor <= crit["valor"] else "não atendida")), texto
    if t == "min":
        texto = f"≥ {crit['valor']}"
        return ("pendente" if valor is None else ("atendida" if valor >= crit["valor"] else "não atendida")), texto
    if t == "min_e_margem":
        texto = f"≥ {crit['minimo']} e ≥ baseline + {crit['margem']}"
        if valor is None or base is None:
            return "pendente", texto
        ok = valor >= crit["minimo"] and valor >= base + crit["margem"]
        return ("atendida" if ok else "não atendida"), texto
    return "pendente", f"tipo de critério desconhecido: {t}"


def ultimo_arquivo(experimento: str) -> Path | None:
    c = sorted(PASTA_RESULTADOS.glob(f"{experimento}__*.json"))
    return c[-1] if c else None


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    obr = json.loads((RAIZ / "experimentos" / "obrigacoes.json").read_text(encoding="utf-8"))
    plano = (RAIZ / "PLANO.md").read_text(encoding="utf-8")
    agora = dt.datetime.now().astimezone().isoformat(timespec="minutes")
    avisos: list[str] = []
    registros: dict[str, dict] = {}
    linhas = [
        "# Quadro de validação",
        "",
        f"Gerado por `docs/gerar_quadro.py` em {agora}. **Não editar à mão.** Critérios declarados em {obr['declarado_em']} (`experimentos/obrigacoes.json`, espelho do `PLANO.md`).",
        "",
        "| Obrigação | Métrica | Valor | Baseline | Critério | Status | Execução | Fonte |",
        "|---|---|---|---|---|---|---|---|",
    ]
    contagem: dict[str, int] = {}
    guia = [
        "# Guia do avaliador externo",
        "",
        f"Gerado por `docs/gerar_quadro.py` em {agora}. **Não editar à mão.**",
        "",
        "Para cada obrigação do `PLANO.md`: como reproduzir o número, onde ele está gravado e o que inspecionar à mão.",
        "Tudo que vem da bateria sintética leva o rótulo SINTÉTICO e não vale como evidência sobre a impressora (PLANO, P3).",
        "",
    ]
    for o in obr["obrigacoes"]:
        if f"### {o['id']} " not in plano:
            avisos.append(f"{o['id']} não encontrada no PLANO.md")
        arq = ultimo_arquivo(o["experimento"])
        reg = None
        if arq is not None:
            reg = registros.get(arq.name) or json.loads(arq.read_text(encoding="utf-8"))
            registros[arq.name] = reg
        res = reg["resultado"] if reg else None
        valor = buscar(res, o["metrica"]) if res else None
        base = buscar(res, o["baseline"]) if (res and o.get("baseline")) else None
        status, texto = avaliar(o["criterio"], valor, base)
        contagem[status] = contagem.get(status, 0) + 1
        if reg:
            execucao = f"#{reg['execucao_numero_para_estes_dados']}"
            execucao += " · fora da amostra" if reg["vale_como_fora_da_amostra"] else " · repetição"
            if reg["git"].get("sujo"):
                execucao += " · ⚠ não commitado"
            if res and res.get("rotulo"):
                execucao += f" · {res['rotulo']}"
            fonte = f"`resultados/{arq.name}`"
        else:
            execucao, fonte = "—", f"experimento `{o['experimento']}` ainda não existe"
        linhas.append(f"| {o['id']} {o['titulo']} | `{o['metrica']}` | {fmt(valor)} | {fmt(base)} | {texto} | **{status}** | {execucao} | {fonte} |")

        guia += [f"## {o['id']} — {o['titulo']}", "",
                 f"- Reproduzir: `python -m experimentos.{o['experimento']}` e depois `python docs/gerar_quadro.py`.",
                 f"- Número: `resultado.{o['metrica']}` em {fonte}." + (f" Baseline: `resultado.{o['baseline']}`." if o.get("baseline") else ""),
                 f"- Critério declarado: {texto}. Status atual: **{status}**."]
        if o["id"] in ("P2", "P8") and res and res.get("explicacoes_proposto"):
            guia.append("- Inspeção manual: leia as explicações abaixo e anote, para cada uma, se o caminho faz sentido e se cada passo diz de onde veio (nota 0–2).")
            n = 0
            for job, ex in res["explicacoes_proposto"].items():
                if not ex.get("causa"):
                    continue
                guia.append(f"  - **{job}** → causa `{ex['causa']}`, regras {ex['regras']}, ajustes {[(a['parametro'], a['de'], a['para']) for a in ex['ajustes']]}, trade-offs {ex['tradeoffs']}")
                for p in ex["passos"]:
                    guia.append(f"    - {p}")
                n += 1
                if n >= 5:
                    break
        guia.append("")

    linhas += ["", "## Resumo", ""]
    for k in ("atendida", "não atendida", "pendente"):
        linhas.append(f"- {k}: {contagem.get(k, 0)}")
    exp01 = registros.get((ultimo_arquivo("exp01_pipeline_sintetico") or Path("x")).name)
    if exp01:
        r = exp01["resultado"]
        metodos = [m for m in ("proposto", "baseline_limiar", "baseline_geometrico", "baseline_temporal") if m in r]
        cols = ("anomalia_f1", "pureza_media", "acuracia_causa", "taxa_viavel", "taxa_resolve", "taxa_tradeoffs", "taxa_explicacao_completa", "delta_tempo_medio_pct")
        linhas += ["", f"## Métodos lado a lado — exp01 ({r.get('rotulo', '')}, commit {str(exp01['git'].get('commit'))[:8]}, execução #{exp01['execucao_numero_para_estes_dados']})", "",
                   "| método | " + " | ".join(cols) + " |", "|---|" + "---|" * len(cols)]
        for m in metodos:
            linhas.append(f"| {m} | " + " | ".join(fmt(r[m].get(c)) for c in cols) + " |")
    if avisos:
        linhas += ["", "## Avisos", ""] + [f"- {a}" for a in avisos]
    (RAIZ / "docs" / "quadro_validacao.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    (RAIZ / "docs" / "guia_avaliador.md").write_text("\n".join(guia) + "\n", encoding="utf-8")
    print("gerados: docs/quadro_validacao.md, docs/guia_avaliador.md |", ", ".join(f"{k}={v}" for k, v in contagem.items()))
    for a in avisos:
        print("AVISO:", a)


if __name__ == "__main__":
    main()
