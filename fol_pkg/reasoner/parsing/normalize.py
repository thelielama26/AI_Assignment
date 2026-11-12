from __future__ import annotations

import re

LEADING_FUNCTION_WORDS = ("the", "if", "all", "someone", "something", "it", "they")


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def clean(sentence: str) -> str:
    sentence = re.sub(r"\s+", " ", sentence.strip()).rstrip(".!?").strip()
    first, _, rest = sentence.partition(" ")
    if first.lower() in LEADING_FUNCTION_WORDS:
        sentence = f"{first.lower()} {rest}".strip()
    return sentence


def lemma(verb: str) -> str:
    if verb.endswith("ies"):
        return verb[:-3] + "y"
    if re.search(r"(ss|sh|ch|x|z)es$", verb):
        return verb[:-2]
    if verb.endswith("s") and not verb.endswith("ss"):
        return verb[:-1]
    return verb
