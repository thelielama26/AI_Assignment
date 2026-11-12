from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from ..logic.formula import And, Exists, Forall, Formula, Iff, Imp, Not, Or, Pred, Xor
from ..logic.terms import Term, Var
from .lexicon import (
    COPULAS, DETERMINERS, DO, FILLERS, GENERIC_NOUNS, GENERIC_PRONOUN_QUANTIFIERS, HAVE, MODALS,
    PREPOSITIONS, PRONOUNS, QUANTIFIERS, is_verb, stem,
)
from .parser import ParseError

WORD = re.compile(r"[A-Za-z0-9$%][A-Za-z0-9$%'’\-\.]*[A-Za-z0-9$%]|[A-Za-z0-9$%]|[,;]")
CONTRACTIONS = {"don": "do", "doesn": "does", "didn": "did", "isn": "is", "aren": "are", "wasn": "was",
                "weren": "were", "hasn": "has", "haven": "have", "hadn": "had", "won": "will",
                "can": "can", "couldn": "could", "wouldn": "would", "shouldn": "should"}
NAME_CONNECTORS = {"of", "de", "von", "van", "der", "la", "le", "du", "del", "the"}
RELATIVE = {"who", "that", "which", "whom"}
PLURAL_VERBS = {"are", "were", "do", "have"}
BAD_NP_END = RELATIVE | {"and", "or", ",", "of", "in", "on", "at", "by", "with", "to", "for", "from",
                         "the", "a", "an", "not", "either", "neither", "both", "nor", ";"}
CLAUSE_STARTERS = {"he", "she", "they", "it", "there", "all", "every", "each", "no", "some", "any",
                   "someone", "everyone", "nobody", "something", "everything", "if", "either", "neither"}


@dataclass(frozen=True, slots=True)
class Tok:
    text: str
    low: str
    cap: bool


def tokenize(sentence: str) -> list[Tok]:
    toks: list[Tok] = []
    sentence = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", sentence)
    sentence = re.sub(r"[“\"]([^”\"]+)[”\"]", lambda m: " " + re.sub(r"[^A-Za-z0-9]+", "", m.group(1)).capitalize() + " ", sentence)
    sentence = re.sub(r",?\s+or both\b|\band/or\b", " or", sentence)
    for m in WORD.finditer(sentence):
        w = m.group(0)
        low = w.lower().replace("’", "'")
        if low == "cannot":
            toks += [Tok("can", "can", False), Tok("not", "not", False)]
        elif low.endswith("n't") and len(low) > 3:
            base = CONTRACTIONS.get(low[:-3], low[:-3])
            toks += [Tok(base, base, w[0].isupper()), Tok("not", "not", False)]
        else:
            toks.append(Tok(w, low, w[0].isupper() or w[0].isdigit()))
    return [t for t in toks if t.low not in FILLERS]


def is_possessive(tok: Tok) -> bool:
    return tok.low.endswith("'s") or tok.low.endswith("s'")


def split_top(toks: list[Tok], separators: set[str]) -> list[list[Tok]]:
    parts: list[list[Tok]] = [[]]
    for t in toks:
        if t.low in separators:
            parts.append([])
        else:
            parts[-1].append(t)
    return parts


def strip_commas(toks: list[Tok]) -> list[Tok]:
    start, end = 0, len(toks)
    while start < end and toks[start].low in {",", ";"}:
        start += 1
    while end > start and toks[end - 1].low in {",", ";"}:
        end -= 1
    return toks[start:end]


def negate(f: Formula) -> Formula:
    return f.f if isinstance(f, Not) else Not(f)


Builder = Callable[[Term], Formula]


