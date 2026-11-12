from __future__ import annotations

from dataclasses import dataclass

from ..logic.terms import Fact, Literal, Rule, Var

NEG = "~"

Model = dict[str, set[tuple[str, ...]]]


@dataclass(frozen=True, slots=True)
class CompiledRule:
    head: tuple[str, tuple]
    pos: tuple[tuple[str, tuple], ...]
    neg: tuple[tuple[str, tuple], ...]
    free: tuple[Var, ...]
    source: Rule


def signed_pred(lit: Literal) -> str:
    return lit.atom.pred if lit.positive else NEG + lit.atom.pred


def fact_key(lit: Literal) -> Fact:
    return signed_pred(lit), lit.atom.args


def compile_rule(rule: Rule, cwa: bool) -> CompiledRule:
    pos, neg = [], []
    for lit in rule.body:
        if lit.positive:
            pos.append((lit.atom.pred, lit.atom.args))
        elif cwa:
            neg.append((lit.atom.pred, lit.atom.args))
        else:
            pos.append((NEG + lit.atom.pred, lit.atom.args))
    bound = {a for _, args in pos for a in args if isinstance(a, Var)}
    needed = [a for a in rule.head.atom.args if isinstance(a, Var)]
    needed += [a for _, args in neg for a in args if isinstance(a, Var)]
    free = tuple(dict.fromkeys(v for v in needed if v not in bound))
    return CompiledRule((signed_pred(rule.head), rule.head.atom.args), tuple(pos), tuple(neg), free, rule)


def holds(lit: Literal, certain: Model, possible: Model, cwa: bool) -> bool:
    pred, args = lit.atom.pred, lit.atom.args
    if lit.positive:
        return args in certain.get(pred, ())
    explicit = args in certain.get(NEG + pred, ())
    if cwa:
        return explicit or args not in possible.get(pred, ())
    return explicit
