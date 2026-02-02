from __future__ import annotations

import argparse
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

_EMOJI_RE = re.compile(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]+", flags=re.UNICODE)
_SPACE_RE = re.compile(r"\s+")
_ROLE_PREFIX_RE = re.compile(r"^(User|Assistant):\s*", re.IGNORECASE)

_BAD_PHRASES = (
    "as an ai",
    "i am an ai",
    "i’m an ai",
    "i'm an ai",
    "language model",
    "system prompt",
    "token",
    "tokens",
    "training data",
    "template",
    "tool",
    "developer message",
)


def _project_root() -> Path:
    # sentiencex-ai/tools/micro_template_generator.py -> sentiencex-ai
    return Path(__file__).resolve().parents[1]


def _clean_text(text: str, *, allow_emojis: bool) -> str:
    s = _SPACE_RE.sub(" ", text.strip())
    if not allow_emojis:
        s = _EMOJI_RE.sub("", s).strip()
    low = s.lower()
    if any(p in low for p in _BAD_PHRASES):
        raise ValueError(f"Generated disallowed meta/self-reference: {s!r}")
    return s


def _ensure_max_sentences(text: str, max_sentences: int) -> str:
    if max_sentences <= 0:
        return ""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if not parts:
        return text.strip()
    return " ".join(parts[:max_sentences]).strip()


