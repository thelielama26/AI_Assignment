from __future__ import annotations

from dataclasses import dataclass

from .terms import Term, Var


@dataclass(frozen=True, slots=True)
class Pred:
    name: str
    args: tuple[Term, ...]


@dataclass(frozen=True, slots=True)
class Not:
    f: Formula


@dataclass(frozen=True, slots=True)
class And:
    fs: tuple[Formula, ...]


@dataclass(frozen=True, slots=True)
class Or:
    fs: tuple[Formula, ...]


@dataclass(frozen=True, slots=True)
class Imp:
    a: Formula
    b: Formula


@dataclass(frozen=True, slots=True)
class Iff:
    a: Formula
    b: Formula


@dataclass(frozen=True, slots=True)
class Xor:
    a: Formula
    b: Formula


@dataclass(frozen=True, slots=True)
class Forall:
    var: Var
    body: Formula


@dataclass(frozen=True, slots=True)
class Exists:
    var: Var
    body: Formula


Formula = Pred | Not | And | Or | Imp | Iff | Xor | Forall | Exists


def show(f: Formula) -> str:
    if isinstance(f, Pred):
        return f"{f.name}({', '.join(map(str, f.args))})"
    if isinstance(f, Not):
        return f"¬{show(f.f)}"
    if isinstance(f, And):
        return "(" + " ∧ ".join(map(show, f.fs)) + ")"
    if isinstance(f, Or):
        return "(" + " ∨ ".join(map(show, f.fs)) + ")"
    if isinstance(f, Imp):
        return f"({show(f.a)} → {show(f.b)})"
    if isinstance(f, Iff):
        return f"({show(f.a)} ↔ {show(f.b)})"
    if isinstance(f, Xor):
        return f"({show(f.a)} ⊕ {show(f.b)})"
    if isinstance(f, Forall):
        return f"∀{f.var.name} {show(f.body)}"
    return f"∃{f.var.name} {show(f.body)}"
