from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set


def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_lines(path: Path) -> List[str]:
    if not path.exists():
        raise FileNotFoundError(str(path))
    lines: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def _read_wordset(path: Path) -> Set[str]:
    return {ln.lower() for ln in _read_lines(path)}


@dataclass(frozen=True)
class Templates:
    normal: List[dict]
    empathy: List[dict]
    ack_short: List[dict]
    proactive: List[dict]
    safety: List[dict]

    @staticmethod
    def load(dir_path: Path) -> "Templates":
        def load_json(name: str) -> List[dict]:
            p = dir_path / name
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                raise ValueError(f"{p} must be a JSON list")
            return data

        return Templates(
            normal=load_json("normal.json"),
            empathy=load_json("empathy.json"),
            ack_short=load_json("ack_short.json"),
            proactive=load_json("proactive.json"),
            safety=load_json("safety.json"),
        )


@dataclass(frozen=True)
class Lexicons:
    sentiment_pos: Set[str]
    sentiment_neg: Set[str]
    threat: Set[str]
    sarcasm: Set[str]
    hedging: Set[str]
    minimizers: Set[str]
    masking_markers: Set[str]
    distress_topics: Set[str]

    def any_in(self, tokens: Iterable[str], lex: Set[str]) -> bool:
        tset = {t.lower() for t in tokens}
        return any(w in tset for w in lex)


@dataclass(frozen=True)
class LocalePack:
    name: str
    alphabet: Set[str]
    normalize_rules: List[str]
    abbreviations: Set[str]
    lexicons: Lexicons
    templates: Templates
    style_rules: Dict[str, object]

    @staticmethod
    def load(locale: str) -> "LocalePack":
        root = _project_root()
        base = root / "locale" / locale
        if not base.exists():
            raise FileNotFoundError(f"Locale not found: {locale} ({base})")

        alphabet = set("".join(_read_lines(base / "alphabet.txt")))
        normalize_rules = _read_lines(base / "normalize.rules")
        abbreviations = {a.strip() for a in _read_lines(base / "abbreviations.txt")}

        lex_dir = base / "lexicons"
        templates_dir = base / "templates"

        lex = Lexicons(
            sentiment_pos=_read_wordset(lex_dir / "sentiment_pos.txt"),
            sentiment_neg=_read_wordset(lex_dir / "sentiment_neg.txt"),
            threat=_read_wordset(lex_dir / "threat.txt"),
            sarcasm=_read_wordset(lex_dir / "sarcasm.txt"),
            hedging=_read_wordset(lex_dir / "hedging.txt"),
            minimizers=_read_wordset(lex_dir / "minimizers.txt"),
            masking_markers=_read_wordset(lex_dir / "masking_markers.txt"),
            distress_topics=_read_wordset(lex_dir / "distress_topics.txt"),
        )

        templates = Templates.load(templates_dir)
        style_rules = json.loads((base / "style_rules.json").read_text(encoding="utf-8"))

        return LocalePack(
            name=locale,
            alphabet=alphabet,
            normalize_rules=normalize_rules,
            abbreviations=abbreviations,
            lexicons=lex,
            templates=templates,
            style_rules=style_rules,
        )

