from __future__ import annotations

from collections import deque
from itertools import product
from typing import Iterable

from ..logic.terms import Fact, Var
from ..logic.unify import match
from .negation import CompiledRule, Model


def _ground(args: tuple, subst: dict) -> tuple[str, ...]:
    return tuple(subst[a] if isinstance(a, Var) else a for a in args)


def least_model(
    rules: list[CompiledRule],
    facts: Iterable[Fact],
    blocked: Model | None,
    domain: tuple[str, ...],
    why: dict | None = None,
) -> Model:
    store: Model = {}
    queue: deque[Fact] = deque()

    def add(pred: str, args: tuple[str, ...], reason) -> None:
        bucket = store.setdefault(pred, set())
        if args in bucket:
            return
        bucket.add(args)
        queue.append((pred, args))
        if why is not None:
            why[(pred, args)] = reason

    def join(lits, k, subst):
        if k == len(lits):
            yield subst
            return
        pred, pattern = lits[k]
        bucket = store.get(pred, ())
        if all(not isinstance(p, Var) or p in subst for p in pattern):
            if _ground(pattern, subst) in bucket:
                yield from join(lits, k + 1, subst)
            return
        for fact_args in tuple(bucket):
            extended = match(pattern, fact_args, subst)
            if extended is not None:
                yield from join(lits, k + 1, extended)

    def fire(rule: CompiledRule, subst: dict) -> None:
        for values in product(domain, repeat=len(rule.free)):
            full = {**subst, **dict(zip(rule.free, values))} if rule.free else subst
            if blocked is not None and any(
                _ground(args, full) in blocked.get(pred, ()) for pred, args in rule.neg
            ):
                continue
            reason = None
            if why is not None:
                reason = (
                    rule.source,
                    tuple((p, _ground(a, full)) for p, a in rule.pos),
                    tuple((p, _ground(a, full)) for p, a in rule.neg),
                )
            add(rule.head[0], _ground(rule.head[1], full), reason)

    triggers: dict[str, list[tuple[CompiledRule, int, tuple]]] = {}
    for rule in rules:
        for i, (pred, _) in enumerate(rule.pos):
            triggers.setdefault(pred, []).append((rule, i, rule.pos[:i] + rule.pos[i + 1:]))

    for pred, args in facts:
        add(pred, args, None)
    for rule in rules:
        if not rule.pos:
            fire(rule, {})

    while queue:
        pred, args = queue.popleft()
        for rule, i, rest in triggers.get(pred, ()):
            start = match(rule.pos[i][1], args, {})
            if start is None:
                continue
            for subst in join(rest, 0, start):
                fire(rule, subst)
    return store


def _size(model: Model) -> int:
    return sum(len(v) for v in model.values())


def well_founded(
    rules: list[CompiledRule], facts: list[Fact], domain: tuple[str, ...]
) -> tuple[Model, Model]:
    if not any(r.neg for r in rules):
        model = least_model(rules, facts, None, domain)
        return model, model
    possible = least_model(rules, facts, None, domain)
    certain = least_model(rules, facts, possible, domain)
    while True:
        possible = least_model(rules, facts, certain, domain)
        grown = least_model(rules, facts, possible, domain)
        if _size(grown) == _size(certain):
            return grown, possible
        certain = grown
