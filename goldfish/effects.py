"""Card effects, keyed by card id.

Each function models exactly the printed text, restricted to what can matter in
a goldfish game. Effects that only touch the opponent's board (DP minus,
suspend, delete, De-Digivolve, "can't suspend", immunity) are left out on
purpose and noted where they occur. Every optional ("by ...", "you may") choice
is routed through the policy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .cards import (
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
    TOMORO_KYO,
    UNSUSPEND_SOURCES,
    Card,
)
from .state import PlacedOption, Stack, TamerInPlay

if TYPE_CHECKING:
    from .engine import Game


# ---------------------------------------------------------------------- tamers
def tomoro_kyo_trigger(g: Game, t: TamerInPlay) -> None:
    """[Start of Your Main Phase] [On Play] Place the top card of your deck under this
    Tamer. Then, if your opponent has a Digimon, gain 1 memory."""
    g.place_fuel_from_deck(t, 1)
    if g.opp_has_digimon():
        g.gain(1)


def on_play_tamer(g: Game, t: TamerInPlay) -> None:
    if t.card.id == TOMORO_KYO:
        tomoro_kyo_trigger(g, t)


def start_of_main(g: Game) -> None:
    # Glowing Dawn [Delay]: by trashing this card after the placing turn, gain 2 memory.
    for p in list(g.placed):
        if p.card.id == GLOWING_DAWN and p.placed_turn < g.turn:
            g.placed.remove(p)
            g.trash.append(p.card)
            g.gain(2)
            g.say("Glowing Dawn delay: +2 memory")
    # e-Pulse [Start of Your Main Phase]: by placing this card from the battle area
    # under a BEATBREAK Tamer, draw 1 and gain 1 memory.
    for p in list(g.placed):
        if p.card.id == EPULSE and g.tamers:
            g.placed.remove(p)
            g.place_fuel(p.card)
            g.draw(1)
            g.gain(1)
            g.say("e-Pulse tucks under a Tamer: draw 1, +1 memory")
    # Kyo [Start of Your Main Phase]: by placing 1 BEATBREAK card from your hand
    # under this Tamer, draw 1 and gain 1 memory.
    for t in g.tamers:
        if t.card.id == KYO:
            c = g.policy.pick_tuck(g)
            if c is not None:
                g.hand.remove(c)
                g.place_fuel(c, t)
                g.draw(1)
                g.gain(1)
                g.say(f"Kyo tucks {c}: draw 1, +1 memory")
    for t in g.tamers:
        if t.card.id == TOMORO_KYO:
            tomoro_kyo_trigger(g, t)
            g.say("Tomoro & Kyo: +1 fuel" + (", +1 memory" if g.opp_has_digimon() else ""))


# ---------------------------------------------------------------------- digimon
def gekkomon(g: Game, st: Stack) -> None:
    """[When Moving] [On Play] Reveal the top 3 cards. Add 1 Glowing Dawn card to the
    hand and place 1 such card under any of your Glowing Dawn Tamers. Rest to bottom."""
    seen = g.reveal(3)
    if not seen:
        return
    pick = g.policy.pick_from_reveal(g, seen)
    seen.remove(pick)
    g.hand.append(pick)
    if g.tamers and seen:
        fuel = g.policy.pick_fuel_from_reveal(g, seen)
        seen.remove(fuel)
        g.place_fuel(fuel)
    g.to_bottom(seen)


def liollmon_bt25(g: Game, st: Stack) -> None:
    """[On Play] Reveal the top 3 cards. Add 1 Glowing Dawn card and 1 yellow BEATBREAK
    card among them to the hand. Rest to bottom."""
    seen = g.reveal(3)
    if not seen:
        return
    pick = g.policy.pick_from_reveal(g, seen)
    seen.remove(pick)
    g.hand.append(pick)
    yellow = [c for c in seen if c.is_yellow]
    if yellow:
        pick2 = g.policy.pick_from_reveal(g, yellow)
        seen.remove(pick2)
        g.hand.append(pick2)
    g.to_bottom(seen)


def liollmon_bt26(g: Game, st: Stack) -> None:
    """[When Moving] [On Play] By placing your top security card under any of your
    Glowing Dawn Tamers, <Recovery +1 (Deck)>."""
    if g.security_to_fuel():
        g.recovery(1)


def liollmon_bt26_inherited(g: Game, st: Stack) -> None:
    """[When Attacking][Once Per Turn] You may add your top security card to the hand.
    Then, if you have 0 security cards, <Recovery +1 (Deck)>."""
    if "lio26" in st.used or len(g.security) <= g.cfg.min_security:
        return
    st.used.add("lio26")
    g.security_to_hand()
    if not g.security:
        g.recovery(1)


def chiropmon(g: Game, st: Stack) -> None:
    """[On Play] By trashing 1 fuel, return 1 Glowing Dawn Digimon card from trash to hand."""
    target = g.policy.pick_recursion(g)
    if target is not None and g.trash_fuel(1):
        g.trash.remove(target)
        g.hand.append(target)
        g.say(f"Chiropmon returns {target} to hand")


def cougarmon_st23(g: Game, st: Stack) -> None:
    """[On Play] [When Digivolving] Add your top security card to the hand. Then <Recovery +1>."""
    g.security_to_hand()
    g.recovery(1)


def cougarmon_bt25(g: Game, st: Stack) -> None:
    """[On Play] [When Digivolving] (-3000 DP to an opponent's Digimon: not modeled.) Then,
    by trashing 2 fuel, this Digimon may digivolve into a Glowing Dawn Digimon card in
    the hand without paying the cost."""
    c = g.policy.pick_evo_card(g, st, st.level + 1)
    if c is not None and g.total_fuel() >= 2 and g.policy.want_free_chain(g, st, c):
        g.trash_fuel(2)
        g.stats.free_digivolves += 1
        g.digivolve(st, c, cost=0)


def cougarmon_bt26_attacking(g: Game, st: Stack) -> None:
    """[When Attacking][Once Per Turn] By trashing 1 fuel or your top security card, you
    may use 1 Glowing Dawn Option card from your hand with the cost reduced by 2."""
    if "c26" in st.used:
        return
    action = g.policy.plan_option_use(g, st, discount=2)
    if action is None:
        return
    paid = (len(g.security) > g.cfg.min_security and g.trash_security()) or g.trash_fuel(1)
    if paid:
        st.used.add("c26")
        action()


def nightchiropmon(g: Game, st: Stack) -> None:
    """[On Play] [When Digivolving] <Draw 1> and trash 1 card in your hand."""
    g.draw(1)
    c = g.policy.pick_discard(g)
    if c is not None:
        g.hand.remove(c)
        g.trash.append(c)


def lv5_play_or_use(g: Game, st: Stack) -> None:
    """Murasamemon ST23-04 / Monarchlizamon ST23-08 [On Play] [When Digivolving]: (DP effect
    not modeled.) Then, if it's your turn, by trashing 1 fuel, you may play or use 1
    Glowing Dawn card from your hand with the cost reduced by 3."""
    action = g.policy.plan_discounted_play(g, st, discount=3)
    if action is not None and g.trash_fuel(1):
        action()


def murasamemon_bt25(g: Game, st: Stack) -> None:
    """[When Digivolving] [When Attacking] [Once Per Turn] If it's your turn, by adding
    your top security card to the hand or trashing 1 fuel, you may play or use 1 Glowing
    Dawn card from your hand with the cost reduced by 3."""
    if "m041" in st.used:
        return
    action = g.policy.plan_discounted_play(g, st, discount=3)
    if action is None:
        return
    paid = (len(g.security) > g.cfg.min_security and g.security_to_hand()) or g.trash_fuel(1)
    if paid:
        st.used.add("m041")
        action()


def murasamemon_dual(g: Game, st: Stack) -> None:
    """[When Digivolving] (trash a security card so an opponent's card can't suspend: not
    modeled.) [When Digivolving] [When Attacking] [Once Per Turn] By trashing 1 fuel,
    <Recovery +1 (Deck)>."""
    if "m031" in st.used:
        return
    if len(g.security) <= g.cfg.min_security and g.trash_fuel(1):
        st.used.add("m031")
        g.recovery(1)


def habakirimon(g: Game, st: Stack) -> None:
    """[When Digivolving] [When Attacking] [Once Per Turn] <Recovery +1 (Deck)>. Then, by
    trashing the top security card of 1 player with the most security cards, this
    Digimon unsuspends."""
    if "haba" in st.used:
        return
    st.used.add("haba")
    g.recovery(1)
    mine, theirs = len(g.security), g.opp_security
    most = max(mine, theirs)
    if theirs == most and theirs > 0:
        g.trash_opp_security()           # free damage, and the unsuspend comes with it
        st.suspended = False
        g.say(f"  Habakirimon trashes an opponent's security card; opponent at {g.opp_security}")
    elif mine == most and st.suspended and mine > g.cfg.min_security:
        g.trash_security()
        st.suspended = False
        g.say("  Habakirimon trashes our top security card to unsuspend")


def atratusmon(g: Game, st: Stack) -> None:
    """[When Digivolving] [When Attacking] [Once Per Turn] Immunity and delete the
    opponent's lowest-DP Digimon: nothing to model in a goldfish game."""
    st.used.add("atra")


def kekkomon_trick(g: Game, st: Stack) -> None:
    """Kekkomon inherited: [When Attacking][Once Per Turn] By trashing 1 fuel, this Digimon
    may digivolve into a Glowing Dawn Digimon card in the hand with the cost reduced by 2."""
    if "kekkomon" in st.used or g.total_fuel() < 1:
        return
    c = g.policy.pick_evo_card(g, st, st.level + 1)
    if c is None:
        return
    plan = g.digivolve_plan(st, c, trick=True)
    if plan is None or not g.can_pay(plan[0], g.floor):
        return
    st.used.add("kekkomon")
    g.stats.kekkomon_tricks += 1
    g.digivolve(st, c, cost=plan[0], fuel=plan[1])


# ---------------------------------------------------------------------- options
def resolve_option(g: Game, card: Card, during_attack: Stack | None, arts_target: Stack | None) -> None:
    """Resolve an Option (or a DUAL card's Option information) that has been paid for."""
    if card.id == EPULSE:
        # [Main] Play 1 BEATBREAK card with play cost 4 or less from hand or trash for free.
        # Then place this card in the battle area.
        target, source = g.policy.epulse_target(g)
        if target is not None:
            g.play_card(target, source, free=True)
        g.placed.append(PlacedOption(card, g.turn))
        return
    if card.id == GLOWING_DAWN:
        # [Main] Reveal 3, add 1 Glowing Dawn card, rest to bottom. Place this card in the battle area.
        seen = g.reveal(3)
        if seen:
            pick = g.policy.pick_from_reveal(g, seen)
            seen.remove(pick)
            g.hand.append(pick)
            g.to_bottom(seen)
        g.placed.append(PlacedOption(card, g.turn))
        return
    if card.id == MONARCHLIZAMON_DUAL:
        # [Main] 1 of your Digimon gains <Rush>, <Security Attack +1> and +5000 DP for the
        # turn (errata: your turn only). Then, it may attack.
        target = during_attack or g.policy.pick_sa_target(g)
        if target is not None:
            target.rush = True
            target.sa_turn_bonus += 1
    # MURASAMEMON_DUAL, HABAKIRIMON and ATRATUSMON Option halves only touch the
    # opponent's board: nothing to model. Arts Digivolve applies to all four DUALs.
    st = arts_target or g.policy.choose_arts_target(g, card, during_attack)
    if st is not None and st.level == (card.level or 0) - 1:
        g.arts_digivolve(st, card)
    else:
        g.trash.append(card)


# ---------------------------------------------------------------------- dispatch
ON_PLAY = {
    GEKKOMON: gekkomon,
    LIOLLMON_BT25: liollmon_bt25,
    LIOLLMON_BT26: liollmon_bt26,
    CHIROPMON: chiropmon,
    COUGARMON_ST23: cougarmon_st23,
    COUGARMON_BT25: cougarmon_bt25,
    NIGHTCHIROPMON: nightchiropmon,
    MURASAMEMON_ST23: lv5_play_or_use,
    MONARCHLIZAMON_ST23: lv5_play_or_use,
}

WHEN_DIGIVOLVING = {
    COUGARMON_ST23: cougarmon_st23,
    COUGARMON_BT25: cougarmon_bt25,
    NIGHTCHIROPMON: nightchiropmon,
    MURASAMEMON_ST23: lv5_play_or_use,
    MONARCHLIZAMON_ST23: lv5_play_or_use,
    MURASAMEMON_BT25: murasamemon_bt25,
    MURASAMEMON_DUAL: murasamemon_dual,
    HABAKIRIMON: habakirimon,
    ATRATUSMON: atratusmon,
}

WHEN_MOVING = {
    GEKKOMON: gekkomon,
    LIOLLMON_BT26: liollmon_bt26,
}

WHEN_ATTACKING = {
    COUGARMON_BT26: cougarmon_bt26_attacking,
    MURASAMEMON_BT25: murasamemon_bt25,
    MURASAMEMON_DUAL: murasamemon_dual,
    HABAKIRIMON: habakirimon,
    ATRATUSMON: atratusmon,
}


def on_play(g: Game, st: Stack) -> None:
    fn = ON_PLAY.get(st.top.id)
    if fn:
        fn(g, st)


def when_digivolving(g: Game, st: Stack) -> None:
    fn = WHEN_DIGIVOLVING.get(st.top.id)
    if fn:
        fn(g, st)


def when_moving(g: Game, st: Stack) -> None:
    fn = WHEN_MOVING.get(st.top.id)
    if fn:
        fn(g, st)


def when_attacking(g: Game, st: Stack) -> None:
    """The top card's own [When Attacking] first, then inherited ones, Kekkomon's last so
    nothing is pending on a card that has just been digivolved over."""
    fn = WHEN_ATTACKING.get(st.top.id)
    if fn:
        fn(g, st)
    if st.has_source(LIOLLMON_BT26):
        liollmon_bt26_inherited(g, st)
    if st.has_source(KEKKOMON):
        kekkomon_trick(g, st)


def end_of_attack(g: Game, st: Stack) -> None:
    """Inherited from Murasamemon / Monarchlizamon (non-DUAL): [End of Attack][Once Per
    Turn] By trashing 1 fuel, this Digimon unsuspends."""
    if "unsuspend" in st.used or not st.suspended:
        return
    if not any(c.id in UNSUSPEND_SOURCES for c in st.sources):
        return
    if g.policy.want_unsuspend(g, st) and g.trash_fuel(1):
        st.used.add("unsuspend")
        st.suspended = False
        g.say(f"  {st.top} unsuspends (inherited, 1 fuel)")
