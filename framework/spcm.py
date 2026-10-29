"""SPCM: Sensor-driven Process Characterisation Module (the module this master's adds to the framework).

Input: the sensor series of a job and its operation log (from KINM). Output: operational-state records,
each a contiguous span of windows with the same (state, anomaly) label, carrying the method that
produced it, its configuration, the windows it covers, the series it came from, and the operation-log
entries it overlaps. Nothing here decides anything about the plan: states are evidence, asserted into the
SKL by the CFRM and weighed by the KEFC.

The clustering itself lives in the ``regimes`` module (own k-means and the robust threshold baseline);
this module is the adapter that gives its output the framework's shape and the time alignment with the
operation log. Labels are translated once here (``LABEL_MAP``).
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

import regimes
from contracts.estados import EstadosOperacionais
from contracts.sensores import SerieMultivariada
from framework.kinm import OperationLogEntry

LABEL_MAP = {"aquecimento": "heating", "impressao": "printing", "anomalia": "anomaly", "resfriamento": "cooling",
             "fora_do_padrao": "off_pattern"}
METHODS = ("kmeans_windows", "robust_threshold")
DEFAULT_CONFIG = {"method": "kmeans_windows", "window_s": 10.0, "k": 4, "seed": 0, "anomaly_factor": 2.0,
                  "distance_percentile": 99.0, "threshold_n_mad": 3.0, "min_overlap_s": 10.0}


def translate_label(nome: str) -> str:
    if nome in LABEL_MAP:
        return LABEL_MAP[nome]
    if nome.startswith("impressao_"):
        return "printing_" + nome.split("_", 1)[1]
    return nome


@dataclass
class SPCMModel:
    method: str
    config: dict
    calibration_jobs: list[str]
    regimes_model: object | None = None     # regimes.ModeloRegimes for kmeans_windows
    threshold: float | None = None          # vibration-std threshold for robust_threshold

    def describe(self) -> dict:
        d = {"method": self.method, "config": self.config, "calibration_jobs": self.calibration_jobs}
        if self.regimes_model is not None:
            m = self.regimes_model
            d["state_names"] = {str(k): translate_label(v) for k, v in m.nomes_estado.items()}
            d["anomaly_state"] = m.estado_anomalia
            d["distance_threshold"] = m.limiar_distancia
        if self.threshold is not None:
            d["vibration_std_threshold"] = self.threshold
        return d


@dataclass
class OperationalStateRecord:
    state_id: str
    job_id: str
    label: str
    kind: str                          # anomaly | stable_pattern
    start_s: float
    end_s: float
    window_count: int
    window_indices: list[int]
    anomaly_flag: bool
    anomaly_score: float
    method_id: str
    method_config: dict
    derived_from_series: str
    overlaps: list[dict] = field(default_factory=list)      # {entry_id, feature_local_id, overlap_s}
    transitions_to: str | None = None


def fit(series: list[SerieMultivariada], config: dict | None = None) -> SPCMModel:
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    if cfg["method"] not in METHODS:
        raise ValueError(f"unknown SPCM method {cfg['method']!r}; known: {METHODS}")
    if not series:
        raise ValueError("SPCM fit: no calibration series")
    jobs = [s.job_id for s in series]
    if cfg["method"] == "kmeans_windows":
        m = regimes.ajustar(series, largura_s=cfg["window_s"], k=cfg["k"], semente=cfg["seed"],
                            fator_anomalia=cfg["anomaly_factor"], percentil_distancia=cfg["distance_percentile"])
        return SPCMModel("kmeans_windows", cfg, jobs, regimes_model=m)
    thr = regimes.calibrar_limiar(series, largura_s=cfg["window_s"], n_desvios=cfg["threshold_n_mad"], robusto=True)
    return SPCMModel("robust_threshold", cfg, jobs, threshold=thr)


def _states_of(model: SPCMModel, serie: SerieMultivariada) -> EstadosOperacionais:
    if model.method == "kmeans_windows":
        return regimes.aplicar(model.regimes_model, serie)
    return regimes.baseline_limiar(serie, model.config["window_s"], model.threshold)


def _overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def characterise(model: SPCMModel, serie: SerieMultivariada, operation_log: list[OperationLogEntry],
                 series_source: str = "") -> list[OperationalStateRecord]:
    """Segments the window labels into states and aligns each state with the operation log.
    A state overlaps an entry when the shared time is at least ``min_overlap_s``."""
    est = _states_of(model, serie)
    min_overlap = float(model.config["min_overlap_s"])
    method_config = {k: v for k, v in est.config.items() if k != "estado_anomalia"}
    method_config["min_overlap_s"] = min_overlap
    derived = series_source or serie.job_id
    segments: list[list] = []
    for j in est.janelas:
        key = (j.estado, j.anomalia)
        if segments and segments[-1][0] == key:
            segments[-1][1].append(j)
        else:
            segments.append([key, [j]])
    records: list[OperationalStateRecord] = []
    for n, ((estado, anomalia), janelas) in enumerate(segments):
        start, end = float(janelas[0].inicio_s), float(janelas[-1].fim_s)
        overlaps = []
        for e in operation_log:
            ov = _overlap(start, end, e.start_s, e.end_s)
            if ov >= min_overlap - 1e-9:
                overlaps.append({"entry_id": e.entry_id, "feature_local_id": e.feature_local_id, "overlap_s": ov})
        label = translate_label(est.nomes_estado[estado])
        records.append(OperationalStateRecord(
            state_id=f"state_{serie.job_id}_{n}", job_id=serie.job_id, label=label,
            kind="anomaly" if anomalia else "stable_pattern", start_s=start, end_s=end, window_count=len(janelas),
            window_indices=[j.indice for j in janelas], anomaly_flag=bool(anomalia),
            anomaly_score=float(max(j.score for j in janelas)), method_id=est.metodo, method_config=method_config,
            derived_from_series=str(derived), overlaps=overlaps,
        ))
    for a, b in zip(records, records[1:]):
        a.transitions_to = b.state_id
    return records


def evidence_by_feature(states: list[OperationalStateRecord]) -> dict[str, list[str]]:
    """feature local id -> anomalous states observed during an operation that deposits it."""
    out: dict[str, list[str]] = {}
    for s in states:
        if not s.anomaly_flag:
            continue
        for ov in s.overlaps:
            fid = ov["feature_local_id"]
            if fid is None:
                continue
            out.setdefault(fid, [])
            if s.state_id not in out[fid]:
                out[fid].append(s.state_id)
    return out


def to_dicts(states: list[OperationalStateRecord]) -> list[dict]:
    return [asdict(s) for s in states]


def summary(states: list[OperationalStateRecord]) -> dict:
    anomalous = [s for s in states if s.anomaly_flag]
    linked = [s for s in anomalous if any(o["feature_local_id"] for o in s.overlaps)]
    return {"states": len(states), "anomalous_states": len(anomalous), "anomalous_states_linked_to_feature": len(linked),
            "labels": sorted({s.label for s in states})}


def dumps(states: list[OperationalStateRecord]) -> str:
    return json.dumps(to_dicts(states), indent=2, ensure_ascii=False)
