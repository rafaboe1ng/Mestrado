"""Unified application graph (NetworkX) and its RDF export (rdflib).

Follows the group's conventions: node ids are ``feature_<n>``, ``op_<Name>``, ``opstep_<n>``,
``machine_<key>``, ``material_<Name>``; every node carries ``node_type``; decision edges carry the rule
identifiers and ontology sources that produced them. This repository adds ``opinst_<k>`` (executed
operation, from the machine's log), ``state_<...>`` (operational state from the SPCM) and ``job_<id>``.

In RDF every node is an individual under ``mfg:`` (http://onto.brep.org/manufacturing#) with
``rdf:type``, ``mfg:nodeType``, ``mfg:id`` and ``mfg:name``; edges become direct predicates and each edge
attribute becomes one reified ``rdf:Statement``; parameter records are individuals with typed value,
unit, ruleId, source and ontologySource IRIs. Unknown node types raise instead of being dropped, so a new
kind of node cannot silently vanish from the triplestore. The case ontology of the run is loaded into
the same graph, and each node points to its OWL individual with ``mfg:owlIndividual``, so SPARQL can
cross from the application graph to the reasoned knowledge.
"""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
from rdflib import OWL, RDF, RDFS, XSD, BNode, Graph, Literal, Namespace, URIRef

from framework.skl.build_ontologies import PARAMETER_NAMES

MFG = Namespace("http://onto.brep.org/manufacturing#")
SCHEMA_PATH = Path(__file__).resolve().parent / "manufacturing.ttl"
NODE_CLASS = {
    "feature": MFG.Feature, "operation": MFG.Operation, "operation_instance": MFG.Operation,
    "executed_operation": MFG.ExecutedOperation, "operational_state": MFG.OperationalState,
    "machine": MFG.Machine, "material": MFG.Material, "job": MFG.ManufacturingJob,
}
EDGE_PREDICATE = {
    "REQUIRES": MFG.requires, "INSTANCE_OF": MFG.instanceOfOperationType, "PLANNED_FOR": MFG.plannedFor,
    "RUNS_ON": MFG.runsOn, "MADE_OF": MFG.madeOf, "SEQUENCE_BEFORE": MFG.sequenceBefore, "EXECUTED_AS": MFG.executedAs,
    "DEPOSITS": MFG.deposits, "PART_OF_JOB": MFG.partOfJob, "OBSERVED_DURING": MFG.observedDuring,
    "OBSERVED_ON": MFG.observedOn, "OBSERVED_IN_JOB": MFG.observedInJob, "TRANSITIONS_TO": MFG.transitionsTo,
    "EVIDENCES": MFG.evidences,
}


class UnknownNodeTypeError(ValueError):
    pass


