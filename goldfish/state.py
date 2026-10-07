"""Board objects, run configuration and per-game statistics."""

from __future__ import annotations

from dataclasses import dataclass, field

from .cards import Card


@dataclass
class Stack:
    """A Digimon on the field: digivolution cards at the bottom, top card last."""

    cards: list[Card]
    suspended: bool = False
    # True once the Digimon has been in the battle area since the start of the
    # turn, or was moved from the breeding area this turn. Played Digimon start
    # False and need <Rush> to attack.
    can_attack_flag: bool = False
    rush: bool = False
    sa_turn_bonus: int = 0
    used: set[str] = field(default_factory=set)  # once-per-turn effect keys spent this turn

    @property
    def top(self) -> Card:
        return self.cards[-1]

    @property
    def level(self) -> int:
        return self.top.level or 0

    @property
    def sources(self) -> list[Card]:
        return self.cards[:-1]

    def has_source(self, card_id: str) -> bool:
        return any(c.id == card_id for c in self.sources)

    def can_attack(self) -> bool:
        return not self.suspended and (self.can_attack_flag or self.rush)

    def new_turn(self) -> None:
        self.suspended = False
        self.can_attack_flag = True
        self.rush = False
        self.sa_turn_bonus = 0
        self.used.clear()

    def __str__(self) -> str:
        return f"{self.top} lv{self.level}" + (" (susp)" if self.suspended else "")


@dataclass
class TamerInPlay:
    card: Card
    fuel: list[Card] = field(default_factory=list)  # face-down cards, index 0 is the bottom
    suspended: bool = False
    used: set[str] = field(default_factory=set)


@dataclass
class PlacedOption:
    """An Option card sitting in the battle area (e-Pulse, Glowing Dawn)."""

    card: Card
    placed_turn: int


@dataclass
class Config:
    # Never hand the opponent more memory than this. 3 means "no worse than passing".
    max_give: int = 3
    # A passing goldfish opponent leaves us this much memory each turn.
    start_memory: int = 3
    # The opponent is assumed to have a Digimon in its battle area from this
    # many of its own turns onward (drives "if your opponent has a Digimon").
    opp_board_turn: int = 2
    max_turns: int = 10
    # Optional effects that spend our own security are only used above this count.
    min_security: int = 2
    mulligan: bool = True


@dataclass
class GameStats:
    going_first: bool
    mulliganed: bool = False
    opening_hand: tuple[str, ...] = ()   # card ids after the mulligan decision
    turns_played: int = 0
    kill_turn: int | None = None
    deck_out_turn: int | None = None
    checks: int = 0                 # opponent security cards removed by our checks
    opp_trashed: int = 0            # opponent security cards trashed by effects
    checks_by_turn: list[int] = field(default_factory=list)   # cumulative, index 0 = turn 1
    memory_given: list[int] = field(default_factory=list)
    first_level_turn: dict[int, int] = field(default_factory=dict)
    first_tamer_turn: int | None = None
    kekkomon_tricks: int = 0
    arts_digivolves: int = 0
    free_digivolves: int = 0
    fuel_placed: int = 0
    fuel_spent: int = 0
    fuel_at_turn_start: int = 0
    fuel_at_first_lv6: int | None = None
    lv6_base_dual: bool | None = None    # did the first Lv6 land on a DUAL Lv5 (no inherited unsuspend)?
    library_at_end: int = 0
    security_at_end: int = 0
    # Board snapshots at the end of each turn (index 0 = turn 1).
    tamers_by_turn: list[int] = field(default_factory=list)
    fuel_by_turn: list[int] = field(default_factory=list)
    top_level_by_turn: list[int] = field(default_factory=list)   # highest level on the field

    @staticmethod
    def at_end_of(seq: list[int], turn: int) -> int | None:
        """Value at the end of `turn`, or the final value if the game ended earlier."""
        if not seq:
            return None
        return seq[min(turn, len(seq)) - 1]

    def checks_at_end_of(self, turn: int) -> int:
        """Cumulative checks at the end of `turn` (final total if the game ended earlier)."""
        if not self.checks_by_turn:
            return 0
        return self.checks_by_turn[min(turn, len(self.checks_by_turn)) - 1]