class SentenceParser:
    def __init__(self, exclusive_either: bool = True):
        self.exclusive_either = exclusive_either
        self.var: Var | None = None
        self.var_noun: str | None = None
        self.quant = "forall"
        self.restrict: list[Formula] = []
        self.name: str | None = None
        self.antecedent = False

    def parse(self, text: str) -> Formula:
        toks = strip_commas(tokenize(text))
        if not toks:
            raise ParseError(text)
        return self.close(self.formula(toks))

    def state(self):
        return (self.var, self.var_noun, self.quant, list(self.restrict), self.name, self.antecedent)

    def restore(self, saved) -> None:
        self.var, self.var_noun, self.quant, restrict, self.name, self.antecedent = saved
        self.restrict = list(restrict)

    def close(self, f: Formula) -> Formula:
        if self.var is None:
            return f
        restrictors = tuple(self.restrict)
        if self.quant == "exists":
            return Exists(self.var, And(restrictors + (f,)))
        return Forall(self.var, Imp(And(restrictors), f) if restrictors else f)

    def formula(self, toks: list[Tok]) -> Formula:
        toks = strip_commas(toks)
        if not toks:
            raise ParseError("empty")
        words = [t.low for t in toks]
        if words[:3] == ["it", "is", "not"] and len(words) > 4 and words[3] in {"the", "true", "possible"}:
            if "that" in words:
                return Not(self.formula(toks[words.index("that") + 1:]))
        if words[0] in {"if", "when", "whenever"}:
            if words[:4] == ["if", "and", "only", "if"]:
                return self.conditional(toks[3:])
            return self.conditional(toks)
        for i in range(1, len(toks) - 3):
            if words[i:i + 4] == ["if", "and", "only", "if"]:
                left = self.formula(toks[:i])
                return Iff(left, self.formula(toks[i + 4:]))
        for i in range(1, len(toks)):
            if words[i] in {"if", "unless", "when", "whenever"} and i + 1 < len(toks):
                left, right = toks[:i], toks[i + 1:]
                if words[i] == "unless":
                    return Or((self.formula(left), self.formula(right)))
                only = left and left[-1].low == "only"
                consequent = self.formula(left[:-1] if only else left)
                antecedent = self.formula(right)
                return Imp(consequent, antecedent) if only else Imp(antecedent, consequent)
        split = self.split_clauses(toks)
        if split is not None:
            return split
        return self.clause(toks)

    def conditional(self, toks: list[Tok]) -> Formula:
        words = [t.low for t in toks]
        if "then" in words:
            t = words.index("then")
            ant, cons = toks[1:t], toks[t + 1:]
        else:
            if "," not in words:
                raise ParseError("if without then")
            c = words.index(",")
            ant, cons = toks[1:c], toks[c + 1:]
        self.antecedent = True
        a = self.formula(ant)
        self.antecedent = False
        return Imp(a, self.formula(cons))

    def starts_clause(self, toks: list[Tok], i: int) -> bool:
        if i >= len(toks):
            return False
        t = toks[i]
        rest = [x.low for x in toks[i:]]
        has_verb = any(w in COPULAS or w in DO or w in HAVE or w in MODALS or is_verb(w) for w in rest[1:])
        if t.low in CLAUSE_STARTERS:
            return True
        if t.low in DETERMINERS:
            return any(w in COPULAS or w in DO or w in HAVE for w in rest)
        if t.cap and not is_possessive(t):
            return has_verb
        return False

    def split_clauses(self, toks: list[Tok]) -> Formula | None:
        n = len(toks)
        for separators, combine in (({"or"}, "or"), ({"but", ";"}, "and"), ({"and"}, "and")):
            for i in range(1, n - 1):
                if toks[i].low not in separators:
                    continue
                left = strip_commas(toks[:i])
                right_start = i + 1
                if not self.starts_clause(toks, right_start):
                    continue
                right = toks[right_start:]
                exclusive = False
                if combine == "or":
                    either = [k for k, t in enumerate(left) if t.low == "either"]
                    if either:
                        left = left[:either[0]] + left[either[0] + 1:]
                        exclusive = self.exclusive_either
                    elif left and left[0].low == "neither":
                        continue
                saved = self.state()
                try:
                    lf = self.formula(left)
                    rf = self.formula(right)
                except ParseError:
                    self.restore(saved)
                    continue
                if combine == "or":
                    return Xor(lf, rf) if exclusive else Or((lf, rf))
                return And((lf, rf))
        return None

    def pronoun(self) -> Term:
        if self.var is not None:
            return self.var
        if self.name is not None:
            return self.name
        raise ParseError("unresolved pronoun")

    def name_run(self, toks: list[Tok], i: int) -> int:
        j = i
        while j < len(toks):
            t = toks[j]
            if (t.cap or t.text[0].isdigit()) and not is_possessive(t) and t.low not in {"if", "then"}:
                j += 1
            elif t.low in NAME_CONNECTORS and j > i and j + 1 < len(toks) and toks[j + 1].cap:
                j += 1
            else:
                break
        return j

    def name_term(self, toks: list[Tok]) -> str:
        words = [t.low for t in toks]
        if words and words[0] == "the":
            words = words[1:]
        return " ".join(words)

    def norm(self, toks: list[Tok]) -> str | None:
        words = [stem(t.low) for t in toks if t.low not in DETERMINERS and t.low not in {",", ";"}]
        words = [w for w in words if w not in GENERIC_NOUNS and w != "person"] or []
        return " ".join(words) if words else None

    def vp_start(self, toks: list[Tok], j: int) -> bool:
        low = toks[j].low
        if j > 0 and toks[j - 1].low in DETERMINERS | PREPOSITIONS | {"and", "or", ",", "not"} | RELATIVE:
            return False
        return (low in COPULAS or low in DO or low in HAVE or low in MODALS
                or low in {"either", "both", "neither", "never"} or is_verb(low))

    def with_subject(self, toks: list[Tok], i0: int, build: Callable[[list[Tok]], Term],
                     negated: bool = False, allow_empty: bool = False) -> Formula:
        for j in range(i0 if allow_empty else i0 + 1, len(toks)):
            if not self.vp_start(toks, j):
                continue
            np = strip_commas(toks[i0:j])
            if not np and not allow_empty:
                continue
            if np and np[-1].low in BAD_NP_END:
                continue
            saved = self.state()
            try:
                subject = build(np)
                body = self.vp(toks[j:])(subject)
                return negate(body) if negated else body
            except ParseError:
                self.restore(saved)
        raise ParseError("no subject/verb split")

    def start_generic(self, np: list[Tok], quant: str) -> Var:
        if self.var is not None:
            raise ParseError("two generic subjects")
        var = Var("x")
        self.var = var
        self.quant = "forall" if (quant in {"forall", "none"} or self.antecedent) else "exists"
        self.restrict = []
        r = next((k for k, t in enumerate(np) if t.low in RELATIVE), None)
        head = np if r is None else np[:r]
        self.var_noun = self.norm(head)
        pieces = []
        if head:
            f = self.phrase_formula(var, head)
            if f is not None:
                pieces.append(f)
        if r is not None:
            pieces.append(self.vp(np[r + 1:])(var))
        self.restrict = pieces
        return var

    def clause(self, toks: list[Tok]) -> Formula:
        first = toks[0]
        low = first.low
        if low == "there":
            return self.existential(toks)
        if low in PRONOUNS:
            return self.vp(toks[1:])(self.pronoun())
        if low in GENERIC_PRONOUN_QUANTIFIERS:
            q = GENERIC_PRONOUN_QUANTIFIERS[low]
            return self.with_subject(toks, 1, lambda np: self.start_generic(np, q), negated=(q == "none"),
                                     allow_empty=True)
        if low in QUANTIFIERS:
            q = QUANTIFIERS[low]
            i = 1
            if i < len(toks) and toks[i].low == "of":
                i += 1
            if i < len(toks) and toks[i].low == "the":
                i += 1
            if low == "no" and i < len(toks) and toks[i].low == "one":
                return self.with_subject(toks, i + 1, lambda np: self.start_generic(np, q), negated=True,
                                         allow_empty=True)
            return self.with_subject(toks, i, lambda np: self.start_generic(np, q), negated=(q == "none"))
        if low in {"a", "an"}:
            return self.with_subject(toks, 1, lambda np: self.start_generic(np, "forall"))
        if low == "the":
            return self.with_subject(toks, 1, self.definite)
        j = self.name_run(toks, 0)
        if j > 0:
            nxt = toks[j].low if j < len(toks) else None
            plural = nxt in PLURAL_VERBS or (j == 1 and nxt is not None and is_verb(nxt)
                                              and not nxt.endswith(("s", "ed")) and nxt not in COPULAS
                                              and low.endswith("s") and low not in {"is", "was"})
            if nxt == "and":
                k = self.name_run(toks, j + 1)
                if k > j + 1:
                    names = [self.name_term(toks[:j]), self.name_term(toks[j + 1:k])]
                    parts = [self.vp(toks[k:])(n) for n in names]
                    return And(tuple(parts))
            if not plural and j < len(toks) and low not in GENERIC_NOUNS and stem(low) not in GENERIC_NOUNS:
                saved = self.state()
                subject = self.name_term(toks[:j])
                try:
                    self.name = subject
                    return self.vp(toks[j:])(subject)
                except ParseError:
                    self.restore(saved)
        return self.with_subject(toks, 0, lambda np: self.start_generic(np, "forall"))

    def definite(self, np: list[Tok]) -> Term:
        if not np:
            raise ParseError("empty definite")
        if all(t.cap or t.low in NAME_CONNECTORS for t in np) and not is_possessive(np[0]):
            term = self.name_term(np)
        else:
            if any(t.low in RELATIVE or t.low == "," for t in np):
                raise ParseError("complex definite")
            noun = self.norm(np)
            if noun is None:
                raise ParseError("generic definite")
            if self.var is not None and self.var_noun == noun:
                return self.var
            term = noun
        self.name = term
        return term

    def existential(self, toks: list[Tok]) -> Formula:
        words = [t.low for t in toks]
        if len(toks) < 3 or words[1] not in COPULAS | {"exists", "exist"}:
            raise ParseError("there")
        i = 2
        negated = False
        if i < len(toks) and toks[i].low in {"no"}:
            negated = True
            i += 1
        elif i < len(toks) and toks[i].low in {"a", "an", "some", "one", "at", "several"}:
            i += 1
            if toks[i - 1].low == "at" and i < len(toks) and toks[i].low == "least":
                i += 2
        np = toks[i:]
        if not np:
            raise ParseError("empty existential")
        var = Var("x")
        r = next((k for k, t in enumerate(np) if t.low in RELATIVE), None)
        head = np if r is None else np[:r]
        pieces = []
        f = self.phrase_formula(var, head)
        if f is not None:
            pieces.append(f)
        if r is not None:
            pieces.append(self.vp(np[r + 1:])(var))
        body = Exists(var, And(tuple(pieces)))
        return Not(body) if negated else body

    def vp(self, toks: list[Tok]) -> Builder:
        toks = strip_commas(toks)
        if not toks:
            raise ParseError("empty vp")
        low = toks[0].low
        if low == "either":
            parts = [self.vp(p) for p in split_top(toks[1:], {"or"}) if p]
            if len(parts) < 2:
                raise ParseError("either")
            return lambda s: self.combine_or([p(s) for p in parts], self.exclusive_either)
        if low == "neither":
            parts = [self.vp(p) for p in split_top(toks[1:], {"nor"}) if p]
            if len(parts) < 2:
                raise ParseError("neither")
            return lambda s: And(tuple(Not(p(s)) for p in parts))
        if low == "both":
            parts = [self.vp(p) for p in split_top(toks[1:], {"and"}) if p]
            return lambda s: And(tuple(p(s) for p in parts))
        groups = self.vp_coordination(toks)
        if groups is not None:
            builders, ops = groups
            return lambda s: self.fold([b(s) for b in builders], ops)
        return self.simple_vp(toks)

    def combine_or(self, parts: list[Formula], exclusive: bool) -> Formula:
        if len(parts) == 2 and exclusive:
            return Xor(parts[0], parts[1])
        return Or(tuple(parts))

    def fold(self, parts: list[Formula], ops: list[str]) -> Formula:
        groups = [[parts[0]]]
        for p, op in zip(parts[1:], ops):
            if op == "or":
                groups.append([p])
            else:
                groups[-1].append(p)
        ands = [g[0] if len(g) == 1 else And(tuple(g)) for g in groups]
        return ands[0] if len(ands) == 1 else Or(tuple(ands))

    def vp_coordination(self, toks: list[Tok]) -> tuple[list[Builder], list[str]] | None:
        cuts: list[tuple[int, str, int]] = []
        pending = {"and": 0, "or": 0}
        for i in range(1, len(toks)):
            if toks[i].low == "both":
                pending["and"] += 1
            elif toks[i].low == "either":
                pending["or"] += 1
            elif toks[i].low in pending and pending[toks[i].low]:
                pending[toks[i].low] -= 1
                continue
            if toks[i].low in {"and", "or", "but", ","}:
                k = i + 1
                op = {"and": "and", "or": "or", "but": "and", ",": "and"}[toks[i].low]
                while k < len(toks) and toks[k].low in {"and", "or", "but", ","}:
                    if toks[k].low == "or":
                        op = "or"
                    k += 1
                if k < len(toks) and self.vp_start_after_cut(toks, k):
                    cuts.append((i, op, k))
        if not cuts:
            return None
        builders, ops, start = [], [], 0
        for i, op, k in cuts:
            builders.append(self.vp(toks[start:i]))
            ops.append(op)
            start = k
        builders.append(self.vp(toks[start:]))
        return builders, ops

    def vp_start_after_cut(self, toks: list[Tok], k: int) -> bool:
        low = toks[k].low
        return (low in COPULAS or low in DO or low in HAVE or low in MODALS
                or low in {"either", "neither", "both", "never"} or is_verb(low))

    def simple_vp(self, toks: list[Tok]) -> Builder:
        n = len(toks)
        i = 0
        neg = False
        while i < n and (toks[i].low in DO or toks[i].low in MODALS):
            i += 1
            if i < n and toks[i].low == "not":
                neg = True
                i += 1
        if i < n and toks[i].low == "never":
            neg = True
            i += 1
        if i >= n:
            raise ParseError("empty verb phrase")
        low = toks[i].low
        if low in COPULAS:
            i += 1
            if i < n and toks[i].low == "not":
                neg = not neg
                i += 1
            comp = self.complement(toks[i:])
            return (lambda s: negate(comp(s))) if neg else comp
        if low in HAVE:
            i += 1
            if i < n and toks[i].low == "not":
                neg = True
                i += 1
            rest = [Tok("have", "have", False)] + toks[i:]
        else:
            if low in DETERMINERS or low in PREPOSITIONS or low in {"and", "or", "if", "then", "that", "who", "which"}:
                raise ParseError("not a verb phrase")
            rest = toks[i:]
        if any(t.low in COPULAS or t.low in DO or t.low in MODALS for t in rest):
            raise ParseError("stray auxiliary")

        def build(s: Term) -> Formula:
            f = self.phrase_formula(s, rest)
            if f is None:
                raise ParseError("empty predicate")
            return negate(f) if neg else f

        return build

    def complement(self, toks: list[Tok]) -> Builder:
        toks = strip_commas(toks)
        if not toks:
            raise ParseError("empty complement")
        low = toks[0].low
        if low == "either":
            parts = [self.complement(p) for p in split_top(toks[1:], {"or"}) if p]
            return lambda s: self.combine_or([p(s) for p in parts], self.exclusive_either)
        if low == "neither":
            parts = [self.complement(p) for p in split_top(toks[1:], {"nor"}) if p]
            return lambda s: And(tuple(Not(p(s)) for p in parts))
        if low == "both":
            parts = [self.complement(p) for p in split_top(toks[1:], {"and"}) if p]
            return lambda s: And(tuple(p(s) for p in parts))
        r = next((k for k, t in enumerate(toks) if t.low in RELATIVE), len(toks))
        for sep, joiner in (({"or"}, "or"), ({"and"}, "and")):
            cut = next((k for k in range(1, r) if toks[k].low in sep), None)
            if cut is not None:
                left, right = self.complement(toks[:cut]), self.complement(toks[cut + 1:])
                if joiner == "or":
                    return lambda s: Or((left(s), right(s)))
                return lambda s: And((left(s), right(s)))
        return self.np_complement(toks)

    def np_complement(self, toks: list[Tok]) -> Builder:
        r = next((k for k, t in enumerate(toks) if t.low in RELATIVE), None)
        if r is None:
            def build(s: Term) -> Formula:
                f = self.phrase_formula(s, toks)
                if f is None:
                    raise ParseError("empty complement")
                return f
            return build
        head, rel = toks[:r], self.vp(toks[r + 1:])

        def build_rel(s: Term) -> Formula:
            pieces = []
            f = self.phrase_formula(s, head) if head else None
            if f is not None:
                pieces.append(f)
            pieces.append(rel(s))
            return pieces[0] if len(pieces) == 1 else And(tuple(pieces))

        return build_rel

    def is_name_start(self, toks: list[Tok], k: int) -> bool:
        t = toks[k]
        if not (t.cap or t.text[0].isdigit()) or is_possessive(t):
            return False
        b = k - 1
        if b >= 0 and toks[b].low == "the":
            b -= 1
        if b < 0:
            return False
        return toks[b].low in PREPOSITIONS or is_verb(toks[b].low)

    def phrase_formula(self, subject: Term, toks: list[Tok]) -> Formula | None:
        toks = strip_commas(toks)
        spans: list[tuple[int, int]] = []
        k = 0
        while k < len(toks):
            if self.is_name_start(toks, k):
                end = self.name_run(toks, k)
                if end == len(toks):
                    spans.append((k, end))
                k = end
            else:
                k += 1
        if not spans:
            name = self.norm(toks)
            return None if name is None else Pred(name, (subject,))
        if len(spans) > 1:
            raise ParseError("several names")
        s, e = spans[0]
        if e < len(toks):
            raise ParseError("material after name")
        left = toks[:s]
        while left and left[-1].low == "the":
            left = left[:-1]
        if not left:
            raise ParseError("bare name")
        term = self.name_term(toks[s:e])
        last = left[-1]
        if last.low in PREPOSITIONS:
            before = left[:-1]
            if not before:
                return Pred(last.low, (subject, term))
            if is_verb(before[-1].low):
                return Pred(self.norm(left) or last.low, (subject, term))
            head = self.norm(before)
            relation = Pred(last.low, (subject, term))
            return relation if head is None else And((Pred(head, (subject,)), relation))
        name = self.norm(left)
        if name is None:
            raise ParseError("empty relation")
        return Pred(name, (subject, term))


def parse_formula(text: str, exclusive_either: bool = True) -> Formula:
    return SentenceParser(exclusive_either).parse(text)
