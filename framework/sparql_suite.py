"""Fixed SPARQL suite over the unified graph export.

Every run evaluates all queries in order. Each query has a category and an expectation that depends
only on the run's context (``sensor_evidence``, ``operation_log_present``, ``has_anomalous_states``,
``has_evidence``): ``nonempty`` (must return rows), ``empty`` (an assertion written as a search for
violations: must return no rows), or ``skip``. ``assert_suite`` raises when an ``empty`` query fails, so a
provenance hole aborts the run before the RAL, as the group's Q52 does. The suite is the executable form
of P11 and P13 at the graph level.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

PREFIXES = """
PREFIX mfg: <http://onto.brep.org/manufacturing#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
PREFIX ap:  <http://onto.brep.org/manufacturing/additive-parameters#>
"""


@dataclass(frozen=True)
class Query:
    id: str
    category: str
    description: str
    sparql: str
    expect: Callable[[dict], str]


def always(kind: str) -> Callable[[dict], str]:
    return lambda ctx: kind


def nonempty_if(flag: str) -> Callable[[dict], str]:
    return lambda ctx: "nonempty" if ctx.get(flag) else "empty"


def empty_if_not(flag: str) -> Callable[[dict], str]:
    return lambda ctx: "skip" if ctx.get(flag) else "empty"


SUITE: list[Query] = [
    # ---- features
    Query("Q01", "features", "every feature with its type and material", """
        SELECT ?f ?type ?mat WHERE { ?f a mfg:Feature ; mfg:featureType ?type ; mfg:madeOf ?mat . } ORDER BY ?f""", always("nonempty")),
    Query("Q02", "features", "features whose class came from a numeric qualifier, with the qualifier id", """
        SELECT ?f ?q WHERE { ?f a mfg:Feature ; mfg:qualifierRuleId ?q . }""", always("nonempty")),
    # ---- operations
    Query("Q03", "operations", "feature -> operation decisions with their rule identifiers (reified)", """
        SELECT ?f ?op ?rules WHERE { ?f mfg:requires ?op .
          ?st a rdf:Statement ; rdf:subject ?f ; rdf:predicate mfg:requires ; rdf:object ?op ; mfg:ruleIds ?rules . }""", always("nonempty")),
    Query("Q04", "operations", "operation types ordered by precedence", """
        SELECT ?op ?p WHERE { ?op a mfg:Operation ; mfg:nodeType "operation" ; mfg:precedence ?p . } ORDER BY ?p""", always("nonempty")),
    # ---- plan
    Query("Q05", "plan", "planned steps in order with validation status", """
        SELECT ?s ?n ?status ?f WHERE { ?s mfg:nodeType "operation_instance" ; mfg:stepNumber ?n ; mfg:validationStatus ?status ; mfg:plannedFor ?f . } ORDER BY ?n""", always("nonempty")),
    Query("Q06", "plan", "sequence chain between consecutive steps", """
        SELECT ?a ?b WHERE { ?a mfg:sequenceBefore ?b . }""", always("nonempty")),
    Query("Q07", "plan", "steps aligned with an executed operation of the log", """
        SELECT ?s ?x ?t0 ?t1 WHERE { ?s mfg:executedAs ?x . ?x mfg:startTime ?t0 ; mfg:endTime ?t1 . }""", nonempty_if("operation_log_present")),
    # ---- provenance
    Query("Q08", "provenance", "parameter records with rule id and ontology source", """
        SELECT ?s ?p ?v ?u ?rule ?onto WHERE { ?s mfg:hasParameterRecord ?r . ?r a mfg:ParameterRecord ;
          mfg:parameterName ?p ; mfg:value ?v ; mfg:unit ?u ; mfg:ruleId ?rule ; mfg:ontologySource ?onto . }""", always("nonempty")),
    Query("Q09", "provenance", "ASSERTION: steps with a parameter set but fewer than six parameter records", """
        SELECT ?s (COUNT(?r) AS ?n) WHERE { ?s mfg:nodeType "operation_instance" ; mfg:parameterSet ?ps .
          OPTIONAL { ?s mfg:hasParameterRecord ?r . ?r a mfg:ParameterRecord . } } GROUP BY ?s HAVING (COUNT(?r) < 6)""", always("empty")),
    Query("Q10", "provenance", "ASSERTION: parameter records lacking ruleId or ontologySource", """
        SELECT ?r WHERE { ?r a mfg:ParameterRecord . FILTER NOT EXISTS { ?r mfg:ruleId ?x . ?r mfg:ontologySource ?o . } }""", always("empty")),
    Query("Q11", "provenance", "cross-check: the parameter set of each step is the one the SKL inferred for its feature", """
        SELECT ?s ?ps ?owlset WHERE { ?s mfg:nodeType "operation_instance" ; mfg:parameterSet ?ps ; mfg:plannedFor ?f .
          ?f mfg:owlIndividual ?ind . ?ind ap:requiresParameterSet ?owlset .
          FILTER (STRENDS(STR(?owlset), CONCAT("#", ?ps))) }""", always("nonempty")),
    # ---- validation
    Query("Q12", "validation", "steps held for review with their halt reasons", """
        SELECT ?s ?code ?req WHERE { ?s mfg:validationStatus "requires_review" ; mfg:haltReason ?code . OPTIONAL { ?s mfg:expertRequestId ?req } }""", always("skip")),
    Query("Q13", "validation", "count of steps by validation status", """
        SELECT ?status (COUNT(?s) AS ?n) WHERE { ?s mfg:nodeType "operation_instance" ; mfg:validationStatus ?status . } GROUP BY ?status""", always("nonempty")),
    # ---- operational states
    Query("Q14", "operational_states", "operational states with label, span and method", """
        SELECT ?st ?label ?kind ?t0 ?t1 ?m WHERE { ?st a mfg:OperationalState ; mfg:stateLabel ?label ; mfg:stateKind ?kind ;
          mfg:startTime ?t0 ; mfg:endTime ?t1 ; mfg:methodId ?m . } ORDER BY ?t0""", nonempty_if("sensor_evidence")),
    Query("Q15", "operational_states", "anomalous states with the executed operation and the feature being deposited", """
        SELECT ?st ?x ?f WHERE { ?st a mfg:OperationalState ; mfg:anomalyFlag true ; mfg:observedDuring ?x . ?x mfg:deposits ?f . }""",
          lambda ctx: "nonempty" if (ctx.get("has_evidence")) else "skip"),
    Query("Q16", "operational_states", "ASSERTION: anomalous states not linked to any executed operation although a log exists", """
        SELECT ?st WHERE { ?st a mfg:OperationalState ; mfg:anomalyFlag true . FILTER NOT EXISTS { ?st mfg:observedDuring ?x } }""",
          lambda ctx: "empty" if (ctx.get("sensor_evidence") and ctx.get("operation_log_present")) else "skip"),
    Query("Q17", "operational_states", "state transition chain", """
        SELECT ?a ?b WHERE { ?a mfg:transitionsTo ?b . }""", nonempty_if("sensor_evidence")),
    Query("Q18", "operational_states", "ASSERTION: states without method provenance (methodId, methodConfig, derivedFromSeries)", """
        SELECT ?st WHERE { ?st a mfg:OperationalState . FILTER NOT EXISTS { ?st mfg:methodId ?m ; mfg:methodConfig ?c ; mfg:derivedFromSeries ?d } }""", always("empty")),
    # ---- evidence
    Query("Q19", "evidence", "steps held by anomalous_operational_state with the evidence state", """
        SELECT ?s ?f ?st WHERE { ?s mfg:haltReason "anomalous_operational_state" ; mfg:plannedFor ?f ; mfg:evidenceState ?st . }""",
          nonempty_if("has_evidence")),
    Query("Q20", "evidence", "recommended adjustments with rule id, ontology source and evidence state", """
        SELECT ?s ?rec ?rule ?st WHERE { ?s mfg:hasRecommendedAdjustment ?rec . ?rec mfg:ruleId ?rule ; mfg:ontologySource ?o ; mfg:evidenceState ?st . }""",
          lambda ctx: "nonempty" if ctx.get("has_recommendations") else "skip"),
    Query("Q21", "evidence", "ASSERTION: recommended adjustments lacking ruleId, ontologySource or evidenceState", """
        SELECT ?rec WHERE { ?rec a mfg:RecommendedAdjustment . FILTER NOT EXISTS { ?rec mfg:ruleId ?r ; mfg:ontologySource ?o ; mfg:evidenceState ?st } }""", always("empty")),
    Query("Q22", "evidence", "ASSERTION: without the sensor module no step may carry an evidence halt or a recommendation", """
        SELECT ?s WHERE { { ?s mfg:haltReason "anomalous_operational_state" } UNION { ?s mfg:haltReason "parameter_adjustment_suggested" }
          UNION { ?s mfg:hasRecommendedAdjustment ?r } }""", lambda ctx: "skip" if ctx.get("sensor_evidence") else "empty"),
    Query("Q23", "evidence", "ASSERTION: a recommendation never changes the planned records (recommended values live only under rec_ nodes)", """
        SELECT ?r WHERE { ?r a mfg:ParameterRecord ; mfg:source ?src . FILTER (?src != "swrl_rule") }""", always("empty")),
]


class SPARQLAssertionError(RuntimeError):
    pass


def run_suite(graph, context: dict) -> list[dict]:
    results = []
    for q in SUITE:
        expected = q.expect(context)
        rows = [{str(k): str(v) for k, v in r.asdict().items()} for r in graph.query(PREFIXES + q.sparql)]
        if expected == "skip":
            passed = None
        elif expected == "nonempty":
            passed = len(rows) > 0
        else:
            passed = len(rows) == 0
        results.append({"id": q.id, "category": q.category, "description": q.description, "expected": expected,
                        "rows": len(rows), "passed": passed, "sample": rows[:5]})
    return results


def assert_suite(results: list[dict]) -> None:
    failed = [r for r in results if r["passed"] is False]
    if failed:
        raise SPARQLAssertionError("SPARQL suite failed: " + "; ".join(f"{r['id']} ({r['expected']}, {r['rows']} rows): {r['description']}" for r in failed))


def suite_summary(results: list[dict]) -> dict:
    return {"queries": len(results), "passed": sum(1 for r in results if r["passed"] is True),
            "failed": sum(1 for r in results if r["passed"] is False), "skipped": sum(1 for r in results if r["passed"] is None),
            "failed_ids": [r["id"] for r in results if r["passed"] is False]}
