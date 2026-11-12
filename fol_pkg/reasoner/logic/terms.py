from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Var:
    name: str

    def __str__(self) -> str:
        return f"?{self.name}"


@dataclass(frozen=True, slots=True)
class Fn:
    name: str
    args: tuple[Term, ...]

    def __str__(self) -> str:
        return f"{self.name}({', '.join(map(str, self.args))})"


Term = str | Var | Fn
Fact = tuple[str, tuple[str, ...]]


def is_ground_term(term: Term) -> bool:
    if isinstance(term, Var):
        return False
    if isinstance(term, Fn):
        return all(is_ground_term(a) for a in term.args)
    return True


@dataclass(frozen=True, slots=True)
class Atom:
    pred: str
    args: tuple[Term, ...]

    @property
    def is_ground(self) -> bool:
        return all(is_ground_term(a) for a in self.args)

    def __str__(self) -> str:
        return f"{self.pred}({', '.join(map(str, self.args))})"


@dataclass(frozen=True, slots=True)
class Literal:
    atom: Atom
    positive: bool = True

    def __str__(self) -> str:
        return str(self.atom) if self.positive else f"not {self.atom}"


@dataclass(frozen=True, slots=True)
class Rule:
    head: Literal
    body: tuple[Literal, ...]

    def __str__(self) -> str:
        return f"{' & '.join(map(str, self.body))} -> {self.head}"