# ---------------------------------------------------------------------------------------------- build
def build_kg(plan: dict, reconciled: list, states: list, operation_log: list, entry_names: dict[str, str],
             state_names: dict[str, str], case_iri: str) -> nx.DiGraph:
    G = nx.DiGraph()
    job_id = plan["job_id"]
    job_node = f"job_{job_id}"
    G.add_node(job_node, node_type="job", name=job_id, owl=f"{case_iri}job_{job_id}")
    machine_node = f"machine_{plan['machine']}"
    G.add_node(machine_node, node_type="machine", name=plan["machine"])
    material_node = f"material_{plan['material']}"
    G.add_node(material_node, node_type="material", name=plan["material"])

    for rf in reconciled:
        if rf.unmapped:
            continue
        G.add_node(rf.individual, node_type="feature", name=f"Feature {rf.feature_id} ({rf.leaf_class or rf.owl_class})",
                   feature_type=rf.leaf_class or rf.owl_class, local_id=rf.local_id, dimensions=dict(rf.dimensions),
                   mapping_confidence=rf.combined_confidence, qualifier_rule_id=rf.qualifier_rule_id,
                   owl=f"{case_iri}{rf.individual}")
        G.add_edge(rf.individual, material_node, relation="MADE_OF", source="cfrm_assertion")

    by_local = {rf.local_id: rf.individual for rf in reconciled if rf.individual}
    log_by_entry = {e.entry_id: e for e in operation_log}
    for entry_id, name in entry_names.items():
        e = log_by_entry[entry_id]
        G.add_node(name, node_type="executed_operation", name=e.description or entry_id, entry_id=entry_id,
                   start_s=e.start_s, end_s=e.end_s, owl=f"{case_iri}{name}")
        G.add_edge(name, job_node, relation="PART_OF_JOB", source="operation_log")
        if e.feature_local_id in by_local:
            G.add_edge(name, by_local[e.feature_local_id], relation="DEPOSITS", source="operation_log")

    prev = None
    for s in plan["steps"]:
        op_node = f"op_{s['operation']}"
        if op_node not in G:
            G.add_node(op_node, node_type="operation", name=s["operation"], precedence=s["precedence"])
        G.add_edge(s["feature_individual"], op_node, relation="REQUIRES", confidence=s["mapping_confidence"],
                   rule_ids=list(s["operation_rule_ids"]), ontology_sources=list(s["operation_ontology_sources"]))
        step_node = f"opstep_{s['step_number']}"
        G.add_node(step_node, node_type="operation_instance", name=f"{s['operation']} for feature {s['feature_id']}",
                   step_number=s["step_number"], validation_status=s["validation_status"], operation=s["operation"],
                   parameter_set=s["parameter_set"], parameters=s["parameters"],
                   halt_reasons=[e["reason_code"] for e in s["exceptions"]], expert_request_ids=list(s["expert_request_ids"]),
                   recommended_adjustments=s["recommended_adjustments"], evidence_state_ids=list(s["evidence_state_ids"]))
        G.add_edge(step_node, op_node, relation="INSTANCE_OF", source="kefc")
        G.add_edge(step_node, s["feature_individual"], relation="PLANNED_FOR", source="kefc", validation_status=s["validation_status"])
        G.add_edge(step_node, machine_node, relation="RUNS_ON", source="kefc")
        G.add_edge(step_node, job_node, relation="PART_OF_JOB", source="kefc")
        for entry_id, name in entry_names.items():
            if by_local.get(log_by_entry[entry_id].feature_local_id) == s["feature_individual"]:
                G.add_edge(step_node, name, relation="EXECUTED_AS", source="operation_log_alignment")
        if prev:
            G.add_edge(prev, step_node, relation="SEQUENCE_BEFORE", source="kefc_precedence")
        prev = step_node

    for st in states:
        node = state_names.get(st.state_id, st.state_id)
        G.add_node(node, node_type="operational_state", name=f"{st.label} [{st.start_s:g}-{st.end_s:g} s]", label=st.label,
                   kind=st.kind, start_s=st.start_s, end_s=st.end_s, window_count=st.window_count, anomaly_flag=st.anomaly_flag,
                   anomaly_score=st.anomaly_score, method_id=st.method_id, method_config=st.method_config,
                   derived_from_series=st.derived_from_series, owl=f"{case_iri}{node}")
        G.add_edge(node, machine_node, relation="OBSERVED_ON", source="spcm")
        G.add_edge(node, job_node, relation="OBSERVED_IN_JOB", source="spcm")
        for ov in st.overlaps:
            if ov["entry_id"] in entry_names:
                G.add_edge(node, entry_names[ov["entry_id"]], relation="OBSERVED_DURING", overlap_s=ov["overlap_s"], source="spcm_alignment")
            if st.anomaly_flag and ov["feature_local_id"] in by_local:
                G.add_edge(node, by_local[ov["feature_local_id"]], relation="EVIDENCES", source="spcm_alignment", method_id=st.method_id)
    for st in states:
        if st.transitions_to and state_names.get(st.transitions_to, st.transitions_to) in G:
            G.add_edge(state_names.get(st.state_id, st.state_id), state_names.get(st.transitions_to, st.transitions_to),
                       relation="TRANSITIONS_TO", source="spcm")
    return G


# ---------------------------------------------------------------------------------------------- RDF
def _lit(v):
    if isinstance(v, bool):
        return Literal(v, datatype=XSD.boolean)
    if isinstance(v, int):
        return Literal(v, datatype=XSD.integer)
    if isinstance(v, float):
        return Literal(v, datatype=XSD.double)
    if isinstance(v, (list, tuple)):
        return Literal("|".join(str(x) for x in v))
    if isinstance(v, dict):
        return Literal(json.dumps(v, sort_keys=True))
    return Literal(str(v))


