"""Structured Knowledge Layer for the FDM case.

``knowledge/`` holds the OWL files written by ``build_ontologies.py`` (never edited by hand) and the
single rule file ``knowledge/rules/fdm_rules.swrl``; ``repository.py`` loads them, asserts the case
individuals and reasons; ``rule_engine.py`` is the forward-chaining engine used where Pellet is not
available.
"""
from framework.skl.repository import SKLReasonerError, SKLRepository  # noqa: F401
