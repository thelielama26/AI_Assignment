from __future__ import annotations

import re

from ..logic.scm import CausalProblem, Equation
from .parser import ParseError

CAUSE = re.compile(r"^(?P<cause>.+?) causes? (?P<effects>.+)$")
PRIOR = re.compile(r"^(?P<var>\w+)~\s*Bern\((?P<p>[\d.]+)\)\.?$")
OBSERVED = re.compile(r"^We observed (?P<what>.+?)\.?$")
WOULD = re.compile(r"^Would (?P<target>\w+) occur if (?P<given>.+?)(?: instead of \w+)?\?$")
NESTED = re.compile(
    r"^Assume (?P<first>.+?), and based on this assumption, further suppose (?P<second>.+?)\. "
    r"Would (?P<target>\w+) occur\?$"
)


def is_causal(context: str) -> bool:
    return context.lstrip().startswith("We know that")


def signed(text: str) -> tuple[str, bool]:
    text = text.strip()
    negated = text.startswith("not ")
    return text.removeprefix("not ").strip().lower(), negated


def _equations(sentence: str) -> list[Equation]:
    m = re.match(r"^We know that (?P<body>.+?)\.?$", sentence.strip())
    if not m:
        raise ParseError(sentence)
    equations: list[Equation] = []
    last: tuple[str, tuple] | None = None
    for segment in m["body"].split(", "):
        segment = re.sub(r"^and ", "", segment.strip())
        found = CAUSE.match(segment)
        if found:
            cause = found["cause"].replace(" together", "")
            op = "or" if " or " in cause else "and"
            last = (op, tuple(signed(p) for p in re.split(r" or | and ", cause)))
            effects = found["effects"]
        elif last is not None:
            effects = segment
        else:
            raise ParseError(sentence)
        for effect in re.split(r" and ", effects):
            name, negated = signed(effect)
            equations.append(Equation(name, negated, last[0], last[1]))
    return equations


def _observation(text: str) -> tuple[str, bool]:
    text = text.strip()
    if re.search(r"\s+not occurs?$", text):
        return signed(re.sub(r"\s+not occurs?$", "", text))[0], False
    name, negated = signed(re.sub(r"\s+occurs?$", "", text))
    return name, not negated


def _interventions(text: str) -> list[tuple[str, bool]]:
    result = []
    for part in re.split(r" and ", text):
        name, negated = signed(part)
        result.append((name, not negated))
    return result


def parse_problem(context: str, query: str) -> CausalProblem:
    sentences = re.split(r"(?<=\.)\s+", context.strip())
    equations = _equations(sentences[0])
    observations: dict[str, bool] = {}
    priors: dict[str, float] = {}
    for sentence in sentences[1:]:
        sentence = sentence.strip()
        if not sentence:
            continue
        prior = PRIOR.match(sentence)
        observed = OBSERVED.match(sentence)
        if prior:
            priors[prior["var"].lower()] = float(prior["p"])
        elif observed:
            for part in re.split(r" and ", observed["what"]):
                name, value = _observation(part)
                observations[name] = value
        else:
            raise ParseError(sentence)

    query = query.strip()
    nested = NESTED.match(query)
    if nested:
        interventions = _interventions(nested["first"]) + _interventions(nested["second"])
        target = nested["target"]
    else:
        would = WOULD.match(query)
        if not would:
            raise ParseError(query)
        interventions = _interventions(would["given"])
        target = would["target"]
    return CausalProblem(equations, interventions, target.lower(), observations, priors)
