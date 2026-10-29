"""Runner: one configuration, one output folder, one sub-folder per job.

Order per job (the group's order with the SPCM inserted after input normalisation):
KINM -> SPCM -> SKL repository (fails loud before anything is written) -> CFRM -> reasoning -> KEFC ->
unified graph -> RDF + SPARQL suite (assertions abort before the RAL) -> RAL -> summary.

Files per job: kinm_features.json, operation_log.json, operational_states.json, reconciled_features.json,
case_ontology.owl, reasoning_report.json, manufacturing_plan.json, expert_validation_requests.json,
unified_graph.ttl, unified_graph.json, sparql_results.json, print_profile.json, print_profile.ini,
ral_refusals.json, summary.json. The run folder gets config.json and run_summary.json.

Run: ``python -m framework.main --output runs/exemplo --jobs job_009 job_010``;
``--no-sensor-evidence`` reproduces the group's pipeline without the module (the ablation).
"""
from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cad_features
import sensores
from framework import cfrm, kinm, spcm
from framework.expert_validation import ExpertValidationStore
from framework.kefc import KEFCController
from framework.kg import build_kg, export_rdf, write_graph_files
from framework.ral import PrintProfileSerialiser
from framework.skl.repository import SKLReasonerError, SKLRepository
from framework.sparql_suite import assert_suite, run_suite, suite_summary

RAIZ = Path(__file__).resolve().parents[1]


@dataclass
class RunConfig:
    output_dir: str
    data_root: str = str(RAIZ / "dados" / "sintetico")
    jobs: list[str] | None = None                  # default: the battery's evaluation jobs
    calibration_jobs: list[str] | None = None      # default: the battery's calibration jobs
    material: str = "PLA"
    machine_key: str = "fdm_printer_lab"
    sensor_evidence: bool = True
    spcm: dict = field(default_factory=dict)
    reasoner: str = "auto"
    label: str = "reference"
    knowledge_dir: str | None = None
    rules_path: str | None = None
    drop_operation_log: bool = False               # fault injection for P14


def _dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


def load_battery(data_root: Path) -> tuple[dict, dict]:
    bateria = json.loads((data_root / "bateria.json").read_text(encoding="utf-8"))
    return bateria, bateria["jobs"]


def run_job(job_id: str, produto, serie, series_source: str, model: spcm.SPCMModel | None, cfg: RunConfig,
            out_dir: Path) -> dict:
    # SKL first: without knowledge nothing is written for this job.
    repo = SKLRepository(cfg.knowledge_dir or SKLRepository.__init__.__defaults__[0], cfg.rules_path, cfg.reasoner, case_id=job_id)
    out_dir.mkdir(parents=True, exist_ok=True)

    # KINM
    features = kinm.normalise_product(produto, source_file=f"fichas/{produto.produto_id}@{produto.versao_design}.json")
    log = [] if cfg.drop_operation_log else kinm.normalise_operation_log(serie)
    series_rec = kinm.normalise_sensor_series(serie, series_source)
    _dump(out_dir / "kinm_features.json", {"features": kinm.to_dicts(features), "sensor_series": dataclasses.asdict(series_rec)})
    _dump(out_dir / "operation_log.json", kinm.to_dicts(log))

    # SPCM
    states: list = []
    evidence: dict = {}
    if cfg.sensor_evidence:
        if model is None:
            raise ValueError("sensor evidence enabled but no SPCM model was fitted")
        states = spcm.characterise(model, serie, log, series_source)
        evidence = spcm.evidence_by_feature(states)
        _dump(out_dir / "operational_states.json", {"model": model.describe(), "states": spcm.to_dicts(states), "summary": spcm.summary(states)})

    # CFRM
    job_name = repo.assert_job(job_id)
    reconciled = cfrm.map_features(features, repo, cfg.material, cfg.machine_key, evidence)
    entry_names = cfrm.map_operation_log(log, reconciled, repo, job_name)
    state_names = cfrm.map_states(states, entry_names, repo, cfg.machine_key, job_name)
    marked = cfrm.assert_evidence(reconciled, state_names, repo)
    _dump(out_dir / "reconciled_features.json", {"features": cfrm.to_dicts(reconciled), "operation_instances": entry_names,
                                                 "state_individuals": state_names, "features_with_evidence": marked})

    # SKL reasoning
    report = repo.reason()
    repo.save_case(out_dir / "case_ontology.owl")
    _dump(out_dir / "reasoning_report.json", report)

    # KEFC
    store = ExpertValidationStore(out_dir / "expert_validation_requests.json")
    controller = KEFCController(repo, store, cfg.machine_key, sensor_evidence_enabled=cfg.sensor_evidence)
    plan = controller.build_manufacturing_plan(reconciled, cfg.material, job_id, operation_log_present=bool(log))
    _dump(out_dir / "manufacturing_plan.json", plan)

    # Unified graph, RDF, SPARQL
    G = build_kg(plan, reconciled, states, log, entry_names, state_names, repo.case_iri)
    g = export_rdf(G, out_dir / "case_ontology.owl")
    graph_info = write_graph_files(G, g, out_dir)
    context = {"sensor_evidence": cfg.sensor_evidence, "operation_log_present": bool(log),
               "has_anomalous_states": any(s.anomaly_flag for s in states), "has_evidence": bool(evidence),
               "has_recommendations": any(s["recommended_adjustments"] for s in plan["steps"])}
    results = run_suite(g, context)
    _dump(out_dir / "sparql_results.json", {"context": context, "summary": suite_summary(results), "results": results})
    assert_suite(results)

    # RAL
    ral = PrintProfileSerialiser(store).serialise(plan, out_dir)

    summary = {
        "job_id": job_id, "label": cfg.label, "sensor_evidence": cfg.sensor_evidence, "operation_log_present": bool(log),
        "features": len(features), "features_mapped": sum(1 for r in reconciled if not r.unmapped),
        "features_with_evidence": marked, "states": spcm.summary(states) if states else None,
        "reasoner": report["reasoner"], "skl_version": report["skl_version"], "inferences": report["inferences"],
        "steps": len(plan["steps"]), "approved_steps": len(plan["approved_steps"]),
        "steps_by_status": _count(s["validation_status"] for s in plan["steps"]), "halt_summary": plan["halt_summary"],
        "steps_retained_by_evidence": sorted({s["feature_local_id"] for s in plan["steps"]
                                              if any(e["reason_code"] == "anomalous_operational_state" for e in s["exceptions"])}),
        "recommended_adjustments": sum(len(s["recommended_adjustments"]) for s in plan["steps"]),
        "expert_validation": store.summary(), "graph": graph_info, "sparql": suite_summary(results),
        "ral": {k: ral[k] for k in ("handed", "serialised", "refused")},
    }
    _dump(out_dir / "summary.json", summary)
    return summary


