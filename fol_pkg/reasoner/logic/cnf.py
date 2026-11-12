from __future__ import annotations

from itertools import count, product

from .formula import And, Exists, Forall, Formula, Iff, Imp, Not, Or, Pred, Xor
from .terms import Atom, Fn, Literal, Term, Var

Clause = tuple[Literal, ...]

MAX_CLAUSES = 256


class TooLarge(Exception):
    pass


def nnf(f: Formula, positive: bool = True) -> Formula:
    if isinstance(f, Pred):
        return f if positive else Not(f)
    if isinstance(f, Not):
        return nnf(f.f, not positive)
    if isinstance(f, And):
        parts = tuple(nnf(g, positive) for g in f.fs)
        return And(parts) if positive else Or(parts)
    if isinstance(f, Or):
        parts = tuple(nnf(g, positive) for g in f.fs)
        return Or(parts) if positive else And(parts)
    if isinstance(f, Imp):
        return nnf(Or((Not(f.a), f.b)), positive)
    if isinstance(f, Iff):
        return nnf(And((Imp(f.a, f.b), Imp(f.b, f.a))), positive)
    if isinstance(f, Xor):
        return nnf(And((Or((f.a, f.b)), Not(And((f.a, f.b))))), positive)
    if isinstance(f, Forall):
        body = nnf(f.body, positive)
        return Forall(f.var, body) if positive else Exists(f.var, body)
    body = nnf(f.body, positive)
    return Exists(f.var, body) if positive else Forall(f.var, body)


def _subst_term(term: Term, env: dict[Var, Term]) -> Term:
    if isinstance(term, Var):
        return env.get(term, term)
    if isinstance(term, Fn):
        return Fn(term.name, tuple(_subst_term(a, env) for a in term.args))
    return term


class _Skolemizer:
    def __init__(self, tag: str):
        self.tag = tag
        self.ids = count()

    def run(self, f: Formula, env: dict[Var, Term], universals: tuple[Var, ...]) -> Formula:
        if isinstance(f, Pred):
            return Pred(f.name, tuple(_subst_term(a, env) for a in f.args))
        if isinstance(f, Not):
            return Not(self.run(f.f, env, universals))
        if isinstance(f, (And, Or)):
            return type(f)(tuple(self.run(g, env, universals) for g in f.fs))
        n = next(self.ids)
        if isinstance(f, Forall):
            fresh = Var(f"{f.var.name}_{self.tag}{n}")
            return self.run(f.body, {**env, f.var: fresh}, universals + (fresh,))
        skolem = Fn(f"sk{self.tag}{n}", universals) if universals else f"sk{self.tag}{n}"
        return self.run(f.body, {**env, f.var: skolem}, universals)


def _literals(f: Formula) -> list[list[Literal]]:
    if isinstance(f, Pred):
        return [[Literal(Atom(f.name, f.args), True)]]
    if isinstance(f, Not):
        p = f.f
        return [[Literal(Atom(p.name, p.args), False)]]
    if isinstance(f, And):
        out: list[list[Literal]] = []
        for g in f.fs:
            out.extend(_literals(g))
            if len(out) > MAX_CLAUSES:
                raise TooLarge
        return out
    parts = [_literals(g) for g in f.fs]
    size = 1
    for p in parts:
        size *= len(p)
    if size > MAX_CLAUSES:
        raise TooLarge
    return [[lit for clause in combo for lit in clause] for combo in product(*parts)]


def _tidy(literals: list[Literal]) -> Clause | None:
    seen: dict[Literal, None] = {}
    for lit in literals:
        seen[lit] = None
    for lit in seen:
        if Literal(lit.atom, not lit.positive) in seen:
            return None
    return tuple(seen)


def to_clauses(f: Formula, tag: str = "") -> list[Clause]:
    skolemized = _Skolemizer(tag).run(nnf(f), {}, ())
    clauses = []
    for raw in _literals(skolemized):
        clause = _tidy(raw)
        if clause is not None:
            clauses.append(clause)
    return clauses
