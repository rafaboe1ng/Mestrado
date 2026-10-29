import pytest

from framework.skl.rule_engine import FactStore, RuleParseError, attribute, forward_chain, parse_rules

pytestmark = pytest.mark.framework

RULES = """
# comment
wall_op: Wall(?f) -> requiresOperation(?f, WallDepositionOp)
thin_params: ThinWall(?f) ^ madeOfMaterial(?f, PLA) -> requiresParameterSet(?f, PLA_ThinWall_Params)
mark: ThinWall(?f) ^ FeatureWithAnomalousDeposition(?f) -> recommendsParameterSet(?f, Recovery)
"""


def test_parse_rules_reads_ids_and_atoms():
    rules = parse_rules(RULES)
    assert [r.rule_id for r in rules] == ["wall_op", "thin_params", "mark"]
    assert rules[1].antecedent[1].predicate == "madeOfMaterial" and rules[1].antecedent[1].individual == "PLA"
    assert rules[0].consequent.individual == "WallDepositionOp"


@pytest.mark.parametrize("bad", [
    "x: Wall(?f) ^ madeOfMaterial(?g, PLA) -> requiresOperation(?f, Op)",   # two variables
    "x: greaterThan(?v, 0.8) -> Thin(?f)",             # numeric literal, not an individual
    "x: Wall(?f) requiresOperation(?f, Op)",           # no arrow
    "x: Wall(?f) -> Op(?f)\nx: Wall(?f) -> Op(?f)",    # duplicate id
])
def test_parse_rules_rejects_unsupported_forms(bad):
    with pytest.raises(RuleParseError):
        parse_rules(bad)


def test_forward_chain_uses_ancestors_and_records_rule_ids():
    rules = parse_rules(RULES)
    facts = FactStore()
    facts.add_class("f1", "ThinWall")
    for anc in ("Wall", "Feature"):
        facts.add_class("f1", anc)
    facts.add_prop("f1", "madeOfMaterial", "PLA")
    inf = forward_chain(rules, facts, ["f1"], {"ThinWall": {"Wall", "Feature"}})
    got = {(i.predicate, i.value, i.rule_id) for i in inf}
    assert ("requiresOperation", "WallDepositionOp", "wall_op") in got
    assert ("requiresParameterSet", "PLA_ThinWall_Params", "thin_params") in got
    assert not any(i.predicate == "recommendsParameterSet" for i in inf), "no evidence class, no recommendation"
    assert attribute(rules, facts, "f1", "requiresParameterSet", "PLA_ThinWall_Params") == ["thin_params"]


def test_forward_chain_is_idempotent():
    rules = parse_rules(RULES)
    facts = FactStore()
    facts.add_class("f1", "Wall")
    first = forward_chain(rules, facts, ["f1"])
    second = forward_chain(rules, facts, ["f1"])
    assert len(first) == 1 and second == []
