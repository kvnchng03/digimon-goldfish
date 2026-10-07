"""Parse decklists in the plain "count name id" format and apply card edits."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

from .cards import CARDS, Card, Kind

# "4 Kekkomon   ST23-01", "2 Murasamemon BT26-031_P1", "4x e-Pulse ST23-15"
_LINE = re.compile(r"^\s*(\d+)\s*[x×]?\s+(.*?)\s+([A-Z]+\d*-\d+)(?:_P\d+)?\s*$")
_EDIT = re.compile(r"^\s*([A-Z]+\d*-\d+)\s*:\s*([+-]?\d+)\s*$")


@dataclass
class Deck:
    main: list[Card]
    eggs: list[Card]

    def counts(self) -> dict[str, int]:
        return dict(Counter(c.id for c in self.main + self.eggs))

    def describe(self) -> str:
        by_id = Counter(c.id for c in self.main + self.eggs)
        rows = sorted(by_id.items(), key=lambda kv: ((CARDS[kv[0]].level or 9), CARDS[kv[0]].kind.value, kv[0]))
        return "\n".join(f"{n} {CARDS[cid].name} {cid}" for cid, n in rows)


def validate(main: list[Card], eggs: list[Card]) -> None:
    if len(main) != 50:
        raise ValueError(f"main deck has {len(main)} cards, need exactly 50")
    if len(eggs) > 5:
        raise ValueError(f"egg deck has {len(eggs)} cards, max 5")
    for cid, n in Counter(c.id for c in main + eggs).items():
        if n > 4:
            raise ValueError(f"{n} copies of {cid}, max 4")


def parse_decklist(text: str) -> Deck:
    main: list[Card] = []
    eggs: list[Card] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _LINE.match(line)
        if not m:
            raise ValueError(f"can't parse decklist line: {raw!r}")
        n, name, cid = int(m.group(1)), m.group(2), m.group(3)
        card = CARDS.get(cid)
        if card is None:
            raise ValueError(f"unknown card {cid} ({name}); add it to cards.py")
        (eggs if card.kind is Kind.EGG else main).extend([card] * n)
    validate(main, eggs)
    return Deck(main, eggs)


def apply_edits(deck: Deck, spec: str) -> Deck:
    """Return a new deck with edits like "BT26-089:+1,ST23-15:-1" applied."""
    main, eggs = list(deck.main), list(deck.eggs)
    for part in spec.split(","):
        m = _EDIT.match(part)
        if not m:
            raise ValueError(f"bad edit {part!r}; expected ID:+N or ID:-N")
        cid, delta = m.group(1), int(m.group(2))
        card = CARDS.get(cid)
        if card is None:
            raise ValueError(f"unknown card {cid}; add it to cards.py")
        target = eggs if card.kind is Kind.EGG else main
        if delta >= 0:
            target.extend([card] * delta)
        else:
            for _ in range(-delta):
                idx = next((i for i, c in enumerate(target) if c.id == cid), None)
                if idx is None:
                    raise ValueError(f"can't remove {cid}: none left in the deck")
                del target[idx]
    validate(main, eggs)
    return Deck(main, eggs)
