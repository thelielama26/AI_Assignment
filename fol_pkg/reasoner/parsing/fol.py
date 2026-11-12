from __future__ import annotations

import re

from ..logic.formula import And, Exists, Forall, Formula, Iff, Imp, Not, Or, Pred, Xor
from ..logic.terms import Fn, Term, Var
from .parser import ParseError

TOKEN = re.compile(r"\s*(∀|∃|→|↔|⟷|⊕|∧|∨|¬|≠|=|\(|\)|,|[^\s()∀∃→↔⟷⊕∧∨¬≠=,]+)")
QUANTIFIERS = {"∀", "∃"}


def _tokens(text: str) -> list[str]:
    tokens, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise ParseError(text)
        tokens.append(m.group(1))
        pos = m.end()
    return tokens


class _Parser:
    def __init__(self, tokens: list[str]):
        self.toks = tokens
        self.i = 0
        self.bound: dict[str, Var] = {}

    def peek(self) -> str | None:
        return self.toks[self.i] if self.i < len(self.toks) else None

    def take(self, expected: str | None = None) -> str:
        tok = self.peek()
        if tok is None or (expected is not None and tok != expected):
            raise ParseError(f"expected {expected!r} at {self.i}")
        self.i += 1
        return tok

    def formula(self) -> Formula:
        left = self.implication()
        while self.peek() in ("↔", "⟷"):
            self.take()
            left = Iff(left, self.implication())
        return left

    def implication(self) -> Formula:
        left = self.disjunction()
        if self.peek() == "→":
            self.take()
            return Imp(left, self.implication())
        return left

    def disjunction(self) -> Formula:
        left = self.conjunction()
        while self.peek() in ("∨", "⊕"):
            op = self.take()
            right = self.conjunction()
            left = Or((left, right)) if op == "∨" else Xor(left, right)
        return left

    def conjunction(self) -> Formula:
        parts = [self.unary()]
        while self.peek() == "∧":
            self.take()
            parts.append(self.unary())
        return parts[0] if len(parts) == 1 else And(tuple(parts))

    def unary(self) -> Formula:
        tok = self.peek()
        if tok == "¬":
            self.take()
            return Not(self.unary())
        if tok in QUANTIFIERS:
            self.take()
            name = self.take()
            var = Var(name)
            saved = self.bound.get(name)
            self.bound[name] = var
            body = self.unary()
            if saved is None:
                del self.bound[name]
            else:
                self.bound[name] = saved
            return Forall(var, body) if tok == "∀" else Exists(var, body)
        if tok == "(":
            self.take()
            inner = self.formula()
            self.take(")")
            return inner
        return self.atom()

    def term(self) -> Term:
        name = self.take()
        if name in {"(", ")", ","}:
            raise ParseError(name)
        if self.peek() == "(":
            self.take()
            args = [self.term()]
            while self.peek() == ",":
                self.take()
                args.append(self.term())
            self.take(")")
            return Fn(name.lower(), tuple(args))
        return self.bound.get(name, name.lower())

    def atom(self) -> Formula:
        name = self.take()
        if self.peek() == "(":
            self.take()
            args = [self.term()]
            while self.peek() == ",":
                self.take()
                args.append(self.term())
            self.take(")")
            return Pred(name.lower(), tuple(args))
        left = self.bound.get(name, name.lower())
        op = self.peek()
        if op in ("=", "≠"):
            self.take()
            right = self.term()
            eq = Pred("=", (left, right))
            return eq if op == "=" else Not(eq)
        raise ParseError(f"bare symbol {name}")


def parse_fol(text: str) -> Formula:
    parser = _Parser(_tokens(text))
    result = parser.formula()
    if parser.peek() is not None:
        raise ParseError(f"trailing input: {parser.peek()}")
    return result
