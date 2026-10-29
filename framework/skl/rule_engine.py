"""Forward-chaining engine for the restricted SWRL subset used by the rule file.

The group's rule file uses only two atom shapes, ``Class(?f)`` and ``property(?f, Individual)``,
with a single variable. Pellet executes them where Java 25 exists. This engine executes the same
file over the asserted individuals of an owlready2 world, so that the stated and executed rule sets
cannot diverge, and records the rule identifier of every inferred fact (the provenance the KEFC
needs). It is declared in ``reasoning_report`` as ``python_forward_chaining``; it is not a hidden
default.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

ATOM = re.compile(r"^\s*(\w+)\(\s*\?(\w+)\s*(?:,\s*(\w+)\s*)?\)\s*$")


@dataclass(frozen=True)
class Atom:
    predicate: str          # class name or property name
    variable: str           # the single variable, normally 'f'
    individual: str | None  # None for class atoms

    @property
    def is_class(self) -> bool:
        return self.individual is None


@dataclass(frozen=True)
class ParsedRule:
    rule_id: str
    text: str
    antecedent: tuple[Atom, ...]
    consequent: Atom

    @property
    def antecedent_classes(self) -> tuple[str, ...]:
        return tuple(a.predicate for a in self.antecedent if a.is_class)


class RuleParseError(ValueError):
    pass


def parse_atom(text: str) -> Atom:
    m = ATOM.match(text)
    if not m:
        raise RuleParseError(f"atom not in the accepted form Class(?f) or prop(?f, Ind): {text!r}")
    return Atom(m.group(1), m.group(2), m.group(3))


def parse_rules(text: str) -> list[ParsedRule]:
    rules: list[ParsedRule] = []
    seen: set[str] = set()
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line or "->" not in line:
            raise RuleParseError(f"line {lineno}: expected 'rule_id: antecedent -> consequent'")
        rule_id, body = line.split(":", 1)
        rule_id = rule_id.strip()
        if rule_id in seen:
            raise RuleParseError(f"line {lineno}: duplicate rule id {rule_id!r}")
        seen.add(rule_id)
        ante, cons = body.split("->", 1)
        antecedent = tuple(parse_atom(a) for a in ante.split("^"))
        consequent = parse_atom(cons)
        variables = {a.variable for a in antecedent} | {consequent.variable}
        if len(variables) != 1:
            raise RuleParseError(f"line {lineno}: rules must use a single variable, found {sorted(variables)}")
        rules.append(ParsedRule(rule_id, line, antecedent, consequent))
    return rules


@dataclass
class Inference:
    subject: str
    predicate: str
    value: str
    rule_id: str


@dataclass
class FactStore:
    """Facts about individuals: class membership (with ancestors) and property values (names)."""

    classes: dict[str, set[str]] = field(default_factory=dict)
    props: dict[str, dict[str, list[str]]] = field(default_factory=dict)

    def add_class(self, subject: str, cls: str) -> bool:
        s = self.classes.setdefault(subject, set())
        if cls in s:
            return False
        s.add(cls)
        return True

    def add_prop(self, subject: str, prop: str, value: str) -> bool:
        vals = self.props.setdefault(subject, {}).setdefault(prop, [])
        if value in vals:
            return False
        vals.append(value)
        return True

    def has_class(self, subject: str, cls: str) -> bool:
        return cls in self.classes.get(subject, ())

    def has_prop(self, subject: str, prop: str, value: str) -> bool:
        return value in self.props.get(subject, {}).get(prop, ())


def forward_chain(rules: list[ParsedRule], facts: FactStore, subjects: list[str],
                  class_ancestors: dict[str, set[str]] | None = None, max_passes: int = 50) -> list[Inference]:
    """Apply rules to a fixpoint. ``class_ancestors`` maps a class to its superclasses so that an
    inferred class membership also satisfies atoms on its ancestors (as DL reasoning would)."""
    class_ancestors = class_ancestors or {}
    inferred: list[Inference] = []
    for _ in range(max_passes):
        changed = False
        for rule in rules:
            for s in subjects:
                ok = True
                for atom in rule.antecedent:
                    if atom.is_class:
                        if not facts.has_class(s, atom.predicate):
                            ok = False
                            break
                    elif not facts.has_prop(s, atom.predicate, atom.individual):
                        ok = False
                        break
                if not ok:
                    continue
                c = rule.consequent
                if c.is_class:
                    if facts.add_class(s, c.predicate):
                        for anc in class_ancestors.get(c.predicate, ()):
                            facts.add_class(s, anc)
                        inferred.append(Inference(s, "rdf:type", c.predicate, rule.rule_id))
                        changed = True
                else:
                    if facts.add_prop(s, c.predicate, c.individual):
                        inferred.append(Inference(s, c.predicate, c.individual, rule.rule_id))
                        changed = True
        if not changed:
            return inferred
    raise RuntimeError(f"forward chaining did not converge in {max_passes} passes")


def satisfied(rule: ParsedRule, facts: FactStore, subject: str) -> bool:
    for atom in rule.antecedent:
        if atom.is_class:
            if not facts.has_class(subject, atom.predicate):
                return False
        elif not facts.has_prop(subject, atom.predicate, atom.individual):
            return False
    return True


def attribute(rules: list[ParsedRule], facts: FactStore, subject: str, predicate: str, value: str) -> list[str]:
    """Rule identifiers that derive ``predicate(subject, value)`` from the facts (used for provenance with
    either engine; with Pellet it is the only way to recover which rule fired)."""
    out = []
    for r in rules:
        c = r.consequent
        if c.is_class:
            match = predicate == "rdf:type" and c.predicate == value
        else:
            match = c.predicate == predicate and c.individual == value
        if match and satisfied(r, facts, subject):
            out.append(r.rule_id)
    return out
