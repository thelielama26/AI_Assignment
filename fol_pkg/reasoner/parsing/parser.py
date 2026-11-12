from __future__ import annotations

from ..logic.kb import KnowledgeBase
from ..logic.terms import Literal, Rule, Var
from .normalize import clean, split_sentences
from .patterns import IF_THEN, clause, conjunction, universal


class ParseError(ValueError):
    pass


def _is_ground(lit: Literal) -> bool:
    return lit.atom.is_ground


def parse_sentence(sentence: str) -> tuple[list[Literal], list[Rule]]:
    text = clean(sentence)
    m = IF_THEN.match(text)
    if m:
        body, heads = conjunction(m["cond"]), conjunction(m["head"])
        if body is None or heads is None:
            raise ParseError(sentence)
        return [], [Rule(head, tuple(body)) for head in heads]
    general = universal(text)
    if general is not None:
        return [], [Rule(head, body) for body, head in general]
    literals = conjunction(text)
    if literals is None or not all(_is_ground(lit) for lit in literals):
        raise ParseError(sentence)
    return literals, []


def parse_context(text: str) -> KnowledgeBase:
    kb = KnowledgeBase()
    for sentence in split_sentences(text):
        try:
            facts, rules = parse_sentence(sentence)
        except ParseError:
            kb.unparsed.append(sentence)
            continue
        kb.facts.extend(facts)
        kb.rules.extend(rules)
    return kb


def parse_query(text: str) -> Literal:
    parsed = clause(clean(text))
    if parsed is None or isinstance(parsed[0], Var) or not _is_ground(parsed[1]):
        raise ParseError(text)
    return parsed[1]
