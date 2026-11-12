from __future__ import annotations

import re

from ..logic.terms import Atom, Literal, Var
from .normalize import lemma

X = Var("X")
VARIABLE_WORDS = {"someone", "something", "it", "they"}

NAME = r"[A-Z][a-z]+"
NOUN_PHRASE = rf"(?:the [a-z]+(?: [a-z]+)*|{NAME})"
SUBJECT = rf"(?:someone|something|it|they|{NOUN_PHRASE})"
OBJECT = rf"(?:{NOUN_PHRASE}|someone|something)"

IS = re.compile(rf"^(?P<s>{SUBJECT}) (?:is|are) (?P<neg>not )?(?P<adj>[a-z]+)$")
DOES_NOT = re.compile(rf"^(?P<s>{SUBJECT}) (?:does|do) not (?P<v>[a-z]+) (?P<o>{OBJECT})$")
VERB = re.compile(rf"^(?P<s>{SUBJECT}) (?P<v>[a-z]+) (?P<o>{OBJECT})$")
CONTINUATION = re.compile(r"^(?P<neg>not )?(?P<adj>[a-z]+)$")
UNIVERSAL = re.compile(
    r"^(?:all )?(?P<conds>(?:not )?[a-z]+(?:, (?:not )?[a-z]+)*) (?:things|people) "
    r"(?:are|is) (?P<neg>not )?(?P<adj>[a-z]+)$"
)
IF_THEN = re.compile(r"^if (?P<cond>.+?),? then,? (?P<head>.+)$")


def term(text: str):
    if text in VARIABLE_WORDS:
        return X
    return text[4:] if text.startswith("the ") else text.lower()


def attribute(subject, adj: str, positive: bool) -> Literal:
    return Literal(Atom(adj, (subject,)), positive)


def relation(subject, verb: str, obj, positive: bool) -> Literal:
    return Literal(Atom(verb, (subject, term(obj) if isinstance(obj, str) else obj)), positive)


def clause(text: str) -> tuple[object, Literal] | None:
    m = IS.match(text)
    if m:
        subject = term(m["s"])
        return subject, attribute(subject, m["adj"], not m["neg"])
    m = DOES_NOT.match(text)
    if m:
        subject = term(m["s"])
        return subject, relation(subject, m["v"], m["o"], False)
    m = VERB.match(text)
    if m:
        subject = term(m["s"])
        return subject, relation(subject, lemma(m["v"]), m["o"], True)
    return None


def conjunction(text: str) -> list[Literal] | None:
    literals: list[Literal] = []
    subject = None
    for segment in text.split(" and "):
        segment = segment.strip()
        parsed = clause(segment)
        if parsed is not None:
            subject, literal = parsed
            literals.append(literal)
            continue
        m = CONTINUATION.match(segment)
        if m and subject is not None:
            literals.append(attribute(subject, m["adj"], not m["neg"]))
            continue
        return None
    return literals


def universal(text: str) -> list[tuple[tuple[Literal, ...], Literal]] | None:
    m = UNIVERSAL.match(text[:1].lower() + text[1:])
    if not m:
        return None
    body = []
    for cond in m["conds"].split(", "):
        negated = cond.startswith("not ")
        body.append(attribute(X, cond.removeprefix("not "), not negated))
    return [(tuple(body), attribute(X, m["adj"], not m["neg"]))]