def export_rdf(G: nx.DiGraph, case_owl_path: str | Path | None = None) -> Graph:
    g = Graph()
    g.bind("mfg", MFG)
    g.bind("owl", OWL)
    if SCHEMA_PATH.exists():
        g.parse(str(SCHEMA_PATH), format="turtle")
    if case_owl_path and Path(case_owl_path).exists():
        g.parse(str(case_owl_path), format="xml")

    for node, data in G.nodes(data=True):
        ntype = data.get("node_type")
        if ntype not in NODE_CLASS:
            raise UnknownNodeTypeError(f"node {node!r} has node_type {ntype!r} with no RDF class; add it to NODE_CLASS")
        uri = MFG[node]
        g.add((uri, RDF.type, NODE_CLASS[ntype]))
        g.add((uri, MFG.nodeType, Literal(ntype)))
        g.add((uri, MFG.id, Literal(node)))
        g.add((uri, MFG.name, Literal(data.get("name", node))))
        if data.get("owl"):
            g.add((uri, MFG.owlIndividual, URIRef(data["owl"])))
        if ntype == "feature":
            g.add((uri, MFG.featureType, Literal(data["feature_type"])))
            g.add((uri, MFG.localId, Literal(data["local_id"])))
            g.add((uri, MFG.mappingConfidence, _lit(float(data["mapping_confidence"]))))
            if data.get("qualifier_rule_id"):
                g.add((uri, MFG.qualifierRuleId, Literal(data["qualifier_rule_id"])))
            for k, v in data["dimensions"].items():
                d = MFG[f"dim_{node}_{k}"]
                g.add((uri, MFG.hasDimension, d))
                g.add((d, RDF.type, MFG.Parameter))
                g.add((d, MFG.parameterType, Literal("dimension")))
                g.add((d, MFG.dimensionKey, Literal(k)))
                g.add((d, MFG.value, _lit(float(v))))
        elif ntype == "operation":
            g.add((uri, MFG.precedence, _lit(int(data["precedence"]))))
        elif ntype == "operation_instance":
            g.add((uri, MFG.stepNumber, _lit(int(data["step_number"]))))
            g.add((uri, MFG.validationStatus, Literal(data["validation_status"])))
            if data.get("parameter_set"):
                g.add((uri, MFG.parameterSet, Literal(data["parameter_set"])))
            for code in data.get("halt_reasons", []):
                g.add((uri, MFG.haltReason, Literal(code)))
            for rid in data.get("expert_request_ids", []):
                g.add((uri, MFG.expertRequestId, Literal(rid)))
            for sid in data.get("evidence_state_ids", []):
                g.add((uri, MFG.evidenceState, MFG[sid]))
            for pname, rec in data.get("parameters", {}).items():
                _add_parameter_record(g, uri, node, pname, rec)
            for n, adj in enumerate(data.get("recommended_adjustments", [])):
                _add_recommendation(g, uri, node, n, adj)
        elif ntype == "executed_operation":
            g.add((uri, MFG.entryId, Literal(data["entry_id"])))
            g.add((uri, MFG.startTime, _lit(float(data["start_s"]))))
            g.add((uri, MFG.endTime, _lit(float(data["end_s"]))))
        elif ntype == "operational_state":
            g.add((uri, MFG.stateLabel, Literal(data["label"])))
            g.add((uri, MFG.stateKind, Literal(data["kind"])))
            g.add((uri, MFG.startTime, _lit(float(data["start_s"]))))
            g.add((uri, MFG.endTime, _lit(float(data["end_s"]))))
            g.add((uri, MFG.windowCount, _lit(int(data["window_count"]))))
            g.add((uri, MFG.anomalyFlag, _lit(bool(data["anomaly_flag"]))))
            g.add((uri, MFG.anomalyScore, _lit(float(data["anomaly_score"]))))
            g.add((uri, MFG.methodId, Literal(data["method_id"])))
            g.add((uri, MFG.methodConfig, _lit(data["method_config"])))
            g.add((uri, MFG.derivedFromSeries, Literal(data["derived_from_series"])))

    for u, v, data in G.edges(data=True):
        rel = data.get("relation")
        pred = EDGE_PREDICATE.get(rel)
        if pred is None:
            raise UnknownNodeTypeError(f"edge {u}->{v} has relation {rel!r} with no RDF predicate; add it to EDGE_PREDICATE")
        g.add((MFG[u], pred, MFG[v]))
        for k, val in data.items():
            if k == "relation":
                continue
            st = BNode()
            g.add((st, RDF.type, RDF.Statement))
            g.add((st, RDF.subject, MFG[u]))
            g.add((st, RDF.predicate, pred))
            g.add((st, RDF.object, MFG[v]))
            g.add((st, MFG[_camel(k)], _lit(val)))
    return g


