"""Writes the OWL files of ``framework/skl/knowledge/`` from Python definitions (owlready2).

Five foundation ontologies, as in the group's SKL, under sibling namespaces of
``http://onto.brep.org/manufacturing/``:

- additive-process     feature classes (with disjoint qualifier leaves), deposition operations with
                       precedence, the evidence class asserted from sensor states
- additive-materials   PLA and PETG with nozzle-temperature ranges
- additive-machines    the laboratory FDM printer: supported operations and safety limits
- additive-parameters  parameter sets (nozzle temperature, print speed, layer height, cooling,
                       flow, retraction) per material and feature class, plus recovery sets
- operational-states   operational states, operation instances and the properties that link a
                       state to the operation during which it was observed

The case ontology (one per run) is created by the repository, never saved here.
Run: ``python -m framework.skl.build_ontologies``.
"""
from __future__ import annotations

from pathlib import Path

from owlready2 import (AllDisjoint, AnnotationProperty, DataProperty, FunctionalProperty, ObjectProperty, Thing,
                       World)

NS = "http://onto.brep.org/manufacturing"
KNOWLEDGE_DIR = Path(__file__).resolve().parent / "knowledge"
FOUNDATION = ("additive_process", "additive_materials", "additive_machines", "additive_parameters", "operational_states")
IRIS = {
    "additive_process": f"{NS}/additive-process#",
    "additive_materials": f"{NS}/additive-materials#",
    "additive_machines": f"{NS}/additive-machines#",
    "additive_parameters": f"{NS}/additive-parameters#",
    "operational_states": f"{NS}/operational-states#",
}
def file_name(name: str) -> str:
    """OWL file named after the last segment of its IRI, so owlready2 can resolve imports from the folder."""
    return IRIS[name].rsplit("/", 1)[-1].rstrip("#") + ".owl"


A_CONFIRMAR = "common FDM practice; to be confirmed by trials or a cited source before P9"

# Parameter sets: (nozzle_temp C, print_speed mm/s, layer_height mm, cooling_fan %, flow_rate %, retraction mm)
PARAMETER_SETS = {
    # name: (material, operation, values, note)
    "PLA_Base_Params": ("PLA", "BaseDepositionOp", (210, 50, 0.2, 100, 100, 5), "default set"),
    "PLA_StandardWall_Params": ("PLA", "WallDepositionOp", (210, 50, 0.2, 100, 100, 5), "default set"),
    "PLA_ThinWall_Params": ("PLA", "WallDepositionOp", (210, 45, 0.2, 100, 100, 5), "R1: thin wall needs speed <= 45; R2: cooling >= 60"),
    "PLA_StandardHole_Params": ("PLA", "HoleDepositionOp", (210, 50, 0.2, 100, 100, 5), "default set"),
    "PLA_SmallHole_Params": ("PLA", "HoleDepositionOp", (210, 50, 0.2, 100, 100, 5), "R4: small hole needs flow <= 100"),
    "PLA_StandardRib_Params": ("PLA", "RibDepositionOp", (210, 50, 0.2, 100, 100, 5), "default set"),
    "PLA_ThinRib_Params": ("PLA", "RibDepositionOp", (210, 40, 0.2, 100, 100, 5), "R5: thin rib needs speed <= 40"),
    "PLA_StandardOverhang_Params": ("PLA", "OverhangDepositionOp", (210, 50, 0.2, 100, 100, 5), "default set"),
    "PLA_SteepOverhang_Params": ("PLA", "OverhangDepositionOp", (210, 50, 0.2, 100, 100, 5), "R3: steep overhang needs speed <= 50"),
    # recovery sets, recommended only when an anomalous deposition state was observed
    "PLA_ThinWall_Recovery_Params": ("PLA", "WallDepositionOp", (205, 35, 0.2, 100, 100, 5), "recovery after anomalous deposition of a thin wall"),
    "PLA_Wall_Recovery_Params": ("PLA", "WallDepositionOp", (210, 45, 0.2, 100, 100, 5), "recovery after anomalous deposition of a wall"),
    "PLA_SteepOverhang_Recovery_Params": ("PLA", "OverhangDepositionOp", (210, 40, 0.2, 100, 100, 5), "recovery after anomalous deposition of a steep overhang"),
    "PLA_Overhang_Recovery_Params": ("PLA", "OverhangDepositionOp", (210, 45, 0.2, 100, 100, 5), "recovery after anomalous deposition of an overhang"),
    "PLA_ThinRib_Recovery_Params": ("PLA", "RibDepositionOp", (210, 35, 0.2, 100, 100, 5), "recovery after anomalous deposition of a thin rib"),
}
PARAMETER_NAMES = ("nozzle_temp", "print_speed", "layer_height", "cooling_fan", "flow_rate", "retraction")
PARAMETER_UNITS = {"nozzle_temp": "C", "print_speed": "mm/s", "layer_height": "mm", "cooling_fan": "%", "flow_rate": "%", "retraction": "mm"}
PARAMETER_PROPS = {"nozzle_temp": "hasNozzleTemp", "print_speed": "hasPrintSpeed", "layer_height": "hasLayerHeight",
                   "cooling_fan": "hasCoolingFan", "flow_rate": "hasFlowRate", "retraction": "hasRetraction"}

