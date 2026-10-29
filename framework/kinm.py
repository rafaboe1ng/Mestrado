"""KINM: Knowledge and Input Normalisation Module.

Turns the three inputs of the FDM case into records with explicit source provenance, in the shape the
group's pipeline uses for features (``id``, ``type``, ``dimensions``, ``source_file``, ``source_id``,
``match_confidence``, ``reconciliation``). There is one source per input here, so reconciliation is
``single_source`` with confidence 1.0; a second source (CAD extraction) would go through a type-gated
reconciliation before this point, as in the group's KINM.

Vocabulary crosses the language boundary here and only here: Portuguese contract fields become English
record fields; the mapping tables are the single place to change.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from pathlib import Path

from contracts.base import garantir
from contracts.produto import ProdutoFeatures
from contracts.sensores import SerieMultivariada

TYPE_MAP = {"base": "Base", "parede": "Wall", "furo": "Hole", "nervura": "Rib", "aba": "Overhang", "outro": "GenericFeature"}
DIMENSION_MAP = {"espessura_mm": "thickness_mm", "altura_mm": "height_mm", "comprimento_mm": "length_mm",
                 "largura_mm": "width_mm", "diametro_mm": "diameter_mm", "angulo_graus": "angle_deg"}
PARAMETER_MAP = {"temp_bico": "nozzle_temp", "velocidade": "print_speed", "altura_camada": "layer_height",
                 "resfriamento": "cooling_fan", "fluxo": "flow_rate", "retracao": "retraction"}


@dataclass
class FeatureRecord:
    id: int
    local_id: str
    type: str
    dimensions: dict[str, float]
    adjacent: list[str]
    source_file: str
    source_id: str
    match_confidence: float = 1.0
    reconciliation: str = "single_source"
    product_id: str = ""
    design_version: str = ""


@dataclass
class OperationLogEntry:
    entry_id: str
    feature_local_id: str | None
    start_s: float
    end_s: float
    description: str
    source: str = "operation_log"


@dataclass
class SensorSeriesRecord:
    job_id: str
    product_id: str
    design_version: str
    channels: list[str]
    rate_hz: float
    n_samples: int
    duration_s: float
    parameters_used: dict[str, float]
    source: str
    sha256: str | None = None
    extras: dict = field(default_factory=dict)


def normalise_product(produto: ProdutoFeatures, source_file: str = "feature_sheet") -> list[FeatureRecord]:
    """One record per feature, ids renumbered 1..N in sheet order (feature_<id> is the key everywhere downstream)."""
    garantir(produto)
    records = []
    for n, f in enumerate(produto.features, start=1):
        dims = {DIMENSION_MAP.get(k, k): float(v) for k, v in f.dimensoes.items()}
        records.append(FeatureRecord(n, f.id, TYPE_MAP.get(f.tipo, "GenericFeature"), dims, list(f.adjacentes), source_file, f.id,
                                     1.0, "single_source", produto.produto_id, produto.versao_design))
    return records


def normalise_operation_log(serie: SerieMultivariada) -> list[OperationLogEntry]:
    """The machine's operation log: which feature was being deposited in each time span. Empty when the
    series carries no operations; the KEFC then cannot align sensor states and halts with missing_knowledge."""
    return [OperationLogEntry(o.id, o.feature_id, float(o.inicio_s), float(o.fim_s), o.descricao) for o in serie.operacoes]


def normalise_sensor_series(serie: SerieMultivariada, source: str | Path = "") -> SensorSeriesRecord:
    garantir(serie)
    src = Path(source) if source else None
    sha = None
    if src and src.is_dir() and (src / "serie.csv").exists():
        sha = hashlib.sha256((src / "serie.csv").read_bytes()).hexdigest()
    params = {PARAMETER_MAP.get(k, k): float(v) for k, v in serie.parametros_usados.items()}
    return SensorSeriesRecord(serie.job_id, serie.produto_id, serie.versao_design, list(serie.canais), float(serie.taxa_hz),
                              int(len(serie.t)), float(serie.duracao_s), params, str(source), sha)


def to_dicts(records) -> list[dict]:
    return [asdict(r) for r in records]
