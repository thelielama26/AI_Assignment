from __future__ import annotations

from .terms import Atom, Fn, Term, Var

Subst = dict[Var, Term]


def walk(term: Term, subst: Subst) -> Term:
    while isinstance(term, Var) and term in subst:
        term = subst[term]
    return term


def occurs(var: Var, term: Term, subst: Subst) -> bool:
    term = walk(term, subst)
    if term == var:
        return True
    if isinstance(term, Fn):
        return any(occurs(var, a, subst) for a in term.args)
    return False


def unify_terms(a: Term, b: Term, subst: Subst) -> Subst | None:
    a, b = walk(a, subst), walk(b, subst)
    if a == b:
        return subst
    if isinstance(a, Var):
        return None if occurs(a, b, subst) else {**subst, a: b}
    if isinstance(b, Var):
        return None if occurs(b, a, subst) else {**subst, b: a}
    if isinstance(a, Fn) and isinstance(b, Fn) and a.name == b.name and len(a.args) == len(b.args):
        for x, y in zip(a.args, b.args):
            subst = unify_terms(x, y, subst)
            if subst is None:
                return None
        return subst
    return None


def unify(x: Atom, y: Atom, subst: Subst | None = None) -> Subst | None:
    if x.pred != y.pred or len(x.args) != len(y.args):
        return None
    subst = {} if subst is None else subst
    for a, b in zip(x.args, y.args):
        subst = unify_terms(a, b, subst)
        if subst is None:
            return None
    return subst


def match_term(pattern: Term, target: Term, subst: Subst) -> Subst | None:
    if isinstance(pattern, Var):
        bound = subst.get(pattern)
        if bound is None:
            return {**subst, pattern: target}
        return subst if bound == target else None
    if isinstance(pattern, Fn):
        if not isinstance(target, Fn) or pattern.name != target.name or len(pattern.args) != len(target.args):
            return None
        for p, t in zip(pattern.args, target.args):
            subst = match_term(p, t, subst)
            if subst is None:
                return None
        return subst
    return subst if pattern == target else None


def match(pattern: tuple[Term, ...], ground: tuple[Term, ...], subst: Subst) -> Subst | None:
    if len(pattern) != len(ground):
        return None
    out = subst
    for p, g in zip(pattern, ground):
        if isinstance(p, Var):
            bound = out.get(p)
            if bound is None:
                if out is subst:
                    out = dict(subst)
                out[p] = g
            elif bound != g:
                return None
        elif isinstance(p, str):
            if p != g:
                return None
        else:
            out = match_term(p, g, out)
            if out is None:
                return None
    return out


def apply(term: Term, subst: Subst) -> Term:
    term = walk(term, subst)
    if isinstance(term, Fn):
        return Fn(term.name, tuple(apply(a, subst) for a in term.args))
    return term


def substitute(atom: Atom, subst: Subst) -> Atom:
    return Atom(atom.pred, tuple(apply(a, subst) for a in atom.args))
