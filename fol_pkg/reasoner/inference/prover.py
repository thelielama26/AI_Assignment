from __future__ import annotations

from ..logic.cnf import Clause, TooLarge, to_clauses
from ..logic.formula import Formula, Not
from .resolution import Result, refute


def premise_clauses(premises: list[Formula]) -> list[Clause]:
    clauses: list[Clause] = []
    for i, premise in enumerate(premises):
        try:
            clauses.extend(to_clauses(premise, tag=f"p{i}_"))
        except TooLarge:
            continue
    return clauses


def entails(premises: list[Formula], query: Formula, **limits) -> Result:
    return prove(premise_clauses(premises), query, **limits)


def prove(usable: list[Clause], query: Formula, **limits) -> Result:
    try:
        sos = to_clauses(Not(query), tag="q_")
    except TooLarge:
        return Result(False, reason="too large")
    return refute(usable, sos, **limits)