def _camel(k: str) -> str:
    parts = k.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])


def _add_parameter_record(g: Graph, step_uri, step_node: str, pname: str, rec: dict) -> None:
    p = MFG[f"param_{step_node}_{pname}"]
    g.add((step_uri, MFG.hasParameterRecord, p))
    g.add((p, RDF.type, MFG.ParameterRecord))
    g.add((p, MFG.parameterName, Literal(pname)))
    g.add((p, MFG.value, _lit(float(rec["value"]))))
    g.add((p, MFG.unit, Literal(rec["unit"])))
    g.add((p, MFG.ruleId, Literal(rec["rule_id"])))
    g.add((p, MFG.source, Literal(rec["source"])))
    for iri in rec.get("ontology_sources", []):
        g.add((p, MFG.ontologySource, URIRef(iri)))
    facts = rec.get("input_facts", {})
    if facts:
        g.add((p, MFG.inputFeatureId, _lit(int(facts["feature_id"]))))
        g.add((p, MFG.inputFeatureType, Literal(str(facts.get("feature_type")))))
        g.add((p, MFG.inputMaterial, Literal(str(facts.get("material")))))
        g.add((p, MFG.inputMappingConfidence, _lit(float(facts.get("mapping_confidence", 0.0)))))
        if facts.get("qualifier_rule_id"):
            g.add((p, MFG.inputQualifierRuleId, Literal(facts["qualifier_rule_id"])))


def _add_recommendation(g: Graph, step_uri, step_node: str, n: int, adj: dict) -> None:
    r = MFG[f"rec_{step_node}_{n}"]
    g.add((step_uri, MFG.hasRecommendedAdjustment, r))
    g.add((r, RDF.type, MFG.RecommendedAdjustment))
    g.add((r, MFG.parameterSet, Literal(adj["parameter_set"])))
    if adj.get("rule_id"):
        g.add((r, MFG.ruleId, Literal(adj["rule_id"])))
    for iri in adj.get("ontology_sources", []):
        g.add((r, MFG.ontologySource, URIRef(iri)))
    for sid in adj.get("evidence_state_ids", []):
        g.add((r, MFG.evidenceState, MFG[sid]))
    if adj.get("request_id"):
        g.add((r, MFG.expertRequestId, Literal(adj["request_id"])))
    for pname, v in adj.get("values", {}).items():
        p = MFG[f"rec_{step_node}_{n}_{pname}"]
        g.add((r, MFG.hasParameterRecord, p))
        g.add((p, RDF.type, MFG.RecommendedParameterRecord))
        g.add((p, MFG.parameterName, Literal(pname)))
        g.add((p, MFG.value, _lit(float(v["value"]))))
        g.add((p, MFG.unit, Literal(v["unit"])))
        if adj.get("rule_id"):
            g.add((p, MFG.ruleId, Literal(adj["rule_id"])))
        g.add((p, MFG.source, Literal("swrl_rule_recommendation")))


# ---------------------------------------------------------------------------------------------- files
def write_graph_files(G: nx.DiGraph, g: Graph, out_dir: str | Path) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    ttl = out / "unified_graph.ttl"
    g.serialize(destination=str(ttl), format="turtle")
    data = nx.node_link_data(G, edges="edges")
    (out / "unified_graph.json").write_text(json.dumps(data, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    counts: dict[str, int] = {}
    for _, d in G.nodes(data=True):
        counts[d["node_type"]] = counts.get(d["node_type"], 0) + 1
    rel: dict[str, int] = {}
    for _, _, d in G.edges(data=True):
        rel[d["relation"]] = rel.get(d["relation"], 0) + 1
    return {"nodes": G.number_of_nodes(), "edges": G.number_of_edges(), "nodes_by_type": counts, "edges_by_relation": rel,
            "triples": len(g), "ttl": str(ttl)}
