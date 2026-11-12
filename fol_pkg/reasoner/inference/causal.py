from __future__ import annotations

from itertools import product

from ..logic.scm import CausalProblem, Equation
from ..logic.terms import Atom, Literal, Rule
from .forward_chain import well_founded
from .negation import Model, compile_rule


def _lit(name: str, positive: bool = True) -> Literal:
    return Literal(Atom(name, ()), positive)


def equation_rules(eq: Equation) -> list[Rule]:
    causes = [_lit(v, not negated) for v, negated in eq.causes]
    flipped = [Literal(c.atom, not c.positive) for c in causes]
    if eq.op == "and":
        bodies = [[f] for f in flipped] if eq.negated else [causes]
    else:
        bodies = [flipped] if eq.negated else [[c] for c in causes]
    return [Rule(_lit(eq.effect), tuple(body)) for body in bodies]


def evaluate(
    equations: list[Equation], true_roots: set[str], interventions: dict[str, bool]
) -> tuple[Model, Model]:
    rules = [
        compile_rule(rule, cwa=True)
        for eq in equations
        if eq.effect not in interventions
        for rule in equation_rules(eq)
    ]
    facts = [(v, ()) for v in true_roots if v not in interventions]
    facts += [(v, ()) for v, value in interventions.items() if value]
    return well_founded(rules, facts, ())


def _true(model: Model, name: str) -> bool:
    return () in model.get(name, ())


def _roots(problem: CausalProblem) -> list[str]:
    effects = {eq.effect for eq in problem.equations}
    names = {v for eq in problem.equations for v, _ in eq.causes}
    names |= set(problem.observations) | set(problem.priors)
    return sorted(names - effects)


def _weight(assignment: dict[str, bool], priors: dict[str, float]) -> float:
    weight = 1.0
    for name, value in assignment.items():
        if name in priors:
            weight *= priors[name] if value else 1 - priors[name]
    return weight


def _consistent(problem: CausalProblem, certain: Model, possible: Model) -> bool:
    return all(
        _true(certain, name) if value else not _true(possible, name)
        for name, value in problem.observations.items()
    )


def worlds(problem: CausalProblem) -> list[tuple[dict[str, bool], float]]:
    roots = _roots(problem)
    candidates = []
    for values in product([True, False], repeat=len(roots)):
        assignment = dict(zip(roots, values))
        certain, possible = evaluate(
            problem.equations, {r for r, v in assignment.items() if v}, {}
        )
        candidates.append((assignment, _weight(assignment, problem.priors), certain, possible))
    kept = [(a, w) for a, w, c, p in candidates if _consistent(problem, c, p)]
    return kept or [(a, w) for a, w, _, _ in candidates]


def probability(problem: CausalProblem) -> float:
    interventions = dict(problem.interventions)
    total = hits = 0.0
    for assignment, weight in worlds(problem):
        certain, _ = evaluate(
            problem.equations, {r for r, v in assignment.items() if v}, interventions
        )
        total += weight
        hits += weight * _true(certain, problem.target)
    return hits / total if total else 0.0


def solve(problem: CausalProblem) -> bool:
    return probability(problem) > 0.5


def explain(problem: CausalProblem) -> list[str]:
    lines = []
    for eq in problem.equations:
        joiner = " and " if eq.op == "and" else " or "
        cause = joiner.join(("not " if neg else "") + v for v, neg in eq.causes)
        lines.append(f"{eq.effect} := {'not ' if eq.negated else ''}({cause})")
    for name, value in problem.observations.items():
        lines.append(f"observed {name} = {value}")
    interventions = dict(problem.interventions)
    lines.append("intervene: " + ", ".join(f"{k} := {v}" for k, v in interventions.items()))
    assignment, _ = worlds(problem)[0]
    lines.append(f"exogenous world: {assignment}")
    certain, _ = evaluate(problem.equations, {r for r, v in assignment.items() if v}, interventions)
    names = {eq.effect for eq in problem.equations} | set(assignment)
    lines.append("after intervention: " + ", ".join(f"{n}={_true(certain, n)}" for n in sorted(names)))
    lines.append(f"{problem.target} occurs: {_true(certain, problem.target)}")
    return lines
