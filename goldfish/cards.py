"""Card data for the Glowing Dawn (Digimon Beatbreak) card pool.

Only what the goldfish engine needs is encoded here; effects live in effects.py,
keyed by card id. Digivolve costs are the trait route ("Digivolve: X from Lv.N
w/ [Glowing Dawn] trait"), which is never dearer than the color route for any
card in this pool. Every card here carries both the [Glowing Dawn] and
[BEATBREAK] traits, so trait checks are implicit.

Sources: card text transcribed from the Digimon Card Game wiki (2026-10-06);
DUAL card and Arts Digivolve rules from Bandai's Comprehensive Rules (2026-09-18).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Kind(StrEnum):
    EGG = "egg"
    DIGIMON = "digimon"
    TAMER = "tamer"
    OPTION = "option"
    # Digimon information on top, Option information below. The card can be used
    # either way (Comprehensive Rules 4-6) and cannot be *played* as a Digimon.
    DUAL = "dual"


@dataclass(frozen=True)
class Card:
    id: str
    name: str
    kind: Kind
    level: int | None = None
    colors: tuple[str, ...] = ()
    play_cost: int | None = None    # None: cannot be played from hand (eggs, DUAL cards)
    option_cost: int | None = None  # cost to use the Option (half)
    evo_cost: int | None = None     # trait-route digivolve cost from one level below
    dp: int = 0
    sa_bonus: int = 0               # printed <Security Attack +X>
    alliance: bool = False          # printed <Alliance>

    @property
    def is_digimon(self) -> bool:
        return self.kind in (Kind.DIGIMON, Kind.DUAL)

    @property
    def is_option(self) -> bool:
        return self.kind in (Kind.OPTION, Kind.DUAL)

    @property
    def is_tamer(self) -> bool:
        return self.kind is Kind.TAMER

    @property
    def is_yellow(self) -> bool:
        return "yellow" in self.colors

    def __str__(self) -> str:
        return f"{self.name} ({self.id})"


_CARDS = [
    Card("ST23-01", "Kekkomon", Kind.EGG, level=2, colors=("green",)),
    # Lv3
    Card("ST23-06", "Gekkomon", Kind.DIGIMON, 3, ("green",), play_cost=3, evo_cost=0, dp=1000),
    Card("BT25-032", "Liollmon", Kind.DIGIMON, 3, ("yellow",), play_cost=3, evo_cost=0, dp=2000),
    Card("BT26-025", "Liollmon", Kind.DIGIMON, 3, ("yellow",), play_cost=3, evo_cost=0, dp=1000),
    Card("ST23-12", "Chiropmon", Kind.DIGIMON, 3, ("purple",), play_cost=3, evo_cost=0, dp=2000),
    # Lv4
    Card("ST23-03", "Cougarmon", Kind.DIGIMON, 4, ("yellow",), play_cost=4, evo_cost=2, dp=4000),
    Card("BT25-035", "Cougarmon", Kind.DIGIMON, 4, ("yellow",), play_cost=5, evo_cost=2, dp=6000),
    Card("BT26-026", "Cougarmon", Kind.DIGIMON, 4, ("yellow",), play_cost=4, evo_cost=2, dp=4000),
    Card("BT25-049", "Armalizamon", Kind.DIGIMON, 4, ("green",), play_cost=4, evo_cost=2, dp=4000),
    Card("BT26-070", "NightChiropmon", Kind.DIGIMON, 4, ("purple",), play_cost=5, evo_cost=2, dp=5000),
    # Lv5
    Card("ST23-04", "Murasamemon", Kind.DIGIMON, 5, ("yellow",), play_cost=7, evo_cost=3, dp=7000, alliance=True),
    Card("BT25-041", "Murasamemon", Kind.DIGIMON, 5, ("yellow",), play_cost=7, evo_cost=3, dp=7000, alliance=True),
    Card("BT26-031", "Murasamemon", Kind.DUAL, 5, ("yellow", "blue"), option_cost=4, evo_cost=3, dp=8000),
    Card("ST23-08", "Monarchlizamon", Kind.DIGIMON, 5, ("green",), play_cost=7, evo_cost=3, dp=7000, alliance=True),
    Card("BT25-057", "Monarchlizamon", Kind.DUAL, 5, ("green", "black"), option_cost=4, evo_cost=3, dp=8000),
    # Lv6
    Card("BT25-043", "Habakirimon", Kind.DUAL, 6, ("yellow",), option_cost=6, evo_cost=3, dp=12000),
    Card("ST23-09", "Atratusmon", Kind.DUAL, 6, ("green", "black"), option_cost=5, evo_cost=3, dp=12000, sa_bonus=1),
    # Tamers
    Card("ST23-13", "Tomoro Tenma & Kyo Sawashiro", Kind.TAMER, colors=("green", "yellow"), play_cost=4),
    Card("BT25-090", "Tomoro Tenma", Kind.TAMER, colors=("green",), play_cost=4),
    Card("BT26-089", "Kyo Sawashiro", Kind.TAMER, colors=("yellow",), play_cost=3),
    # Options
    Card("P-236", "Glowing Dawn", Kind.OPTION, colors=("green",), option_cost=3),
    Card("ST23-15", "e-Pulse", Kind.OPTION, colors=("white",), option_cost=3),
]

CARDS: dict[str, Card] = {c.id: c for c in _CARDS}

# Short ids used throughout effects.py and policy.py.
KEKKOMON = "ST23-01"
GEKKOMON = "ST23-06"
LIOLLMON_BT25 = "BT25-032"
LIOLLMON_BT26 = "BT26-025"
CHIROPMON = "ST23-12"
COUGARMON_ST23 = "ST23-03"
COUGARMON_BT25 = "BT25-035"
COUGARMON_BT26 = "BT26-026"
ARMALIZAMON = "BT25-049"
NIGHTCHIROPMON = "BT26-070"
MURASAMEMON_ST23 = "ST23-04"
MURASAMEMON_BT25 = "BT25-041"
MURASAMEMON_DUAL = "BT26-031"
MONARCHLIZAMON_ST23 = "ST23-08"
MONARCHLIZAMON_DUAL = "BT25-057"
HABAKIRIMON = "BT25-043"
ATRATUSMON = "ST23-09"
TOMORO_KYO = "ST23-13"
TOMORO = "BT25-090"
KYO = "BT26-089"
GLOWING_DAWN = "P-236"
EPULSE = "ST23-15"

# Lv5 cards whose *inherited* effect unsuspends the Digimon at end of attack.
# The DUAL Lv5s do not qualify: their lower text is Option information, not an
# inherited effect (Comprehensive Rules 2-3-11-5-1).
UNSUSPEND_SOURCES = frozenset({MURASAMEMON_ST23, MURASAMEMON_BT25, MONARCHLIZAMON_ST23})
