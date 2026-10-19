"""Utilitarios comuns aos contratos."""
from __future__ import annotations

import math

OPERADORES = ("<", "<=", ">", ">=", "==")


def comparar(a: float, operador: str, b: float) -> bool:
    """Avalia ``a <operador> b`` com os operadores permitidos nas regras."""
    if operador == "<":
        return a < b
    if operador == "<=":
        return a <= b
    if operador == ">":
        return a > b
    if operador == ">=":
        return a >= b
    if operador == "==":
        return math.isclose(a, b)
    raise ValueError(f"operador desconhecido: {operador!r}")


class ErroContrato(ValueError):
    """Levantado quando um objeto viola o contrato da fronteira."""


def garantir(objeto) -> None:
    """Chama ``objeto.validar()`` e levanta ErroContrato se houver erros."""
    erros = objeto.validar()
    if erros:
        raise ErroContrato(f"{type(objeto).__name__}: " + "; ".join(erros))