def _count(items) -> dict:
    out: dict = {}
    for x in items:
        out[x] = out.get(x, 0) + 1
    return out


def run(cfg: RunConfig) -> dict:
    data_root = Path(cfg.data_root)
    out = Path(cfg.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    _, jobs_info = load_battery(data_root)
    calib = cfg.calibration_jobs or [j for j, i in jobs_info.items() if i["conjunto"] == "calibracao"]
    jobs = cfg.jobs or [j for j, i in jobs_info.items() if i["conjunto"] == "avaliacao"]
    started = dt.datetime.now().astimezone().isoformat(timespec="seconds")

    model = None
    if cfg.sensor_evidence:
        model = spcm.fit([sensores.carregar(data_root / jobs_info[j]["caso"]) for j in calib], cfg.spcm)

    _dump(out / "config.json", {**dataclasses.asdict(cfg), "calibration_jobs_used": calib, "jobs_run": jobs, "started": started,
                                "python": sys.version.split()[0], "platform": platform.platform(),
                                "spcm_model": model.describe() if model else None})
    per_job = {}
    for j in jobs:
        info = jobs_info[j]
        serie = sensores.carregar(data_root / info["caso"])
        produto = cad_features.carregar_ficha(data_root / info["ficha"])
        per_job[j] = run_job(j, produto, serie, str(data_root / info["caso"]), model, cfg, out / j)
    agg = {
        "label": cfg.label, "started": started, "finished": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "jobs": len(per_job), "reasoner": sorted({s["reasoner"] for s in per_job.values()}),
        "skl_version": sorted({s["skl_version"] for s in per_job.values()}),
        "steps": sum(s["steps"] for s in per_job.values()), "approved_steps": sum(s["approved_steps"] for s in per_job.values()),
        "halt_summary": _merge_counts(s["halt_summary"] for s in per_job.values()),
        "jobs_with_evidence_halts": sum(1 for s in per_job.values() if s["steps_retained_by_evidence"]),
        "recommended_adjustments": sum(s["recommended_adjustments"] for s in per_job.values()),
        "sparql_failed": sum(s["sparql"]["failed"] for s in per_job.values()),
        "ral": _merge_counts(s["ral"] for s in per_job.values()),
        "per_job": per_job,
    }
    _dump(out / "run_summary.json", agg)
    return agg


def _merge_counts(dicts) -> dict:
    out: dict = {}
    for d in dicts:
        for k, v in d.items():
            out[k] = out.get(k, 0) + v
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="run the framework on jobs of the synthetic battery")
    ap.add_argument("--output", required=True)
    ap.add_argument("--data-root", default=str(RAIZ / "dados" / "sintetico"))
    ap.add_argument("--jobs", nargs="*", default=None)
    ap.add_argument("--no-sensor-evidence", action="store_true", help="ablation: the group's pipeline without the SPCM")
    ap.add_argument("--spcm-method", default="kmeans_windows", choices=spcm.METHODS)
    ap.add_argument("--reasoner", default="auto", choices=("auto", "python", "pellet"))
    ap.add_argument("--label", default=None)
    args = ap.parse_args(argv)
    cfg = RunConfig(output_dir=args.output, data_root=args.data_root, jobs=args.jobs, sensor_evidence=not args.no_sensor_evidence,
                    spcm={"method": args.spcm_method}, reasoner=args.reasoner,
                    label=args.label or ("ablation_sensor_states" if args.no_sensor_evidence else "reference"))
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        agg = run(cfg)
    except SKLReasonerError as e:
        print(f"SKL error, no plan emitted: {e}", file=sys.stderr)
        return 2
    print(f"[{agg['label']}] jobs={agg['jobs']} reasoner={agg['reasoner']} steps={agg['steps']} approved={agg['approved_steps']} "
          f"halts={agg['halt_summary']} evidence_jobs={agg['jobs_with_evidence_halts']} sparql_failed={agg['sparql_failed']} ral={agg['ral']}")
    print(f"output: {cfg.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
