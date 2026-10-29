"""SKL repository: loads the generated ontologies and the rule file, holds one case ontology per run,
asserts individuals, reasons, and answers the questions the KEFC asks, with rule provenance.

Fail-loud contract (PLANO P14): a missing ontology file, a missing or malformed rule file, a rule that
names an entity no ontology defines, or a requested reasoner that cannot run all raise
``SKLReasonerError`` at construction or at ``reason()``; nothing downstream runs.

Reasoners. ``reasoner="python"`` runs the forward-chaining engine over the same rule file;
``"pellet"`` registers the rules as SWRL in the case ontology and calls Pellet through owlready2
(needs a Java runtime; untested on the machine this was written on, see docs/modulos/framework.md);
``"auto"`` picks Pellet when ``java`` is on PATH and the Python engine otherwise. The engine used is
written in ``reasoning_report`` and copied into every plan, so a result never hides which one ran.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from owlready2 import ObjectPropertyClass, Thing, ThingClass, World

from framework.skl.build_ontologies import (FOUNDATION, IRIS, KNOWLEDGE_DIR, MACHINES, NS, PARAMETER_PROPS,
                                            PARAMETER_UNITS, file_name)
from framework.skl.rule_engine import FactStore, ParsedRule, RuleParseError, attribute, forward_chain, parse_rules

DEFAULT_RULES = KNOWLEDGE_DIR / "rules" / "fdm_rules.swrl"
REASONERS = ("auto", "python", "pellet")
PYTHON_ENGINE = "python_forward_chaining"
PELLET_ENGINE = "pellet"


class SKLReasonerError(RuntimeError):
    """Raised when the knowledge layer cannot be loaded or reasoned over. Never caught into a default."""


def machine_key_to_owl(machine_key: str) -> str:
    if machine_key not in MACHINES:
        raise KeyError(f"machine key {machine_key!r} not declared; known: {sorted(MACHINES)}")
    return MACHINES[machine_key]["individual"]


class SKLRepository:
    def __init__(self, knowledge_dir: str | Path = KNOWLEDGE_DIR, rules_path: str | Path | None = None,
                 reasoner: str = "auto", case_id: str = "case"):
        if reasoner not in REASONERS:
            raise ValueError(f"reasoner must be one of {REASONERS}")
        self.knowledge_dir = Path(knowledge_dir)
        self.rules_path = Path(rules_path) if rules_path else self.knowledge_dir / "rules" / "fdm_rules.swrl"
        self.java = shutil.which("java")
        if reasoner == "pellet" and not self.java:
            raise SKLReasonerError("Pellet requested but no Java runtime is on PATH")
        self.reasoner = PELLET_ENGINE if (reasoner == "pellet" or (reasoner == "auto" and self.java)) else PYTHON_ENGINE
        if not self.rules_path.exists():
            raise SKLReasonerError(f"rule file missing: {self.rules_path}")
        try:
            self.rules: list[ParsedRule] = parse_rules(self.rules_path.read_text(encoding="utf-8"))
        except RuleParseError as e:
            raise SKLReasonerError(f"rule file {self.rules_path.name}: {e}") from e
        if not self.rules:
            raise SKLReasonerError(f"rule file {self.rules_path.name} declares no rules")

        self.world = World()
        self.ontologies: dict[str, Any] = {}
        for name in FOUNDATION:
            path = self.knowledge_dir / file_name(name)
            if not path.exists():
                raise SKLReasonerError(f"ontology missing: {path} (run python -m framework.skl.build_ontologies)")
            with open(path, "rb") as fh:
                self.ontologies[name] = self.world.get_ontology(IRIS[name]).load(fileobj=fh)
        self.case_id = case_id
        self.case = self.world.get_ontology(f"{NS}/case-{case_id}#")
        self.case.imported_ontologies = list(self.ontologies.values())
        self._class_ancestors = self._compute_class_ancestors()
        self._validate_rules()
        self.skl_version = self._version()
        self.reasoning_report: dict | None = None
        self._facts: FactStore | None = None

    # ------------------------------------------------------------------ lookups
    def entity(self, name: str):
        for onto in (self.case, *self.ontologies.values()):
            e = onto[name]
            if e is not None:
                return e
        raise KeyError(f"no entity named {name!r} in the SKL")

    def has_entity(self, name: str) -> bool:
        try:
            self.entity(name)
            return True
        except KeyError:
            return False

    def ontology_of(self, name: str) -> str:
        e = self.entity(name)
        return e.namespace.ontology.base_iri.rstrip("#")

    def rule_sources(self, rule: ParsedRule) -> list[str]:
        names = {a.predicate for a in (*rule.antecedent, rule.consequent)}
        names |= {a.individual for a in (*rule.antecedent, rule.consequent) if a.individual}
        return sorted({self.ontology_of(n) for n in names if self.has_entity(n)})

    def rule_by_id(self, rule_id: str) -> ParsedRule:
        for r in self.rules:
            if r.rule_id == rule_id:
                return r
        raise KeyError(rule_id)

    def _compute_class_ancestors(self) -> dict[str, set[str]]:
        out: dict[str, set[str]] = {}
        for onto in self.ontologies.values():
            for c in onto.classes():
                out[c.name] = {a.name for a in c.ancestors() if a is not Thing and a is not c}
        return out

    def _validate_rules(self) -> None:
        missing = []
        for r in self.rules:
            for a in (*r.antecedent, r.consequent):
                if not self.has_entity(a.predicate):
                    missing.append(f"{r.rule_id}: {a.predicate}")
                if a.individual and not self.has_entity(a.individual):
                    missing.append(f"{r.rule_id}: {a.individual}")
        if missing:
            raise SKLReasonerError("rules reference entities no ontology defines: " + "; ".join(missing))

    def _version(self) -> str:
        h = hashlib.sha256()
        h.update(self.rules_path.read_bytes())
        for name in FOUNDATION:
            h.update((self.knowledge_dir / file_name(name)).read_bytes())
        return h.hexdigest()[:12]

    # ------------------------------------------------------------------ assertions
    def assert_feature(self, feature_id: int, owl_class: str, leaf_class: str | None, material: str, machine_key: str,
                       qualifier_rule_id: str | None = None) -> str:
        name = f"feature_{feature_id}"
        with self.case:
            ind = self.entity(owl_class)(name)
            if leaf_class:
                ind.is_a.append(self.entity(leaf_class))
            ind.madeOfMaterial = self.entity(material)
            ind.printedOn = self.entity(machine_key_to_owl(machine_key))
            if qualifier_rule_id:
                ind.hasQualifierRule.append(qualifier_rule_id)
        return name

    def assert_job(self, job_id: str) -> str:
        name = f"job_{job_id}"
        with self.case:
            ind = self.entity("ManufacturingJob")(name)
            ind.hasJobId = job_id
        return name

    def assert_operation_instance(self, name: str, feature_name: str | None, job_name: str, start_s: float, end_s: float,
                                  step_number: int) -> str:
        with self.case:
            ind = self.entity("OperationInstance")(name)
            if feature_name:
                ind.forFeature = self.entity(feature_name)
            ind.partOfJob = self.entity(job_name)
            ind.hasStartTime = float(start_s)
            ind.hasEndTime = float(end_s)
            ind.hasStepNumber = int(step_number)
        return name

    def assert_state(self, name: str, kind_class: str, label: str, start_s: float, end_s: float, anomaly_flag: bool,
                     anomaly_score: float, window_count: int, method_id: str, method_config: dict, derived_from: str,
                     machine_key: str, job_name: str, observed_during: list[str]) -> str:
        with self.case:
            ind = self.entity(kind_class)(name)
            ind.hasStateLabel = label
            ind.hasStartTime = float(start_s)
            ind.hasEndTime = float(end_s)
            ind.hasAnomalyFlag = bool(anomaly_flag)
            ind.hasAnomalyScore = float(anomaly_score)
            ind.hasWindowCount = int(window_count)
            ind.hasMethodId = method_id
            ind.hasMethodConfig = json.dumps(method_config, sort_keys=True)
            ind.derivedFromSeries = derived_from
            ind.observedOn = self.entity(machine_key_to_owl(machine_key))
            ind.observedInJob = self.entity(job_name)
            for op in observed_during:
                ind.observedDuring.append(self.entity(op))
        return name

    def assert_transition(self, from_state: str, to_state: str) -> None:
        with self.case:
            self.entity(from_state).transitionsTo.append(self.entity(to_state))

    def assert_evidence(self, feature_name: str, state_names: list[str]) -> None:
        if not state_names:
            return
        with self.case:
            ind = self.entity(feature_name)
            cls = self.entity("FeatureWithAnomalousDeposition")
            if cls not in ind.is_a:
                ind.is_a.append(cls)
            for s in state_names:
                ind.evidencedBy.append(self.entity(s))

    # ------------------------------------------------------------------ reasoning
    def _feature_individuals(self):
        feature_cls = self.entity("Feature")
        return [i for i in self.case.individuals() if isinstance(i, feature_cls)]

    def _facts_from_case(self) -> FactStore:
        facts = FactStore()
        for ind in self._feature_individuals():
            for c in ind.is_a:
                if isinstance(c, ThingClass):
                    facts.add_class(ind.name, c.name)
                    for anc in self._class_ancestors.get(c.name, ()):
                        facts.add_class(ind.name, anc)
            for prop in ind.get_properties():
                if not isinstance(prop, ObjectPropertyClass):
                    continue
                v = getattr(ind, prop.python_name)
                vals = v if isinstance(v, list) else ([v] if v is not None else [])
                for x in vals:
                    facts.add_prop(ind.name, prop.name, x.name)
        return facts

    def reason(self) -> dict:
        subjects = [i.name for i in self._feature_individuals()]
        facts = self._facts_from_case()
        if self.reasoner == PYTHON_ENGINE:
            inferences = forward_chain(self.rules, facts, subjects, self._class_ancestors)
            self._write_back(inferences)
        else:
            inferences = self._reason_with_pellet(facts, subjects)
        self._facts = facts
        self.reasoning_report = {
            "reasoner": self.reasoner, "reasoning_status": "completed", "java": self.java,
            "skl_version": self.skl_version, "rules_loaded": len(self.rules), "features": len(subjects),
            "inferences": len(inferences), "rules_fired": sorted({i.rule_id for i in inferences}),
        }
        return self.reasoning_report

    def _write_back(self, inferences) -> None:
        with self.case:
            for inf in inferences:
                ind = self.entity(inf.subject)
                if inf.predicate == "rdf:type":
                    cls = self.entity(inf.value)
                    if cls not in ind.is_a:
                        ind.is_a.append(cls)
                else:
                    prop = self.entity(inf.predicate)
                    val = self.entity(inf.value)
                    current = getattr(ind, prop.python_name)
                    if isinstance(current, list):
                        if val not in current:
                            current.append(val)
                    else:
                        setattr(ind, prop.python_name, val)

    def _reason_with_pellet(self, facts: FactStore, subjects: list[str]):
        from owlready2 import Imp, sync_reasoner_pellet
        from framework.skl.rule_engine import Inference
        before = {(s, p, v) for s in subjects for p, vals in facts.props.get(s, {}).items() for v in vals}
        try:
            with self.case:
                for r in self.rules:
                    Imp().set_as_rule(r.text.split(":", 1)[1].strip())
            sync_reasoner_pellet(self.world, infer_property_values=True, debug=0)
        except Exception as e:  # owlready2 raises OwlReadyJavaError / OwlReadyInconsistentOntologyError
            raise SKLReasonerError(f"Pellet failed: {type(e).__name__}: {e}") from e
        after = self._facts_from_case()
        inferences = []
        for s in subjects:
            for p, vals in after.props.get(s, {}).items():
                for v in vals:
                    if (s, p, v) not in before:
                        facts.add_prop(s, p, v)
                        ids = attribute(self.rules, after, s, p, v)
                        inferences.append(Inference(s, p, v, ids[0] if ids else "unattributed"))
        return inferences

    def _require_reasoned(self) -> None:
        if self.reasoning_report is None or self._facts is None:
            raise SKLReasonerError("reason() has not been run on this repository")

    def _provenance(self, subject: str, predicate: str, value: str) -> tuple[list[str], list[str]]:
        ids = attribute(self.rules, self._facts, subject, predicate, value)
        sources: set[str] = set()
        for rid in ids:
            sources.update(self.rule_sources(self.rule_by_id(rid)))
        return ids, sorted(sources)

    # ------------------------------------------------------------------ queries used by the KEFC
    def get_operations(self, feature_name: str) -> list[dict]:
        self._require_reasoned()
        out = []
        for op in self.entity(feature_name).requiresOperation:
            ids, sources = self._provenance(feature_name, "requiresOperation", op.name)
            out.append({"operation": op.name, "precedence": self.operation_precedence(op.name), "rule_ids": ids,
                        "ontology_sources": sources})
        return sorted(out, key=lambda d: (d["precedence"], d["operation"]))

    def _parameter_set_dict(self, feature_name: str, predicate: str, ps) -> dict:
        ids, sources = self._provenance(feature_name, predicate, ps.name)
        values = {}
        for pname, prop in PARAMETER_PROPS.items():
            v = getattr(ps, prop)
            if v is not None:
                values[pname] = {"value": float(v), "unit": PARAMETER_UNITS[pname]}
        return {"name": ps.name, "operation": ps.forOperation.name if ps.forOperation else None,
                "material": ps.forMaterial.name if ps.forMaterial else None, "values": values,
                "rule_ids": ids, "ontology_sources": sources, "note": list(ps.hasNote)}

    def get_parameter_sets(self, feature_name: str) -> list[dict]:
        self._require_reasoned()
        return [self._parameter_set_dict(feature_name, "requiresParameterSet", ps) for ps in self.entity(feature_name).requiresParameterSet]

    def get_recommended_sets(self, feature_name: str) -> list[dict]:
        self._require_reasoned()
        return [self._parameter_set_dict(feature_name, "recommendsParameterSet", ps) for ps in self.entity(feature_name).recommendsParameterSet]

    def feature_classes(self, feature_name: str) -> list[str]:
        return sorted(c.name for c in self.entity(feature_name).is_a if isinstance(c, ThingClass))

    def evidence_states(self, feature_name: str) -> list[str]:
        return [s.name for s in self.entity(feature_name).evidencedBy]

    def operation_precedence(self, op_name: str) -> int:
        v = self.entity(op_name).hasPrecedenceOrder
        return int(v) if v is not None else 10_000

    def machine_supports_operation(self, machine_key: str, op_name: str) -> bool:
        m = self.entity(machine_key_to_owl(machine_key))
        return any(o.name == op_name for o in m.supportsOperation)

    def machine_limits(self, machine_key: str) -> dict[str, float]:
        m = self.entity(machine_key_to_owl(machine_key))
        out = {}
        for prop in m.get_properties():
            if prop.name.startswith("hasSafety"):
                out[prop.name] = float(getattr(m, prop.python_name))
        return out

    def material_names(self) -> list[str]:
        return sorted(i.name for i in self.entity("Material").instances())

    # ------------------------------------------------------------------ persistence
    def save_case(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.case.save(file=str(path), format="rdfxml")
        return path

    @property
    def case_iri(self) -> str:
        return self.case.base_iri
