"""Decision heuristics for the goldfish engine.

Everything here is a judgement call, kept in one place so it can be read and
argued with. The engine (engine.py) enforces the rules; this file decides what
to do within them. The goal is kill speed (security checks dealt per turn)
under one constraint: never hand the opponent more memory than Config.max_give.

Turn shape:
  1. breeding phase: hatch, or move a Lv4+ (or a Lv3 once a Tamer is out),
  2. setup that keeps memory at 0 or more (Tamers, e-Pulse, cheap digivolves),
  3. attacks, highest level first, letting Kekkomon's attack-time digivolve do
     the expensive work,
  4. spend what is left, down to -max_give, to set up next turn.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .cards import (
    ARMALIZAMON,
    ATRATUSMON,
    CHIROPMON,
    COUGARMON_BT25,
    COUGARMON_BT26,
    COUGARMON_ST23,
    EPULSE,
    GEKKOMON,
    GLOWING_DAWN,
    HABAKIRIMON,
    KEKKOMON,
    KYO,
    LIOLLMON_BT25,
    LIOLLMON_BT26,
    MONARCHLIZAMON_DUAL,
    MONARCHLIZAMON_ST23,
    MURASAMEMON_BT25,
    MURASAMEMON_DUAL,
    MURASAMEMON_ST23,
    NIGHTCHIROPMON,
    TOMORO,
    TOMORO_KYO,
    UNSUSPEND_SOURCES,
    Card,
    Kind,
)
from .state import Stack, TamerInPlay

if TYPE_CHECKING:
    from .engine import Game

Action = Callable[[], None]


@dataclass
class Candidate:
    priority: float
    cost: int
    label: str
    run: Action


TAMER_PREF = {TOMORO_KYO: 3, KYO: 2, TOMORO: 1}


class Policy:
    # ------------------------------------------------------------------ opening
    def should_mulligan(self, g: Game, hand: list[Card]) -> bool:
        return not any(c.is_digimon and c.level == 3 for c in hand)

    # ------------------------------------------------------------------ valuations
    def card_value(self, g: Game, c: Card, in_hand: bool = False) -> float:
        """How much we want `c` in hand right now. Used for reveal picks, Kyo tucks and discards."""
        hand = [x for x in g.hand if x is not c] if in_hand else list(g.hand)
        field_levels = {st.level for st in g.stacks_on_field()}
        n_tamers = len(g.tamers)
        if c.is_tamer:
            return {0: 9.0, 1: 7.5, 2: 4.0}.get(n_tamers, 1.0) + TAMER_PREF[c.id] * 0.1
        if c.id == EPULSE:
            has_target = any(x.is_tamer for x in hand + g.trash)
            if has_target and n_tamers < 3:
                return 8.0
            return 4.0 if n_tamers else 1.5
        if c.id == GLOWING_DAWN:
            return 3.5
        if c.is_digimon:
            level = c.level or 0
            same = sum(1 for x in hand if x.is_digimon and x.level == level)
            below = (level - 1) in field_levels or any(x.is_digimon and x.level == level - 1 for x in hand)
            base = {3: 5.0, 4: 6.0, 5: 7.0, 6: 9.0}[level]
            if level >= 4 and not below:
                base -= 3.0
            if level == 3 and field_levels:
                base = 2.5      # a line is already started; spare Lv3s are tuck fodder
            if level == 6 and 6 in field_levels:
                base -= 4.0
            return base - 1.5 * same
        return 0.0

    def body_score(self, g: Game, c: Card) -> float:
        """How good `c` is as an extra Digimon played straight to the battle area."""
        if c.id == CHIROPMON:
            return 7.0 if any(x.is_digimon for x in g.trash) else 4.0
        return {COUGARMON_ST23: 10.0, GEKKOMON: 9.0, LIOLLMON_BT25: 8.0, ARMALIZAMON: 7.0,
                COUGARMON_BT26: 6.0, LIOLLMON_BT26: 5.0}.get(c.id, 3.0)

    def evo_pref(self, g: Game, st: Stack, c: Card) -> float:
        """Which card to digivolve into when several of the same level are in hand."""
        if c.level == 6:
            return {ATRATUSMON: 10.0, HABAKIRIMON: 8.0}[c.id]
        if c.level == 5:
            # Non-DUAL Lv5s carry the end-of-attack unsuspend as an inherited effect
            # and the -3 play/use trigger; the DUALs have neither.
            return {MURASAMEMON_BT25: 10.0, MURASAMEMON_ST23: 9.0, MONARCHLIZAMON_ST23: 9.0,
                    MONARCHLIZAMON_DUAL: 6.0, MURASAMEMON_DUAL: 5.0}[c.id]
        if c.level == 4:
            lv5_in_hand = any(x.is_digimon and x.level == 5 for x in g.hand)
            if c.id == COUGARMON_BT25 and lv5_in_hand and g.total_fuel() >= 3:
                return 10.0     # 2 fuel for a free Lv5 right away
            return {COUGARMON_ST23: 9.0, COUGARMON_BT25: 7.0, ARMALIZAMON: 6.0,
                    COUGARMON_BT26: 6.0, NIGHTCHIROPMON: 5.0}[c.id]
        if c.level == 3:
            return {GEKKOMON: 9.0, LIOLLMON_BT25: 8.0, LIOLLMON_BT26: 7.0, CHIROPMON: 6.0}[c.id]
        return 0.0

    # ------------------------------------------------------------------ small choices
    def pick_from_reveal(self, g: Game, seen: list[Card]) -> Card:
        return max(seen, key=lambda c: self.card_value(g, c))

    def pick_fuel_from_reveal(self, g: Game, seen: list[Card]) -> Card:
        return min(seen, key=lambda c: self.card_value(g, c))

    def pick_tuck(self, g: Game) -> Card | None:
        """Kyo's start-of-main tuck: the least useful card, unless the hand is one good card."""
        if not g.hand:
            return None
        c = min(g.hand, key=lambda x: self.card_value(g, x, in_hand=True))
        if len(g.hand) == 1 and self.card_value(g, c, in_hand=True) >= 6.0:
            return None
        return c

    def pick_discard(self, g: Game) -> Card | None:
        return min(g.hand, key=lambda x: self.card_value(g, x, in_hand=True)) if g.hand else None

    def choose_fuel_tamer(self, g: Game) -> TamerInPlay:
        return g.tamers[0]

    def pick_recursion(self, g: Game) -> Card | None:
        digis = [c for c in g.trash if c.is_digimon]
        return max(digis, key=lambda c: (c.level or 0, self.card_value(g, c))) if digis else None

    def pick_evo_card(self, g: Game, st: Stack, level: int) -> Card | None:
        cands = [c for c in g.hand if c.is_digimon and c.level == level]
        return max(cands, key=lambda c: self.evo_pref(g, st, c)) if cands else None

    def pick_sa_target(self, g: Game) -> Stack | None:
        cands = [st for st in g.battle if not st.suspended]
        return max(cands, key=lambda st: (st.can_attack(), st.level)) if cands else None

    def choose_alliance(self, g: Game, st: Stack) -> Stack | None:
        """Only ally with Digimon that could not attack anyway (played this turn)."""
        for o in g.battle:
            if o is not st and not o.suspended and not o.can_attack():
                return o
        return None

    def choose_arts_target(self, g: Game, card: Card, during_attack: Stack | None,
                           prefer: Stack | None = None) -> Stack | None:
        want = (card.level or 0) - 1
        cands = [st for st in g.stacks_on_field() if st.level == want]
        if not cands:
            return None

        def score(st: Stack) -> tuple:
            return (
                st is prefer,
                st is during_attack,
                st in g.battle,
                card.level == 6 and st.top.id in UNSUSPEND_SOURCES,   # keep the unsuspend under the Lv6
                st.can_attack(),
            )
        return max(cands, key=score)

    def want_free_chain(self, g: Game, st: Stack, c: Card) -> bool:
        return True

    def want_unsuspend(self, g: Game, st: Stack) -> bool:
        # Once memory has crossed to the opponent the turn is over, so the fuel would be wasted.
        return g.memory >= 0

    # ------------------------------------------------------------------ attack-time helpers
    def trick_available(self, g: Game, st: Stack) -> bool:
        return (st.has_source(KEKKOMON) and "kekkomon" not in st.used and g.total_fuel() >= 1
                and self.pick_evo_card(g, st, st.level + 1) is not None)

    def trick_pending(self, g: Game, st: Stack) -> bool:
        """Will Kekkomon's attack-time digivolve still fire for `st` this turn?"""
        return self.trick_available(g, st) and (st is g.attacking or st.can_attack())

    def trick_beats_arts(self, g: Game, st: Stack, c: Card, discount: int) -> bool:
        if not self.trick_pending(g, st):
            return False
        plan = g.digivolve_plan(st, c, trick=True)
        if plan is None or not g.can_pay(plan[0], g.floor):
            return False
        return plan[0] <= g.option_plan(c, discount)[0]

    def unsuspend_possible(self, g: Game, st: Stack) -> bool:
        if "unsuspend" in st.used:
            return False
        srcs = {c.id for c in st.sources}
        if st.level == 5:
            srcs.add(st.top.id)   # a trick into a Lv6 turns the current Lv5 into a source
        return bool(srcs & UNSUSPEND_SOURCES) and g.total_fuel() >= 1

    # ------------------------------------------------------------------ phases
    def breeding_phase(self, g: Game) -> None:
        st = g.breeding
        if st is None:
            if g.eggs:
                g.hatch()
            return
        if st.level >= 4 or (st.level == 3 and (g.tamers or g.turn >= 3)):
            g.move_from_breeding()

    def main_phase(self, g: Game) -> None:
        self.develop(g, "setup")         # keeps memory >= 0, so we still get to attack
        while not g.over:
            st = self.pick_attacker(g)
            if st is None:
                break
            g.floor = self.phase_floor(g, "attack", st)
            self.maybe_pre_attack_digivolve(g, st)
            if g.over:
                break
            g.attack(st)
            if g.memory < 0:
                break                    # memory crossed to the opponent: the turn ends
        if not g.over and g.memory >= 0:
            self.develop(g, "spend")     # spend the rest, down to what we are willing to give

    def tamer_reserve(self, g: Game) -> int | None:
        """Cost of the cheapest Tamer play we can still make this turn, while we have fewer
        than two Tamers out. Setup spending must leave room for it."""
        if len(g.tamers) >= 2:
            return None
        costs = [c.play_cost or 0 for c in g.hand if c.is_tamer]
        ep = next((c for c in g.hand if c.id == EPULSE), None)
        if ep is not None and g.has_use_req():
            target, _ = self.epulse_target(g)
            if target is not None and target.is_tamer:
                costs.append(g.option_plan(ep)[0])
        costs = [k for k in costs if g.memory - k >= -g.cfg.max_give]
        return min(costs) if costs else None

    def phase_floor(self, g: Game, phase: str, attacker: Stack | None = None) -> int:
        """Lowest memory we accept ending at during this phase of the turn."""
        base = -g.cfg.max_give
        reserve = self.tamer_reserve(g)
        reserve_floor = reserve - g.cfg.max_give if reserve is not None else base
        if phase == "setup":
            return max(0, reserve_floor)
        if phase == "attack":
            others = [o for o in g.battle if o is not attacker and o.can_attack()]
            floor = 0 if (others or (attacker is not None and self.unsuspend_possible(g, attacker))) else base
            return max(floor, reserve_floor)
        return base

    def pick_attacker(self, g: Game) -> Stack | None:
        elig = [st for st in g.battle if st.can_attack()]
        if not elig:
            return None
        return max(elig, key=lambda st: (st.level, self.trick_available(g, st)))

    def maybe_pre_attack_digivolve(self, g: Game, st: Stack) -> None:
        if self.trick_available(g, st):
            return                       # cheaper at attack time
        c = self.pick_evo_card(g, st, st.level + 1)
        if c is None:
            return
        route = self.best_route(g, st, c)
        if route is not None:
            g.say(f"[pre-attack {route.label}]")
            route.run()

    def best_route(self, g: Game, st: Stack, c: Card) -> Candidate | None:
        """Cheapest affordable way to turn `st` into `c`: trait digivolve or Option + Arts."""
        routes: list[Candidate] = []
        plan = g.digivolve_plan(st, c)
        if plan is not None:
            cost, fuel = plan
            routes.append(Candidate(0, cost, f"digivolve {st.top} -> {c}",
                                    lambda: g.digivolve(st, c, cost, fuel)))
        if c.kind is Kind.DUAL and g.has_use_req():
            ocost, _, _ = g.option_plan(c)
            routes.append(Candidate(0, ocost, f"use {c} + Arts onto {st.top}",
                                    lambda: g.use_option(c, g.hand, arts_target=st)))
        affordable = [r for r in routes if g.can_pay(r.cost, g.floor)]
        return min(affordable, key=lambda r: r.cost) if affordable else None

    def develop(self, g: Game, phase: str) -> None:
        while not g.over and g.memory >= 0:
            g.floor = self.phase_floor(g, phase)
            cand = self.best_development(g)
            if cand is None:
                return
            g.say(f"[{cand.label}]")
            cand.run()

    # Development priorities. The first two Tamers outrank everything but a Lv6;
    # a third Tamer is a luxury behind digivolving.
    TAMER_PRIO = {0: 95, 1: 90, 2: 50}
    EVO_PRIO = {3: 75, 4: 80, 5: 85, 6: 92}

    def best_development(self, g: Game) -> Candidate | None:
        cands: list[Candidate] = []
        floor = g.floor
        n_tamers = len(g.tamers)

        # 1. Tamers are the engine; we want two quickly and stop at three.
        if n_tamers < 3:
            for c in sorted((c for c in g.hand if c.is_tamer), key=lambda c: -TAMER_PREF[c.id]):
                if g.can_pay(c.play_cost or 0, floor):
                    cands.append(Candidate(self.TAMER_PRIO[n_tamers], c.play_cost or 0,
                                           f"play {c}", lambda c=c: g.play_card(c, g.hand)))
                    break
        # 2. e-Pulse into a Tamer (or a body once the engine is running).
        ep = next((c for c in g.hand if c.id == EPULSE), None)
        if ep is not None and g.has_use_req():
            target, _ = self.epulse_target(g)
            if target is not None:
                cost, _, _ = g.option_plan(ep)
                if g.can_pay(cost, floor):
                    prio = self.TAMER_PRIO.get(n_tamers, 45) + 2 if target.is_tamer else 45
                    cands.append(Candidate(prio, cost, f"e-Pulse -> {target}",
                                           lambda: g.use_option(ep, g.hand)))
        # 3. Digivolves, highest resulting level first; attackers wait for Kekkomon's trick.
        for st in g.stacks_on_field():
            if st in g.battle and st.can_attack() and self.trick_available(g, st):
                continue
            c = self.pick_evo_card(g, st, st.level + 1)
            if c is None:
                continue
            route = self.best_route(g, st, c)
            if route is None:
                continue
            prio = self.EVO_PRIO[c.level or 3] + (1 if st in g.battle else 0)
            cands.append(Candidate(prio, route.cost, route.label, route.run))
        # 4. Glowing Dawn: dig now, +2 memory next turn.
        gd = next((c for c in g.hand if c.id == GLOWING_DAWN), None)
        if gd is not None and g.has_use_req():
            cost, _, _ = g.option_plan(gd)
            if g.can_pay(cost, floor):
                cands.append(Candidate(40, cost, "use Glowing Dawn", lambda: g.use_option(gd, g.hand)))
        # 5. NightChiropmon [Main]: 2 fuel to reuse a Glowing Dawn Option from the trash at -2.
        for st in g.battle:
            if st.top.id == NIGHTCHIROPMON and "nc_main" not in st.used and g.total_fuel() >= 2:
                action = self.plan_option_use(g, st, discount=2, source=g.trash, extra_fuel=2)
                if action is not None:
                    def reuse(st: Stack = st, action: Action = action) -> None:
                        st.used.add("nc_main")
                        g.trash_fuel(2)
                        action()
                    cands.append(Candidate(45, 0, "NightChiropmon reuses an Option", reuse))
        # 6. A second body once the engine is running: an Alliance partner / extra attacker.
        if g.tamers and g.turn >= 3 and len(g.battle) < 2:
            bodies = [c for c in g.hand if c.is_digimon and c.play_cost is not None and (c.level or 0) <= 4]
            for c in sorted(bodies, key=lambda c: -self.body_score(g, c)):
                if g.can_pay(c.play_cost or 0, floor):
                    cands.append(Candidate(30, c.play_cost or 0, f"play {c} as a body",
                                           lambda c=c: g.play_card(c, g.hand)))
                    break
        if not cands:
            return None
        return max(cands, key=lambda k: (k.priority, -k.cost))

    # ------------------------------------------------------------------ discounted plays
    def epulse_target(self, g: Game) -> tuple[Card | None, list[Card] | None]:
        """What e-Pulse would play for free: a Tamer first, else a body while a Tamer is out
        (its start-of-main tuck needs a BEATBREAK Tamer, so without one a body wastes it)."""
        if len(g.tamers) < 3:
            for cid in (TOMORO_KYO, KYO, TOMORO):
                for src in (g.hand, g.trash):
                    c = next((x for x in src if x.id == cid), None)
                    if c is not None:
                        return c, src
        if g.tamers and len(g.battle) < 3:
            best: tuple[Card, list[Card]] | None = None
            for src in (g.hand, g.trash):
                for x in src:
                    if x.is_digimon and x.play_cost is not None and x.play_cost <= 4:
                        if best is None or self.body_score(g, x) > self.body_score(g, best[0]):
                            best = (x, src)
            if best is not None:
                return best
        return None, None

    def option_candidates(self, g: Game, st: Stack, discount: int, source: list[Card],
                          extra_fuel: int = 0) -> list[tuple[float, Action]]:
        """(value, action) pairs for using a Glowing Dawn Option from `source` right now,
        with `discount` already granted by the triggering card."""
        out: list[tuple[float, Action]] = []
        if not g.has_use_req():
            return out
        in_attack = st if st is g.attacking else None

        def affordable(card: Card) -> bool:
            cost, fuel, _ = g.option_plan(card, discount)
            return g.can_pay(cost, g.floor) and g.total_fuel() >= fuel + extra_fuel

        seen: set[str] = set()
        for c in source:
            if c.id in seen or not c.is_option:
                continue
            seen.add(c.id)
            if c.id == EPULSE:
                target, _ = self.epulse_target(g)
                if target is not None and affordable(c):
                    out.append((80.0 if target.is_tamer else 50.0,
                                lambda c=c: g.use_option(c, source, discount, during_attack=in_attack)))
            elif c.id == GLOWING_DAWN:
                if affordable(c):
                    out.append((40.0, lambda c=c: g.use_option(c, source, discount, during_attack=in_attack)))
            elif c.kind is Kind.DUAL:
                tgt = self.choose_arts_target(g, c, in_attack, prefer=st)
                if tgt is None or not affordable(c):
                    continue
                if tgt is st and self.trick_beats_arts(g, st, c, discount):
                    continue
                out.append((100.0 if c.level == 6 else 60.0,
                            lambda c=c, tgt=tgt: g.use_option(c, source, discount, during_attack=in_attack,
                                                              arts_target=tgt)))
        return out

    def plan_option_use(self, g: Game, st: Stack, discount: int, source: list[Card] | None = None,
                        extra_fuel: int = 0) -> Action | None:
        """Best Glowing Dawn Option to use right now at `discount` (Cougarmon BT26-026,
        NightChiropmon), or None if nothing is worth the activation cost."""
        cands = self.option_candidates(g, st, discount, g.hand if source is None else source, extra_fuel)
        return max(cands, key=lambda k: k[0])[1] if cands else None

    def plan_discounted_play(self, g: Game, st: Stack, discount: int) -> Action | None:
        """Murasamemon / Monarchlizamon trigger: play or use 1 Glowing Dawn card at -3."""
        cands = self.option_candidates(g, st, discount, g.hand)
        floor = g.floor
        if len(g.tamers) < 3:
            for c in sorted((c for c in g.hand if c.is_tamer), key=lambda c: -TAMER_PREF[c.id]):
                cost = max((c.play_cost or 0) - discount, 0)
                if g.can_pay(cost, floor):
                    cands.append((75.0, lambda c=c, cost=cost: g.play_card(c, g.hand, cost=cost)))
                    break
        if len(g.battle) < 3:
            bodies = [c for c in g.hand if c.is_digimon and c.play_cost is not None and (c.level or 0) <= 4]
            if bodies:
                c = max(bodies, key=lambda x: self.body_score(g, x))
                cost = max((c.play_cost or 0) - discount, 0)
                if g.can_pay(cost, floor):
                    cands.append((30.0, lambda c=c, cost=cost: g.play_card(c, g.hand, cost=cost)))
        return max(cands, key=lambda k: k[0])[1] if cands else None