MACHINES = {
    "fdm_printer_lab": {
        "individual": "FdmPrinterLab", "model": "laboratory FDM printer (to be named at collection)",
        "operations": ("BaseDepositionOp", "WallDepositionOp", "HoleDepositionOp", "RibDepositionOp", "OverhangDepositionOp"),
        "limits": {"hasSafetyMaxNozzleTemp": 230.0, "hasSafetyMinNozzleTemp": 190.0, "hasSafetyMaxPrintSpeed": 100.0,
                   "hasSafetyMaxLayerHeight": 0.3, "hasSafetyMinLayerHeight": 0.1, "hasSafetyMaxFlowRate": 115.0,
                   "hasSafetyMaxRetraction": 8.0},
    },
}
MATERIALS = {"PLA": (190.0, 230.0), "PETG": (220.0, 250.0)}


def build_all(dest: Path = KNOWLEDGE_DIR) -> dict[str, Path]:
    dest.mkdir(parents=True, exist_ok=True)
    world = World()
    written: dict[str, Path] = {}

    # --- additive-process ----------------------------------------------------------------
    proc = world.get_ontology(IRIS["additive_process"])
    with proc:
        class Feature(Thing): pass
        class Base(Feature): pass
        class Wall(Feature): pass
        class StandardWall(Wall): pass
        class ThinWall(Wall): pass
        class Hole(Feature): pass
        class StandardHole(Hole): pass
        class SmallHole(Hole): pass
        class Rib(Feature): pass
        class StandardRib(Rib): pass
        class ThinRib(Rib): pass
        class Overhang(Feature): pass
        class StandardOverhang(Overhang): pass
        class SteepOverhang(Overhang): pass
        class GenericFeature(Feature): pass
        class FeatureWithAnomalousDeposition(Feature): pass
        AllDisjoint([StandardWall, ThinWall])
        AllDisjoint([StandardHole, SmallHole])
        AllDisjoint([StandardRib, ThinRib])
        AllDisjoint([StandardOverhang, SteepOverhang])
        AllDisjoint([Base, Wall, Hole, Rib, Overhang])

        class Operation(Thing): pass
        class DepositionOp(Operation): pass

        class requiresOperation(ObjectProperty):
            domain = [Feature]; range = [Operation]
        class hasPrecedenceOrder(DataProperty, FunctionalProperty):
            domain = [Operation]; range = [int]
        class hasRuleSource(AnnotationProperty): pass
        class hasQualifierRule(AnnotationProperty): pass

        for name, prec in (("BaseDepositionOp", 10), ("WallDepositionOp", 20), ("RibDepositionOp", 25),
                           ("HoleDepositionOp", 30), ("OverhangDepositionOp", 40)):
            op = DepositionOp(name)
            op.hasPrecedenceOrder = prec
        FeatureWithAnomalousDeposition.comment = ["Asserted by the sensor-driven process characterisation module when an anomalous operational state overlaps the operation instance that deposits the feature."]
    written["additive_process"] = dest / file_name("additive_process")
    proc.save(file=str(written["additive_process"]), format="rdfxml")

    # --- additive-materials --------------------------------------------------------------
    mat = world.get_ontology(IRIS["additive_materials"])
    mat.imported_ontologies.append(proc)
    with mat:
        class Material(Thing): pass
        class madeOfMaterial(ObjectProperty, FunctionalProperty):
            domain = [proc.Feature]; range = [Material]
        class hasRecommendedNozzleTempMin(DataProperty, FunctionalProperty):
            range = [float]
        class hasRecommendedNozzleTempMax(DataProperty, FunctionalProperty):
            range = [float]
        for name, (lo, hi) in MATERIALS.items():
            m = Material(name)
            m.hasRecommendedNozzleTempMin = lo
            m.hasRecommendedNozzleTempMax = hi
    written["additive_materials"] = dest / file_name("additive_materials")
    mat.save(file=str(written["additive_materials"]), format="rdfxml")

    # --- additive-machines ---------------------------------------------------------------
    mach = world.get_ontology(IRIS["additive_machines"])
    mach.imported_ontologies.append(proc)
    with mach:
        class Machine(Thing): pass
        class FdmPrinter(Machine): pass
        class supportsOperation(ObjectProperty):
            domain = [Machine]; range = [proc.Operation]
        class printedOn(ObjectProperty, FunctionalProperty):
            domain = [proc.Feature]; range = [Machine]
        class hasModel(DataProperty, FunctionalProperty):
            range = [str]
        limit_props = {}
        for pname in ("hasSafetyMaxNozzleTemp", "hasSafetyMinNozzleTemp", "hasSafetyMaxPrintSpeed", "hasSafetyMaxLayerHeight",
                      "hasSafetyMinLayerHeight", "hasSafetyMaxFlowRate", "hasSafetyMaxRetraction"):
            limit_props[pname] = type(pname, (DataProperty, FunctionalProperty), {"range": [float], "namespace": mach})
        for key, spec in MACHINES.items():
            m = FdmPrinter(spec["individual"])
            m.hasModel = spec["model"]
            for opname in spec["operations"]:
                m.supportsOperation.append(proc[opname])
            for pname, val in spec["limits"].items():
                setattr(m, pname, float(val))
    written["additive_machines"] = dest / file_name("additive_machines")
    mach.save(file=str(written["additive_machines"]), format="rdfxml")

    # --- additive-parameters -------------------------------------------------------------
    par = world.get_ontology(IRIS["additive_parameters"])
    par.imported_ontologies.extend([proc, mat])
    with par:
        class ParameterSet(Thing): pass
        class requiresParameterSet(ObjectProperty):
            domain = [proc.Feature]; range = [ParameterSet]
        class recommendsParameterSet(ObjectProperty):
            domain = [proc.Feature]; range = [ParameterSet]
        class forOperation(ObjectProperty, FunctionalProperty):
            domain = [ParameterSet]; range = [proc.Operation]
        class forMaterial(ObjectProperty, FunctionalProperty):
            domain = [ParameterSet]; range = [mat.Material]
        class hasNote(AnnotationProperty): pass
        dprops = {}
        for pname in PARAMETER_PROPS.values():
            dprops[pname] = type(pname, (DataProperty, FunctionalProperty), {"range": [float], "namespace": par})
        for name, (material, operation, values, note) in PARAMETER_SETS.items():
            ps = ParameterSet(name)
            ps.forMaterial = mat[material]
            ps.forOperation = proc[operation]
            for pkey, val in zip(PARAMETER_NAMES, values):
                setattr(ps, PARAMETER_PROPS[pkey], float(val))
            ps.hasNote = [f"{note}; {A_CONFIRMAR}"]
    written["additive_parameters"] = dest / file_name("additive_parameters")
    par.save(file=str(written["additive_parameters"]), format="rdfxml")

    # --- operational-states --------------------------------------------------------------
    ost = world.get_ontology(IRIS["operational_states"])
    ost.imported_ontologies.extend([proc, mach])
    with ost:
        class OperationInstance(Thing): pass
        class OperationalState(Thing): pass
        class StablePattern(OperationalState): pass
        class Transition(OperationalState): pass
        class Anomaly(OperationalState): pass
        class ManufacturingJob(Thing): pass

        class instanceOfOperation(ObjectProperty, FunctionalProperty):
            domain = [OperationInstance]; range = [proc.Operation]
        class forFeature(ObjectProperty, FunctionalProperty):
            domain = [OperationInstance]; range = [proc.Feature]
        class partOfJob(ObjectProperty, FunctionalProperty):
            domain = [OperationInstance]; range = [ManufacturingJob]
        class observedDuring(ObjectProperty):
            domain = [OperationalState]; range = [OperationInstance]
        class observedOn(ObjectProperty, FunctionalProperty):
            domain = [OperationalState]; range = [mach.Machine]
        class observedInJob(ObjectProperty, FunctionalProperty):
            domain = [OperationalState]; range = [ManufacturingJob]
        class transitionsTo(ObjectProperty):
            domain = [OperationalState]; range = [OperationalState]
        class evidencedBy(ObjectProperty):
            domain = [proc.Feature]; range = [OperationalState]

        for pname, rng in (("hasStartTime", float), ("hasEndTime", float), ("hasStateLabel", str), ("hasAnomalyScore", float),
                           ("hasAnomalyFlag", bool), ("hasWindowCount", int), ("hasMethodId", str), ("hasMethodConfig", str),
                           ("derivedFromSeries", str), ("hasStepNumber", int), ("hasOverlapSeconds", float), ("hasJobId", str)):
            type(pname, (DataProperty, FunctionalProperty), {"range": [rng], "namespace": ost})
    written["operational_states"] = dest / file_name("operational_states")
    ost.save(file=str(written["operational_states"]), format="rdfxml")
    return written


if __name__ == "__main__":
    for name, path in build_all().items():
        print(f"{name}: {path}")
