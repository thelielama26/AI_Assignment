from __future__ import annotations

from dataclasses import dataclass, field

from .terms import Literal, Rule


@dataclass
class KnowledgeBase:
    facts: list[Literal] = field(default_factory=list)
    rules: list[Rule] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)

    def constants(self) -> tuple[str, ...]:
        found: dict[str, None] = {}
        literals = list(self.facts)
        for rule in self.rules:
            literals.append(rule.head)
            literals.extend(rule.body)
        for lit in literals:
            for arg in lit.atom.args:
                if isinstance(arg, str):
                    found[arg] = None
        return tuple(found)
