"""Rules engine for a solo (goldfish) game of the Digimon Card Game.

The engine enforces zones, costs, triggers and the turn structure. It never
chooses: every decision is delegated to the Policy object so the heuristics
stay readable and arguable in one place (policy.py).

Opponent model: a goldfish. It never plays cards, never attacks and never
blocks. It is assumed to have a Digimon in its battle area from its
`Config.opp_board_turn`-th turn onward (for "if your opponent has a Digimon"
checks) and to pass every turn, which sets our memory to `Config.start_memory`.
Its 5 security cards are only ever removed by our checks and by our effects.
Card effects that only touch the opponent's board are therefore no-ops here.
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from . import effects
from .cards import ARMALIZAMON, COUGARMON_ST23, KYO, TOMORO, Card, Kind
from .decklist import Deck
from .state import Config, GameStats, PlacedOption, Stack, TamerInPlay

if TYPE_CHECKING:
    from .policy import Policy


class GameOver(Exception):
    """Raised when the game ends mid-action (lethal or deck-out)."""


class Game:
    def __init__(self, deck: Deck, policy: Policy, rng: random.Random, going_first: bool,
                 cfg: Config | None = None, trace: bool = False) -> None:
        self.cfg = cfg or Config()
        self.policy = policy
        self.rng = rng
        self.deck: list[Card] = list(deck.main)   # index -1 is the top card
        self.eggs: list[Card] = list(deck.eggs)
        rng.shuffle(self.deck)
        rng.shuffle(self.eggs)
        self.hand: list[Card] = []
        self.security: list[Card] = []            # index -1 is the top card
        self.trash: list[Card] = []
        self.breeding: Stack | None = None
        self.battle: list[Stack] = []
        self.tamers: list[TamerInPlay] = []
        self.placed: list[PlacedOption] = []      # Option cards sitting in the battle area
        self.memory = 0
        self.turn = 0
        self.going_first = going_first
        self.opp_security = 5
        self.over = False
        self.attacking: Stack | None = None       # the Digimon whose attack is being resolved
        # Lowest memory the policy is currently willing to end up at. The hard
        # rule (never below -max_give) is enforced separately by can_pay().
        self.floor = -self.cfg.max_give
        self.stats = GameStats(going_first=going_first)
        self.trace = trace
        self.log: list[str] = []

    # ------------------------------------------------------------------ logging
    def say(self, msg: str) -> None:
        if self.trace:
            self.log.append(
                f"T{self.turn:<2} mem {self.memory:+d}  fuel {self.total_fuel()}  "
                f"sec {len(self.security)}/{self.opp_security}  hand {len(self.hand)} | {msg}")

    # ------------------------------------------------------------------ game loop
    def play(self) -> GameStats:
        self.setup()
        try:
            while not self.over and self.turn < self.cfg.max_turns:
                self.take_turn()
        except GameOver:
            pass
        self.stats.turns_played = self.turn
        self.stats.library_at_end = len(self.deck)
        self.stats.security_at_end = len(self.security)
        # A game that ended mid-turn has not recorded that turn yet.
        while len(self.stats.checks_by_turn) < self.turn:
            self.stats.checks_by_turn.append(self.stats.checks)
            self.snapshot()
        return self.stats

    def snapshot(self) -> None:
        """Record the board at the end of a turn."""
        s = self.stats
        s.tamers_by_turn.append(len(self.tamers))
        s.fuel_by_turn.append(self.total_fuel())
        s.top_level_by_turn.append(max((st.level for st in self.stacks_on_field()), default=0))

    def setup(self) -> None:
        self.draw(5)
        if self.cfg.mulligan and self.policy.should_mulligan(self, self.hand):
            self.deck.extend(self.hand)
            self.hand.clear()
            self.rng.shuffle(self.deck)
            self.draw(5)
            self.stats.mulliganed = True
        for _ in range(5):
            self.security.append(self.deck.pop())
        self.stats.opening_hand = tuple(c.id for c in self.hand)
        self.say("opening hand: " + ", ".join(str(c) for c in self.hand))

    def take_turn(self) -> None:
        self.turn += 1
        for st in self.stacks_on_field():
            st.new_turn()
        for t in self.tamers:
            t.suspended = False
            t.used.clear()
        self.memory = 0 if (self.turn == 1 and self.going_first) else self.cfg.start_memory
        # Tomoro Tenma [Start of Your Turn]: if you have 2 or less memory, set it to 3.
        if self.memory <= 2 and any(t.card.id == TOMORO for t in self.tamers):
            self.memory = 3
        self.stats.fuel_at_turn_start = self.total_fuel()
        self.floor = -self.cfg.max_give
        self.say(f"--- turn {self.turn} ({'first' if self.going_first else 'second'}) ---")
        if not (self.turn == 1 and self.going_first):
            self.draw(1)
        self.policy.breeding_phase(self)
        effects.start_of_main(self)
        self.policy.main_phase(self)
        self.stats.memory_given.append(-self.memory if self.memory < 0 else 3)
        self.stats.checks_by_turn.append(self.stats.checks)
        self.snapshot()

    # ------------------------------------------------------------------ zones
    def draw(self, n: int = 1) -> None:
        for _ in range(n):
            if not self.deck:
                self.stats.deck_out_turn = self.turn
                self.over = True
                self.say("DECK OUT")
                raise GameOver
            self.hand.append(self.deck.pop())

    def reveal(self, n: int) -> list[Card]:
        seen = [self.deck.pop() for _ in range(min(n, len(self.deck)))]
        self.say("reveal: " + ", ".join(str(c) for c in seen))
        return seen

    def to_bottom(self, cards: list[Card]) -> None:
        for c in cards:
            self.deck.insert(0, c)

    def total_fuel(self) -> int:
        return sum(len(t.fuel) for t in self.tamers)

    def place_fuel(self, card: Card, tamer: TamerInPlay | None = None) -> None:
        tamer = tamer or self.policy.choose_fuel_tamer(self)
        tamer.fuel.append(card)
        self.stats.fuel_placed += 1

    def place_fuel_from_deck(self, tamer: TamerInPlay, n: int = 1) -> None:
        for _ in range(n):
            if self.deck:
                self.place_fuel(self.deck.pop(), tamer)

    def trash_fuel(self, n: int = 1) -> bool:
        """Trash n bottom face-down cards from under our Tamers. False if we can't."""
        if self.total_fuel() < n:
            return False
        for _ in range(n):
            tamer = max(self.tamers, key=lambda t: len(t.fuel))
            self.trash.append(tamer.fuel.pop(0))
        self.stats.fuel_spent += n
        return True

    # ------------------------------------------------------------------ security
    def on_security_removed(self) -> None:
        # Kyo Sawashiro [All Turns]: when your security stack is removed from,
        # by suspending this Tamer, place the top card of your deck under it.
        for t in self.tamers:
            if t.card.id == KYO and not t.suspended:
                t.suspended = True
                self.place_fuel_from_deck(t, 1)

    def security_to_hand(self) -> bool:
        if not self.security:
            return False
        self.hand.append(self.security.pop())
        self.on_security_removed()
        return True

    def security_to_fuel(self) -> bool:
        if not self.security or not self.tamers:
            return False
        self.place_fuel(self.security.pop())
        self.on_security_removed()
        return True

    def trash_security(self) -> bool:
        if not self.security:
            return False
        self.trash.append(self.security.pop())
        self.on_security_removed()
        return True

    def recovery(self, n: int = 1) -> None:
        for _ in range(n):
            if self.deck:
                self.security.append(self.deck.pop())

    def trash_opp_security(self) -> None:
        if self.opp_security > 0:
            self.opp_security -= 1
            self.stats.opp_trashed += 1

    # ------------------------------------------------------------------ memory
    def can_pay(self, cost: int, floor: int | None = None) -> bool:
        floor = -self.cfg.max_give if floor is None else max(floor, -self.cfg.max_give)
        return self.memory - cost >= floor

    def pay(self, cost: int) -> None:
        self.memory -= cost

    def gain(self, n: int) -> None:
        self.memory += n

    # ------------------------------------------------------------------ board queries
    def stacks_on_field(self) -> list[Stack]:
        return self.battle + ([self.breeding] if self.breeding else [])

    def opp_has_digimon(self) -> bool:
        opp_turns_so_far = self.turn - 1 if self.going_first else self.turn
        return opp_turns_so_far >= self.cfg.opp_board_turn

    def has_use_req(self) -> bool:
        """Use Req. [Glowing Dawn]/[BEATBREAK]: any of our cards in play carries the trait."""
        return bool(self.tamers or self.battle or self.breeding)

    def on_any_suspend(self) -> None:
        # Tomoro Tenma [All Turns]: when any Digimon suspend, by suspending this
        # Tamer, place the top 2 cards of your deck face down under it.
        for t in self.tamers:
            if t.card.id == TOMORO and not t.suspended:
                t.suspended = True
                self.place_fuel_from_deck(t, 2)

    def note_level(self, level: int | None, st: Stack | None = None) -> None:
        if level is None:
            return
        if level not in self.stats.first_level_turn:
            self.stats.first_level_turn[level] = self.turn
            if level == 6:
                self.stats.fuel_at_first_lv6 = self.stats.fuel_at_turn_start
                if st is not None and len(st.cards) >= 2:
                    self.stats.lv6_base_dual = st.cards[-2].kind is Kind.DUAL

    # ------------------------------------------------------------------ actions
    def hatch(self) -> None:
        egg = self.eggs.pop()
        self.breeding = Stack([egg])
        self.say(f"hatch {egg}")

    def move_from_breeding(self) -> None:
        st = self.breeding
        assert st is not None and st.level >= 3
        self.breeding = None
        st.can_attack_flag = True
        self.battle.append(st)
        self.say(f"move {st} to battle area")
        effects.when_moving(self, st)

    def play_card(self, card: Card, source: list[Card], free: bool = False, cost: int | None = None) -> None:
        """Play a Digimon or Tamer from `source` (hand or trash)."""
        source.remove(card)
        if not free:
            self.pay(card.play_cost if cost is None else cost)
        if card.is_tamer:
            t = TamerInPlay(card)
            self.tamers.append(t)
            if self.stats.first_tamer_turn is None:
                self.stats.first_tamer_turn = self.turn
            self.say(f"play {card}" + (" (free)" if free else ""))
            effects.on_play_tamer(self, t)
        else:
            st = Stack([card])
            self.battle.append(st)
            self.note_level(card.level)
            self.say(f"play {card}" + (" (free)" if free else ""))
            effects.on_play(self, st)

    def digivolve_plan(self, st: Stack, card: Card, trick: bool = False) -> tuple[int, int] | None:
        """(memory, fuel) to digivolve `st` into `card` via the trait route, or None if illegal.

        `trick` is Kekkomon's inherited effect (-2 for 1 fuel, at attack time).
        Cougarmon ST23-03's own -2 for 1 fuel is added whenever it helps.
        """
        if not card.is_digimon or card.level != st.level + 1 or card.evo_cost is None:
            return None
        cost, fuel = card.evo_cost, 0
        if trick:
            cost -= 2
            fuel += 1
        if st.top.id == COUGARMON_ST23 and cost > 0 and self.total_fuel() - fuel >= 1:
            cost -= 2
            fuel += 1
        if fuel > self.total_fuel():
            return None
        return max(cost, 0), fuel

    def digivolve(self, st: Stack, card: Card, cost: int, fuel: int = 0, source: list[Card] | None = None) -> None:
        (self.hand if source is None else source).remove(card)
        self.pay(cost)
        if fuel:
            self.trash_fuel(fuel)
        st.cards.append(card)
        self.note_level(card.level, st)
        self.say(f"digivolve {st.cards[-2]} -> {card} for {cost}" + (f" (+{fuel} fuel)" if fuel else ""))
        self.draw(1)  # digivolution bonus
        effects.when_digivolving(self, st)

    def arts_digivolve(self, st: Stack, card: Card) -> None:
        """Comprehensive Rules 4-20: after using a DUAL card's Option, a card on the
        field may digivolve into it without paying the cost instead of trashing it."""
        st.cards.append(card)
        self.note_level(card.level, st)
        self.stats.arts_digivolves += 1
        self.say(f"Arts Digivolve {st.cards[-2]} -> {card} (free)")
        self.draw(1)
        effects.when_digivolving(self, st)

    def option_reducers(self) -> list[tuple[str, int, Stack | TamerInPlay]]:
        """Cost reducers for Glowing Dawn Options available right now, 1 fuel each."""
        out: list[tuple[str, int, Stack | TamerInPlay]] = []
        for st in self.battle:
            # Armalizamon [Your Turn][Once Per Turn]: -3 (only while it is the top card)
            if st.top.id == ARMALIZAMON and "armaliza" not in st.used:
                out.append(("armaliza", 3, st))
        for t in self.tamers:
            # Tomoro Tenma [Your Turn][Once Per Turn]: -1
            if t.card.id == TOMORO and "tomoro_opt" not in t.used:
                out.append(("tomoro_opt", 1, t))
        return out

    def option_plan(self, card: Card, discount: int = 0) -> tuple[int, int, list[tuple[str, int, Stack | TamerInPlay]]]:
        """(memory, fuel, reducers) to use `card` as an Option right now."""
        assert card.option_cost is not None
        cost, fuel, use = card.option_cost - discount, 0, []
        for red in sorted(self.option_reducers(), key=lambda r: -r[1]):
            if cost <= 0 or self.total_fuel() - fuel < 1:
                break
            cost -= red[1]
            fuel += 1
            use.append(red)
        return max(cost, 0), fuel, use

    def use_option(self, card: Card, source: list[Card], discount: int = 0,
                   during_attack: Stack | None = None, arts_target: Stack | None = None) -> None:
        cost, fuel, reducers = self.option_plan(card, discount)
        source.remove(card)
        self.pay(cost)
        for key, _amount, holder in reducers:
            holder.used.add(key)
        if fuel:
            self.trash_fuel(fuel)
        self.say(f"use {card} as Option for {cost}" + (f" (+{fuel} fuel)" if fuel else ""))
        effects.resolve_option(self, card, during_attack, arts_target)

    def attack(self, st: Stack) -> None:
        if self.opp_security == 0:
            self.stats.kill_turn = self.turn
            self.over = True
            self.say(f"{st} attacks with the opponent at 0 security: LETHAL")
            raise GameOver
        st.suspended = True
        self.attacking = st
        try:
            self.on_any_suspend()
            self.say(f"{st.top} (lv{st.level}) attacks")
            effects.when_attacking(self, st)
            sa = 1 + st.top.sa_bonus + st.sa_turn_bonus
            if st.top.alliance:
                ally = self.policy.choose_alliance(self, st)
                if ally is not None:
                    ally.suspended = True
                    self.on_any_suspend()
                    sa += 1
                    self.say(f"  Alliance with {ally}")
            hits = min(sa, self.opp_security)
            self.opp_security -= hits
            self.stats.checks += hits
            self.say(f"  {hits} security check(s); opponent at {self.opp_security}")
            effects.end_of_attack(self, st)
        finally:
            self.attacking = None

    # ------------------------------------------------------------------ invariants
    def all_cards(self) -> list[Card]:
        cards = self.deck + self.hand + self.security + self.trash + self.eggs
        for st in self.stacks_on_field():
            cards += st.cards
        for t in self.tamers:
            cards += [t.card] + t.fuel
        cards += [p.card for p in self.placed]
        return cards
