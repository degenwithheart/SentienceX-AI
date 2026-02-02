from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Tuple


@dataclass(frozen=True)
class NormalizeRule:
    pattern: re.Pattern[str]
    repl: str


def parse_rules(lines: Iterable[str]) -> List[NormalizeRule]:
    rules: List[NormalizeRule] = []
    for ln in lines:
        if "=>" not in ln:
            raise ValueError(f"Invalid normalize rule (missing '=>'): {ln!r}")
        left, right = ln.split("=>", 1)
        left = left.strip()
        right = right.strip()
        rules.append(NormalizeRule(pattern=re.compile(left), repl=right))
    return rules


class Normalizer:
    def __init__(self, rules: List[NormalizeRule]):
        self._rules = rules

    @staticmethod
    def from_rule_lines(lines: Iterable[str]) -> "Normalizer":
        return Normalizer(parse_rules(lines))

    def apply(self, text: str) -> str:
        out = text
        for rule in self._rules:
            out = rule.pattern.sub(rule.repl, out)
        return out.strip()


def normalize_basic(text: str) -> Tuple[str, str]:
    s = text.strip()
    return s, s.lower()

