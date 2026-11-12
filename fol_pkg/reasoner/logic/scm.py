from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Equation:
    effect: str
    negated: bool
    op: str
    causes: tuple[tuple[str, bool], ...]


@dataclass
class CausalProblem:
    equations: list[Equation]
    interventions: list[tuple[str, bool]]
    target: str
    observations: dict[str, bool] = field(default_factory=dict)
    priors: dict[str, float] = field(default_factory=dict)
