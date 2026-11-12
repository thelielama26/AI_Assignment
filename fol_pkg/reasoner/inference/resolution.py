from __future__ import annotations

import heapq
import time
from dataclasses import dataclass
from itertools import count

from ..logic.cnf import Clause
from ..logic.terms import Atom, Fn, Literal, Term, Var
from ..logic.unify import apply, match_term, substitute, unify


@dataclass
class Result:
    proved: bool
    given: int = 0
    generated: int = 0
    reason: str = "saturated"
    steps: list | None = None


def _size(term: Term) -> int:
    if isinstance(term, Fn):
        return 1 + sum(_size(a) for a in term.args)
    return 1


def _weight(clause: Clause) -> int:
    return sum(1 + sum(_size(a) for a in lit.atom.args) for lit in clause)


def _term_vars(term: Term, out: list[Var]) -> None:
    if isinstance(term, Var):
        out.append(term)
    elif isinstance(term, Fn):
        for a in term.args:
            _term_vars(a, out)


def _rename_term(term: Term, mapping: dict[Var, Var]) -> Term:
    if isinstance(term, Var):
        return mapping[term]
    if isinstance(term, Fn):
        return Fn(term.name, tuple(_rename_term(a, mapping) for a in term.args))
    return term


def _rename(clause: Clause, tag: str) -> Clause:
    mapping: dict[Var, Var] = {}
    found: list[Var] = []
    for lit in clause:
        for a in lit.atom.args:
            _term_vars(a, found)
    for v in found:
        if v not in mapping:
            mapping[v] = Var(f"{tag}{len(mapping)}")
    return tuple(
        Literal(Atom(l.atom.pred, tuple(_rename_term(a, mapping) for a in l.atom.args)), l.positive)
        for l in clause
    )


def _normalize(clause: Clause) -> Clause:
    ordered = sorted(clause, key=lambda l: (l.atom.pred, l.positive, _size_key(l)))
    return _rename(tuple(ordered), "_")


def _size_key(lit: Literal) -> str:
    return "".join("*" if isinstance(a, Var) else str(a) for a in lit.atom.args)


def _tautology(clause: Clause) -> bool:
    keys = {(l.atom, l.positive) for l in clause}
    return any((a, not s) in keys for a, s in keys)


def _dedupe(literals: list[Literal]) -> Clause:
    return tuple(dict.fromkeys(literals))


def subsumes(general: Clause, specific: Clause) -> bool:
    if len(general) > len(specific):
        return False

    def go(i: int, subst: dict) -> bool:
        if i == len(general):
            return True
        lit = general[i]
        for other in specific:
            if other.positive != lit.positive or other.atom.pred != lit.atom.pred:
                continue
            s: dict | None = subst
            for p, t in zip(lit.atom.args, other.atom.args):
                s = match_term(p, t, s)
                if s is None:
                    break
            if s is not None and go(i + 1, s):
                return True
        return False

    return go(0, {})


def _resolvents(c1: Clause, c2: Clause) -> list[Clause]:
    out = []
    for i, l1 in enumerate(c1):
        for j, l2 in enumerate(c2):
            if l1.positive == l2.positive or l1.atom.pred != l2.atom.pred:
                continue
            subst = unify(l1.atom, l2.atom)
            if subst is None:
                continue
            rest = [l for k, l in enumerate(c1) if k != i] + [l for k, l in enumerate(c2) if k != j]
            out.append(_dedupe([Literal(substitute(l.atom, subst), l.positive) for l in rest]))
    return out


def _factors(clause: Clause) -> list[Clause]:
    out = []
    for i in range(len(clause)):
        for j in range(i + 1, len(clause)):
            a, b = clause[i], clause[j]
            if a.positive != b.positive or a.atom.pred != b.atom.pred:
                continue
            subst = unify(a.atom, b.atom)
            if subst is not None:
                out.append(_dedupe([Literal(substitute(l.atom, subst), l.positive) for l in clause]))
    return out


def refute(
    usable: list[Clause],
    sos: list[Clause],
    max_given: int = 3000,
    max_generated: int = 40000,
    timeout: float = 1.0,
) -> Result:
    deadline = time.perf_counter() + timeout
    tiebreak = count()
    renames = count()
    passive: list[tuple[int, int, Clause]] = []
    seen: set[Clause] = set()
    kept_by_pred: dict[str, list[Clause]] = {}
    partners: list[Clause] = []

    def keep(clause: Clause) -> None:
        for lit in clause:
            kept_by_pred.setdefault(lit.atom.pred, []).append(clause)
        partners.append(clause)

    def redundant(clause: Clause) -> bool:
        if clause in seen:
            return True
        seen.add(clause)
        for lit in clause:
            for other in kept_by_pred.get(lit.atom.pred, ()):
                if len(other) <= len(clause) and subsumes(other, clause):
                    return True
        return False

    for clause in usable:
        norm = _normalize(clause)
        if not norm:
            return Result(True, reason="inconsistent premises")
        seen.add(norm)
        keep(norm)
    for clause in sos:
        norm = _normalize(clause)
        if not norm:
            return Result(True, reason="empty clause")
        if norm not in seen:
            seen.add(norm)
            heapq.heappush(passive, (_weight(norm), next(tiebreak), norm))

    given = generated = 0
    while passive:
        if given >= max_given or generated >= max_generated:
            return Result(False, given, generated, "limit")
        if time.perf_counter() > deadline:
            return Result(False, given, generated, "timeout")
        _, _, current = heapq.heappop(passive)
        if any(len(o) <= len(current) and subsumes(o, current) for lit in current
               for o in kept_by_pred.get(lit.atom.pred, ())):
            continue
        given += 1
        candidates = list(_factors(current))
        seen_partners: set[int] = set()
        for lit in current:
            for other in kept_by_pred.get(lit.atom.pred, ()):
                if id(other) in seen_partners:
                    continue
                seen_partners.add(id(other))
                candidates.extend(_resolvents(current, _rename(other, f"r{next(renames)}_")))
        candidates.extend(_resolvents(current, _rename(current, f"r{next(renames)}_")))
        keep(current)
        for raw in candidates:
            generated += 1
            if not raw:
                return Result(True, given, generated, "refuted")
            if _tautology(raw):
                continue
            clause = _normalize(raw)
            if redundant(clause):
                continue
            heapq.heappush(passive, (_weight(clause), next(tiebreak), clause))
    return Result(False, given, generated, "saturated")