def _write_lines(path: Path, lines: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for ln in lines:
            s = ln.strip()
            if not s:
                continue
            f.write(s + "\n")


def _seeded_shuffle(rng: random.Random, xs: Sequence[str]) -> List[str]:
    out = list(xs)
    rng.shuffle(out)
    return out


def _unique_lines(rng: random.Random, producer, n: int, *, allow_emojis: bool, max_sentences: int) -> List[str]:
    seen = set()
    out: List[str] = []
    tries = 0
    target = int(n)
    while len(out) < target:
        tries += 1
        if tries > target * 70:
            break
        raw = producer()
        raw = _ensure_max_sentences(raw, max_sentences=max_sentences)
        raw = _clean_text(raw, allow_emojis=allow_emojis)
        if not raw:
            continue
        key = raw.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(raw)
    return out


@dataclass(frozen=True)
class GenSpec:
    micro: int
    short: int
    normal: int


class Generator:
    """
    Generates a comprehensive TRAIN/ library for SentienceX-AI learning.

    Guarantees:
    - Writes ONLY into TRAIN/
    - No system/meta language, no self-reference
    - No emojis EXCEPT TRAIN/style_samples/user.txt
    - Micro + short: max 1 sentence (enforced)
    - Acknowledgement turns contain no advice (raw_conversations assistant acks)
    """

    def __init__(self, seed: int):
        self.rng = random.Random(int(seed))

    def pick(self, xs: Sequence[str]) -> str:
        return self.rng.choice(list(xs))

    def chance(self, p: float) -> bool:
        return self.rng.random() < float(p)

    def join(self, *parts: str) -> str:
        return _SPACE_RE.sub(" ", " ".join(p for p in parts if p).strip())

    def punct(self, s: str) -> str:
        if not s:
            return s
        if s[-1] in ".!?":
            return s
        return s + self.pick([".", ".", ".", "?", "!"])

    def one_sentence(self, s: str) -> str:
        s = _ensure_max_sentences(s, 1)
        return self.punct(s)

    def up_to_two(self, s: str) -> str:
        s = _ensure_max_sentences(s, 2)
        if s and s[-1] not in ".!?":
            s = self.punct(s)
        return s


OPENERS = ["", "honestly", "to be honest", "lately", "these days", "well", "hmm"]
HEDGES = ["maybe", "probably", "kind of", "sort of", "i think", "i guess", "not sure"]
TIME_REFS = ["", "today", "recently", "lately", "these days", "this week"]
PEOPLE = ["my boss", "my partner", "my friend", "my coworker", "my family", "someone close to me"]


TOPICS_SPEC: Dict[str, dict] = {
    "anxiety": {
        "sensitivity": 0.55,
        "terms": [
            ("anxiety", 1.0),
            ("worry", 0.9),
            ("tension", 0.8),
            ("racing thoughts", 0.9),
            ("panic", 0.8),
            ("avoidance", 0.7),
            ("restless", 0.6),
            ("tight chest", 0.6),
            ("overthinking", 0.7),
            ("on edge", 0.6),
            ("uneasy", 0.5),
            ("can't relax", 0.6),
        ],
        "actions": [
            "Try a 60-second reset: name 5 things you see, 4 you feel, 3 you hear, 2 you smell, 1 you taste.",
            "Try writing the worry down and circle what you can control today.",
            "Try a small exposure step: one tiny action you can finish in 5 minutes.",
            "Try setting a decision timer so you don't loop for hours.",
            "Try labeling the thought as a thought, not a fact.",
        ],
    },
    "burnout": {
        "sensitivity": 0.45,
        "terms": [
            ("burnout", 1.0),
            ("exhausted", 0.9),
            ("drained", 0.9),
            ("numb", 0.7),
            ("detached", 0.6),
            ("overworked", 0.7),
            ("no energy", 0.8),
            ("can't focus", 0.6),
            ("sleep", 0.5),
            ("no motivation", 0.6),
            ("running on empty", 0.7),
            ("mentally foggy", 0.5),
        ],
        "actions": [
            "Try breaking the next hour into two 25-minute blocks and stop after each to check your body.",
            "Try choosing one task to drop or delay today, even if it's small.",
            "Try writing a two-line plan: must-do and nice-to-do.",
            "Try a hard stop time for tonight and protect it.",
            "Try asking for a smaller scope instead of pushing alone.",
        ],
    },
    "relationships": {
        "sensitivity": 0.40,
        "terms": [
            ("relationship", 1.0),
            ("partner", 0.7),
            ("communication", 0.7),
            ("argument", 0.7),
            ("distance", 0.6),
            ("misunderstood", 0.6),
            ("trust", 0.6),
            ("boundaries", 0.7),
            ("conflict", 0.6),
            ("repair", 0.5),
        ],
        "actions": [
            "Try drafting a one-sentence ask: what you want, without the backstory.",
            "Try reflecting their point first in one line before you respond.",
            "Try picking one moment to talk when neither of you is activated.",
            "Try naming the feeling, then the need: \"I feel __; I need __.\"",
            "Try pausing and returning when your voice is steady.",
        ],
    },
    "sleep": {
        "sensitivity": 0.35,
        "terms": [
            ("sleep", 1.0),
            ("insomnia", 0.9),
            ("tired", 0.8),
            ("wired", 0.6),
            ("restless", 0.6),
            ("night", 0.5),
            ("morning", 0.4),
            ("can't fall asleep", 0.8),
            ("can't stay asleep", 0.7),
            ("racing mind", 0.6),
        ],
        "actions": [
            "Try a 10-minute wind-down with the lights dim and your phone out of reach.",
            "Try writing down tomorrow's worries, then close the notebook.",
            "Try the same wake time for three days to stabilize it.",
            "Try a short body scan from toes to jaw.",
            "Try a gentle \"brain dump\" before bed to unload the loop.",
        ],
    },
}


class Supervised:
    def __init__(self, g: Generator):
        self.g = g

    # Intent (topic-agnostic)
    def intent_greeting(self) -> str:
        base = self.g.pick(["hey", "hi", "hello", "good morning", "good evening", "yo"])
        tail = self.g.pick(["", "there", "again", "how's it going", "what's up"])
        return self.g.one_sentence(self.g.join(base, tail))

    def intent_goodbye(self) -> str:
        base = self.g.pick(["bye", "talk later", "i'll be back", "gotta go", "see you", "i should run"])
        tail = self.g.pick(["", "thanks", "for now", "take care"])
        return self.g.one_sentence(self.g.join(base, tail))

    def intent_question(self) -> str:
        q = self.g.pick(
            [
                "can you help me think this through",
                "what would you do here",
                "how do i handle this",
                "what's a good next step",
                "does that make sense",
                "am i overthinking this",
                "what should i focus on first",
            ]
        )
        return self.g.one_sentence(q)

    def intent_task(self) -> str:
        base = self.g.pick(
            [
                "help me draft a message",
                "help me plan a checklist",
                "help me break this down",
                "help me decide between two options",
                "help me rewrite this to sound calmer",
            ]
        )
        return self.g.one_sentence(base)

    def intent_planning(self) -> str:
        base = self.g.pick(["i need a plan for tomorrow", "i want to map out my next steps", "i'm trying to organize my week", "i need to prioritize a few things"])
        return self.g.one_sentence(base)

    def intent_feedback(self) -> str:
        base = self.g.pick(["that helped", "that didn't land", "too much", "keep it short like that", "be more direct", "be gentler"])
        return self.g.one_sentence(base)

    def intent_venting(self) -> str:
        base = self.g.pick(
            [
                "i feel overwhelmed",
                "i'm frustrated and tired",
                "i don't know how much more i can hold",
                "this has been weighing on me",
                "i'm stressed and it shows",
                "i feel alone in this",
            ]
        )
        return self.g.one_sentence(base)

    # Sentiment (topic-agnostic)
    def sentiment_pos(self) -> str:
        base = self.g.pick(["i feel good", "i feel better", "i feel okay", "i'm relieved", "i feel calmer", "that went well"])
        tail = self.g.pick(["", "today", "this week", "right now"])
        return self.g.one_sentence(self.g.join(base, tail))

    def sentiment_neu(self) -> str:
        base = self.g.pick(["i'm not sure how i feel", "i'm fine i guess", "it's been a day", "i don't know", "i'm here", "i'm listening"])
        return self.g.one_sentence(base)

    def sentiment_neg(self) -> str:
        base = self.g.pick(["i feel bad", "i feel down", "i'm anxious", "i'm stressed", "i feel lonely", "i feel stuck", "this hurts"])
        tail = self.g.pick(["", "today", "lately", "right now"])
        return self.g.one_sentence(self.g.join(base, tail))

    # Sarcasm (topic-agnostic)
    def sarcasm_sarcastic(self) -> str:
        base = self.g.pick(["yeah right", "sure", "totally", "great", "love that", "perfect"])
        tail = self.g.pick(["", "as if", "of course", "just what i needed"])
        s = self.g.join(base, tail)
        if self.g.chance(0.55) and not s.endswith("."):
            s = s + "."
        return self.g.one_sentence(s)

    def sarcasm_not(self) -> str:
        base = self.g.pick(["i mean that", "i'm serious", "no sarcasm", "i'm being honest", "i'm not joking"])
        return self.g.one_sentence(base)

    # Threat / Self-harm (no method details)
    def threat_none(self) -> str:
        base = self.g.pick(
            [
                "i'm upset but i won't hurt anyone",
                "i don't want to harm anyone",
                "i'm angry but i'm staying in control",
                "i can cool down without doing anything reckless",
                "i'm safe right now",
            ]
        )
        return self.g.one_sentence(base)

    def threat_threat(self) -> str:
        base = self.g.pick(
            [
                "i want to hurt someone",
                "i feel like lashing out at someone",
                "i want to make them pay",
                "i want to get back at them",
                "i feel like i could snap at someone",
            ]
        )
        tail = self.g.pick(["", "right now", "for what they did", "and i hate that i feel this way"])
        return self.g.one_sentence(self.g.join(base, tail))

    def threat_self_harm(self) -> str:
        base = self.g.pick(
            [
                "i don't want to be alive",
                "i feel like i can't go on",
                "i want everything to stop",
                "i feel trapped in my life",
                "i keep thinking about hurting myself",
            ]
        )
        tail = self.g.pick(["", "right now", "and it scares me", "and i don't know what to do"])
        return self.g.one_sentence(self.g.join(base, tail))


class TopicsFactory:
    def __init__(self, g: Generator):
        self.g = g

    def topic_doc(self, topic: str) -> List[str]:
        spec = TOPICS_SPEC[topic]
        lines = [f"# topic={topic}", f"# sensitivity={spec['sensitivity']}"]
        for term, w in spec["terms"]:
            lines.append(f"{term}|{w}")
        return lines


class SkillsFactory:
    def __init__(self, g: Generator):
        self.g = g

    def skill_doc(self, topic: str) -> List[str]:
        acts = TOPICS_SPEC[topic]["actions"]
        header = [f"# topic={topic}", "# short, practical actions"]
        bullets: List[str] = []
        for a in _seeded_shuffle(self.g.rng, acts):
            if self.g.chance(0.35):
                bullets.append("Consider " + a[0].lower() + a[1:])
            else:
                bullets.append(a)
        return header + [f"- {b}" for b in bullets]


class StoryFactory:
    def __init__(self, g: Generator):
        self.g = g

    def story_doc(self, topic: str) -> List[str]:
        person = self.g.pick(["They", "He", "She"])
        who = self.g.pick(["at work", "around friends", "with family", "in public", "in meetings"])
        private = self.g.pick(["at night", "alone", "when the room was quiet", "when nobody was watching"])
        feelings = self.g.pick(["tight", "heavy", "numb", "on edge", "exhausted"])
        lines: List[str] = []
        lines.append(f"{person} kept saying everything was fine.")
        lines.append(f"{person} smiled {who} and kept the tone light.")
        lines.append(f"{person} felt {feelings} {private}.")
        lines.append(f"{person} kept thinking about {topic}.")
        if self.g.chance(0.6):
            lines.append(f"{person} laughed it off and changed the subject.")
        lines.append(f"{person} started replying less and less.")
        lines.append(f"{person} told themselves it was {self.g.pick(['temporary', 'not a big deal', 'manageable'])}.")
        lines.append(f"{person} felt stuck between pushing through and falling apart.")
        if self.g.chance(0.5):
            lines.append(f"{person} avoided messages because it felt easier than explaining.")
        lines.append("Eventually, the weight showed up in small ways.")
        lines.append(f"{person} wished someone would notice without making it a big scene.")
        return lines


class RawConversationFactory:
    def __init__(self, g: Generator):
        self.g = g
        self.sup = Supervised(g)

    def _assistant_ack(self) -> str:
        # No advice in acknowledgement-only turns.
        return self.g.one_sentence(self.g.pick(["Mm. I'm here.", "Okay. I'm listening.", "I hear you.", "I'm with you."]))

    def _assistant_empathy(self) -> str:
        return self.g.one_sentence(
            self.g.pick(
                [
                    "That sounds heavy.",
                    "That’s a lot to carry.",
                    "I can see why that would hurt.",
                    "That would wear anyone down.",
                ]
            )
        )

    def _assistant_question(self) -> str:
        return self.g.one_sentence(
            self.g.pick(
                [
                    "What part feels hardest right now?",
                    "Do you want to vent, or do you want a next step?",
                    "What’s the piece you can’t stop thinking about?",
                    "What would make tonight feel a little safer or easier?",
                ]
            )
        )

    def conversation(self, topic: str) -> List[str]:
        opener = self.g.pick(
            [
                f"I've been thinking about {topic} a lot.",
                f"{topic} has been getting to me.",
                f"I feel stuck with {topic}.",
                f"Honestly, {topic} is wearing me down.",
            ]
        )
        user1 = self.g.one_sentence(opener)
        user2 = self.g.one_sentence(self.g.join(self.g.pick(HEDGES), "it's mostly because of", self.g.pick(PEOPLE), self.g.pick(TIME_REFS)))
        user3 = self.g.one_sentence(self.g.pick([self.sup.intent_venting(), self.sup.sentiment_neg(), self.sup.sentiment_neu()]))

        return [
            f"User: {user1}",
            f"Assistant: {self._assistant_empathy()}",
            f"User: {user2}",
            f"Assistant: {self._assistant_question()}",
            f"User: {user3}",
            f"Assistant: {self._assistant_ack()}",
        ]


class StyleSamplesFactory:
    def __init__(self, g: Generator):
        self.g = g

    def user_lines(self, n: int) -> List[str]:
        mood = [
            "i'm tired today",
            "i keep overthinking",
            "i'm okay i guess",
            "not sure what i need",
            "i'm frustrated",
            "i'm trying",
            "i feel calmer now",
            "today felt weird",
            "i don't have words for it",
        ]
        emoji = ["", "", "", " 🙂", " 😅", " 😔"]
        out: List[str] = []
        for _ in range(int(n)):
            s = self.g.join(self.g.pick(OPENERS), self.g.pick(mood), self.g.pick(TIME_REFS)).strip()
            if self.g.chance(0.22):
                s += self.g.pick(emoji)
            s = _ensure_max_sentences(s, 1)
            s = _clean_text(s, allow_emojis=True)
            out.append(s)
        return out


def _gen_supervised_files(g: Generator, train_dir: Path, spec: GenSpec) -> List[Path]:
    sup = Supervised(g)
    written: List[Path] = []

    intent = {
        "greeting": sup.intent_greeting,
        "goodbye": sup.intent_goodbye,
        "question": sup.intent_question,
        "task": sup.intent_task,
        "planning": sup.intent_planning,
        "feedback": sup.intent_feedback,
        "venting": sup.intent_venting,
    }
    sentiment = {"pos": sup.sentiment_pos, "neu": sup.sentiment_neu, "neg": sup.sentiment_neg}
    sarcasm = {"sarcastic": sup.sarcasm_sarcastic, "not_sarcastic": sup.sarcasm_not}
    threat = {"none": sup.threat_none, "threat": sup.threat_threat, "self_harm": sup.threat_self_harm}

    def write_category(cat: str, labels: Dict[str, object]) -> None:
        nonlocal written
        for brev, count in (("micro", spec.micro), ("short", spec.short), ("normal", spec.normal)):
            for label, fn in labels.items():
                path = train_dir / cat / brev / f"{label}.txt"
                max_sents = 1 if brev in {"micro", "short"} else 2
                lines = _unique_lines(g.rng, fn, int(count), allow_emojis=False, max_sentences=max_sents)
                _write_lines(path, lines)
                written.append(path)

    write_category("intent", intent)
    write_category("sentiment", sentiment)
    write_category("sarcasm", sarcasm)
    write_category("threat", threat)
    return written


def _gen_topic_specific(g: Generator, train_dir: Path, *, story_docs_per_topic: int, convs_per_topic: int, style_lines: int) -> List[Path]:
    written: List[Path] = []
    stories = StoryFactory(g)
    skills = SkillsFactory(g)
    topics = TopicsFactory(g)
    convs = RawConversationFactory(g)
    style = StyleSamplesFactory(g)

    for topic in TOPICS_SPEC.keys():
        p = train_dir / "topics" / f"{topic}.txt"
        lines = [_clean_text(ln, allow_emojis=False) for ln in topics.topic_doc(topic)]
        _write_lines(p, lines)
        written.append(p)

    for topic in TOPICS_SPEC.keys():
        p = train_dir / "skills" / f"{topic}.txt"
        lines = [_clean_text(ln, allow_emojis=False) for ln in skills.skill_doc(topic)]
        _write_lines(p, lines)
        written.append(p)

    for topic in TOPICS_SPEC.keys():
        for i in range(int(story_docs_per_topic)):
            p = train_dir / "stories" / topic / f"story_{i:03d}.txt"
            lines = [_clean_text(ln, allow_emojis=False) for ln in stories.story_doc(topic)]
            _write_lines(p, lines)
            written.append(p)

    for topic in TOPICS_SPEC.keys():
        for i in range(int(convs_per_topic)):
            p = train_dir / "raw_conversations" / topic / f"conv_{i:03d}.txt"
            conv_lines: List[str] = []
            for ln in convs.conversation(topic):
                m = _ROLE_PREFIX_RE.match(ln)
                if m:
                    prefix = m.group(1).capitalize()
                    rest = ln[m.end() :].strip()
                    rest = _ensure_max_sentences(rest, 1)
                    rest = _clean_text(rest, allow_emojis=False)
                    conv_lines.append(f"{prefix}: {rest}")
                else:
                    conv_lines.append(_clean_text(ln, allow_emojis=False))
            _write_lines(p, conv_lines)
            written.append(p)

    p = train_dir / "style_samples" / "user.txt"
    _write_lines(p, style.user_lines(int(style_lines)))
    written.append(p)

    return written


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate extensive TRAIN/ corpora for SentienceX-AI learning.")
    ap.add_argument("--seed", type=int, default=7, help="Random seed for reproducible generation.")
    ap.add_argument("--train-dir", type=str, default=None, help="Output TRAIN directory (default: <repo>/TRAIN).")
    ap.add_argument(
        "--target-lines-per-category",
        type=int,
        default=900,
        help="Approx total lines per supervised category (intent/sentiment/sarcasm/threat). Set 0 to use explicit per-file counts.",
    )
    ap.add_argument("--lines-micro", type=int, default=50, help="Lines per label file for micro brevity (used when target-lines-per-category=0).")
    ap.add_argument("--lines-short", type=int, default=50, help="Lines per label file for short brevity (used when target-lines-per-category=0).")
    ap.add_argument("--lines-normal", type=int, default=40, help="Lines per label file for normal brevity (used when target-lines-per-category=0).")
    ap.add_argument("--story-docs-per-topic", type=int, default=25, help="Story documents per topic.")
    ap.add_argument("--convs-per-topic", type=int, default=35, help="Raw conversations per topic.")
    ap.add_argument("--style-lines", type=int, default=500, help="Lines for TRAIN/style_samples/user.txt.")
    args = ap.parse_args()

    root = _project_root()
    train_dir = Path(args.train_dir) if args.train_dir else (root / "TRAIN")
    train_dir.mkdir(parents=True, exist_ok=True)

    g = Generator(seed=int(args.seed))
    spec = GenSpec(micro=int(args.lines_micro), short=int(args.lines_short), normal=int(args.lines_normal))

    written: List[Path] = []
    # Supervised categories are topic-agnostic. Prefer a category-level budget.
    target = int(args.target_lines_per_category)
    if target > 0:
        written += _gen_supervised_files_with_target(g, train_dir, target_lines=target)
    else:
        written += _gen_supervised_files(g, train_dir, spec)
    written += _gen_topic_specific(
        g,
        train_dir,
        story_docs_per_topic=int(args.story_docs_per_topic),
        convs_per_topic=int(args.convs_per_topic),
        style_lines=int(args.style_lines),
    )

    print(f"Wrote {len(written)} files under {train_dir}")
    return 0


def _alloc_counts(target_lines: int, label_count: int) -> GenSpec:
    # Weighted split matching brevity tiers while keeping micro/short single-sentence.
    # Ensures "about 600–1,200 total lines per category" when target_lines is in that range.
    lc = max(1, int(label_count))
    target = max(0, int(target_lines))
    micro = max(12, round((target * 0.40) / lc))
    short = max(12, round((target * 0.35) / lc))
    normal = max(10, round((target * 0.25) / lc))
    return GenSpec(micro=int(micro), short=int(short), normal=int(normal))


def _gen_supervised_files_with_target(g: Generator, train_dir: Path, *, target_lines: int) -> List[Path]:
    sup = Supervised(g)
    written: List[Path] = []

    intent = {
        "greeting": sup.intent_greeting,
        "goodbye": sup.intent_goodbye,
        "question": sup.intent_question,
        "task": sup.intent_task,
        "planning": sup.intent_planning,
        "feedback": sup.intent_feedback,
        "venting": sup.intent_venting,
    }
    sentiment = {"pos": sup.sentiment_pos, "neu": sup.sentiment_neu, "neg": sup.sentiment_neg}
    sarcasm = {"sarcastic": sup.sarcasm_sarcastic, "not_sarcastic": sup.sarcasm_not}
    threat = {"none": sup.threat_none, "threat": sup.threat_threat, "self_harm": sup.threat_self_harm}

    def write_category(cat: str, labels: Dict[str, object]) -> None:
        nonlocal written
        spec = _alloc_counts(target_lines, label_count=len(labels))
        for brev, count in (("micro", spec.micro), ("short", spec.short), ("normal", spec.normal)):
            for label, fn in labels.items():
                path = train_dir / cat / brev / f"{label}.txt"
                max_sents = 1 if brev in {"micro", "short"} else 2
                lines = _unique_lines(g.rng, fn, int(count), allow_emojis=False, max_sentences=max_sents)
                _write_lines(path, lines)
                written.append(path)

    write_category("intent", intent)
    write_category("sentiment", sentiment)
    write_category("sarcasm", sarcasm)
    write_category("threat", threat)
    return written


if __name__ == "__main__":
    raise SystemExit(main())
