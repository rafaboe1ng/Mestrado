"""exp02: the framework (group's architecture + SPCM) on the synthetic battery, three configurations.

- ``reference``: KINM -> SPCM (k-means windows) -> CFRM -> SKL -> KEFC -> graph/RDF/SPARQL -> RAL.
- ``ablation_sensor_states``: the same without the SPCM, i.e. the group's pipeline on the FDM case.
- ``reference_threshold``: SPCM with the robust threshold baseline instead of k-means (same gate).

Metrics for P11-P14 (PLANO): anomalous states linked to an operation instance by SPARQL; evidence
accuracy of the gate against the battery's answer key (set of features whose deposition overlaps an
injected anomaly); adjustments with full provenance; approved parameter records identical to the
ablation; fault injections that fail loud. All numbers carry the SINTETICO label.

Run: ``python -m experimentos.exp02_framework_fdm`` (run folders under ``runs/exp02/``, result JSON under
``resultados/`` with provenance).
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

from rdflib import Graph

import cad_features
import sensores
from experimentos import proveniencia
from framework.main import RunConfig, run, run_job
from framework.skl.build_ontologies import KNOWLEDGE_DIR, file_name
from framework.skl.repository import SKLReasonerError
from framework.sparql_suite import PREFIXES

RAIZ = Path(__file__).resolve().parents[1]
NOME = "exp02_framework_fdm"
RUNS = RAIZ / "runs" / "exp02"
CONFIGS = {
    "reference": {"sensor_evidence": True, "spcm": {"method": "kmeans_windows"}},
    "ablation_sensor_states": {"sensor_evidence": False},
    "reference_threshold": {"sensor_evidence": True, "spcm": {"method": "robust_threshold"}},
}
COUNT_ANOMALOUS = PREFIXES + "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?st a mfg:OperationalState ; mfg:anomalyFlag true . }"
COUNT_LINKED = PREFIXES + "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?st a mfg:OperationalState ; mfg:anomalyFlag true ; mfg:observedDuring ?x . }"
COUNT_LINKED_FEATURE = PREFIXES + "SELECT (COUNT(DISTINCT ?st) AS ?n) WHERE { ?st a mfg:OperationalState ; mfg:anomalyFlag true ; mfg:observedDuring ?x . ?x mfg:deposits ?f . }"


def _count(g: Graph, q: str) -> int:
    return int(next(iter(g.query(q)))[0])


def expected_evidence_features(gab_job: dict, operation_log: list[dict]) -> set[str]:
    """Features whose deposition window overlaps an injected anomaly (the mechanism's ground truth)."""
    out: set[str] = set()
    for a in gab_job["anomalias"]:
        for e in operation_log:
            if e["feature_local_id"] and min(a["fim_s"], e["end_s"]) - max(a["inicio_s"], e["start_s"]) > 0:
                out.add(e["feature_local_id"])
    return out


def analyse(label: str, out: Path, gabarito: dict) -> dict:
    summary = json.loads((out / "run_summary.json").read_text(encoding="utf-8"))
    jobs = summary["per_job"]
    anomalous = linked = linked_feature = 0
    correct = 0
    agree_cause = 0
    adjustments = adjustments_ok = 0
    evidence_halts = 0
    per_job = {}
    for j, s in jobs.items():
        log = json.loads((out / j / "operation_log.json").read_text(encoding="utf-8"))
        plan = json.loads((out / j / "manufacturing_plan.json").read_text(encoding="utf-8"))
        g = Graph().parse(str(out / j / "unified_graph.ttl"), format="turtle")
        anomalous += _count(g, COUNT_ANOMALOUS)
        linked += _count(g, COUNT_LINKED)
        linked_feature += _count(g, COUNT_LINKED_FEATURE)
        retained = set(s["steps_retained_by_evidence"])
        expected = expected_evidence_features(gabarito[j], log)
        correct += retained == expected
        agree_cause += (gabarito[j]["causa_feature"] in retained) if gabarito[j]["causa_feature"] else (not retained)
        for st in plan["steps"]:
            evidence_halts += any(e["reason_code"] == "anomalous_operational_state" for e in st["exceptions"])
            for adj in st["recommended_adjustments"]:
                adjustments += 1
                adjustments_ok += bool(adj["rule_id"] and adj["ontology_sources"] and adj["evidence_state_ids"] and adj["request_id"])
        per_job[j] = {"retained": sorted(retained), "expected": sorted(expected), "causa_gabarito": gabarito[j]["causa_feature"],
                      "status": s["steps_by_status"], "halts": s["halt_summary"]}
    n = len(jobs)
    return {
        "label": label, "n_jobs": n, "reasoner": summary["reasoner"], "skl_version": summary["skl_version"],
        "steps": summary["steps"], "approved_steps": summary["approved_steps"], "halt_summary": summary["halt_summary"],
        "requests_total": sum(s["expert_validation"]["total_requests"] for s in jobs.values()),
        "sparql_failed": summary["sparql_failed"], "ral": summary["ral"],
        "estados_anomalos": anomalous, "estados_anomalos_ligados_pct": (100.0 * linked / anomalous) if anomalous else None,
        "estados_anomalos_com_feature_pct": (100.0 * linked_feature / anomalous) if anomalous else None,
        "acuracia_evidencia": correct / n if n else None, "concordancia_causa_gabarito": agree_cause / n if n else None,
        "passos_retidos_por_evidencia": evidence_halts,
        "ajustes_recomendados": adjustments, "ajustes_com_proveniencia_pct": (100.0 * adjustments_ok / adjustments) if adjustments else None,
        "por_job": per_job,
    }


def records_equal(a: Path, b: Path, jobs: list[str]) -> bool:
    for j in jobs:
        pa = json.loads((a / j / "manufacturing_plan.json").read_text(encoding="utf-8"))
        pb = json.loads((b / j / "manufacturing_plan.json").read_text(encoding="utf-8"))
        ka = {(s["feature_local_id"], s["operation"]): s["parameters"] for s in pa["steps"]}
        kb = {(s["feature_local_id"], s["operation"]): s["parameters"] for s in pb["steps"]}
        if ka != kb:
            return False
    return True


def fault_injections(data_root: Path, jobs_info: dict) -> dict:
    """P14: each injection must raise before any plan file exists, or halt every step."""
    job = next(j for j, i in jobs_info.items() if i["conjunto"] == "avaliacao")
    serie = sensores.carregar(data_root / jobs_info[job]["caso"])
    produto = cad_features.carregar_ficha(data_root / jobs_info[job]["ficha"])
    results = {}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        kd = tmp / "k"
        shutil.copytree(KNOWLEDGE_DIR, kd)
        (kd / file_name("additive_parameters")).unlink()
        bad = tmp / "bad.swrl"
        bad.write_text("r: Wall(?f) ^ greaterThan(?t, 1.2) -> requiresOperation(?f, WallDepositionOp)\n", encoding="utf-8")
        cases = {
            "rules_missing": {"rules_path": str(tmp / "none.swrl")},
            "ontology_missing": {"knowledge_dir": str(kd)},
            "rule_malformed": {"rules_path": str(bad)},
            "pellet_without_java": {"reasoner": "pellet"},
        }
        for name, kw in cases.items():
            out = tmp / name
            kw.setdefault("reasoner", "python")
            cfg = RunConfig(output_dir=str(tmp), sensor_evidence=False, **kw)
            if name == "pellet_without_java" and shutil.which("java"):
                results[name] = "skipped (java present)"
                continue
            try:
                run_job(job, produto, serie, "", None, cfg, out)
                results[name] = "FAILED: plan emitted"
            except SKLReasonerError:
                results[name] = "passed" if not (out / "manufacturing_plan.json").exists() else "FAILED: plan file written"
        # operation log missing with sensors on: every step halts, nothing serialised
        from framework import spcm
        calib = [sensores.carregar(data_root / i["caso"]) for j, i in jobs_info.items() if i["conjunto"] == "calibracao"]
        model = spcm.fit(calib, {"method": "kmeans_windows"})
        cfg = RunConfig(output_dir=str(tmp), sensor_evidence=True, reasoner="python", drop_operation_log=True)
        s = run_job(job, produto, serie, "", model, cfg, tmp / "no_log")
        results["operation_log_missing"] = "passed" if (s["approved_steps"] == 0 and s["ral"]["serialised"] == 0) else "FAILED"
    passed = sum(1 for v in results.values() if v == "passed")
    counted = sum(1 for v in results.values() if not v.startswith("skipped"))
    return {"casos": results, "testes_falha_alta_passando": passed / counted if counted else None}


def executar(data_root: Path = RAIZ / "dados" / "sintetico", runs: Path = RUNS) -> dict:
    gabarito = json.loads((data_root / "gabarito.json").read_text(encoding="utf-8"))
    bateria = json.loads((data_root / "bateria.json").read_text(encoding="utf-8"))
    if runs.exists():
        shutil.rmtree(runs)
    resultado: dict = {}
    outs = {}
    for label, cfgd in CONFIGS.items():
        cfg = RunConfig(output_dir=str(runs / label), data_root=str(data_root), label=label, reasoner="auto", **cfgd)
        run(cfg)
        outs[label] = runs / label
        resultado[label] = analyse(label, runs / label, gabarito)
    jobs = list(resultado["reference"]["por_job"])
    resultado["reference"]["registros_parametro_iguais_a_ablacao"] = records_equal(outs["reference"], outs["ablation_sensor_states"], jobs)
    resultado["reference_threshold"]["registros_parametro_iguais_a_ablacao"] = records_equal(outs["reference_threshold"], outs["ablation_sensor_states"], jobs)
    fi = fault_injections(data_root, bateria["jobs"])
    resultado["reference"]["testes_falha_alta_passando"] = fi["testes_falha_alta_passando"]
    resultado["injecoes_de_falha"] = fi["casos"]
    resultado["config"] = {"configs": CONFIGS, "jobs_avaliacao": jobs, "pasta_runs": str(runs.relative_to(RAIZ))}
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
    caminho = proveniencia.registrar(NOME, r, comando=f"python -m experimentos.{NOME}",
                                     dados=[RAIZ / "dados" / "sintetico", KNOWLEDGE_DIR])
    cols = ("steps", "approved_steps", "passos_retidos_por_evidencia", "acuracia_evidencia", "estados_anomalos_ligados_pct",
            "ajustes_com_proveniencia_pct", "sparql_failed", "requests_total")
    print(f"[{r['rotulo']}] jobs: {len(r['config']['jobs_avaliacao'])} | reasoner: {r['reference']['reasoner']}")
    print("config".ljust(26) + "".join(c[:18].ljust(20) for c in cols))
    for label in CONFIGS:
        print(label.ljust(26) + "".join(_fmt(r[label].get(c)).ljust(20) for c in cols))
    print(f"registros iguais a ablacao: {r['reference']['registros_parametro_iguais_a_ablacao']} | falha alta: {r['reference']['testes_falha_alta_passando']} {r['injecoes_de_falha']}")
    reg = json.loads(caminho.read_text(encoding="utf-8"))
    print(f"gravado em {caminho.relative_to(RAIZ)} | execucao {reg['execucao_numero_para_estes_dados']} | fora da amostra: {reg['vale_como_fora_da_amostra']}")
    for a in reg["avisos"]:
        print("AVISO:", a)


if __name__ == "__main__":
    main()
