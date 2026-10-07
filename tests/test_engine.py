import random
import unittest
from pathlib import Path

from goldfish import effects
from goldfish.cards import CARDS
from goldfish.decklist import parse_decklist
from goldfish.engine import Game, GameOver
from goldfish.policy import Policy
from goldfish.state import Config, Stack, TamerInPlay

DECK = parse_decklist((Path(__file__).resolve().parent.parent / "decks" / "glowing_dawn.txt").read_text())


def card(cid):
    return CARDS[cid]


def make_game(*, hand=(), battle=(), tamers=(), fuel=0, memory=3, security=5, opp_security=5,
              turn=3, going_first=False, filler="ST23-15"):
    """A game with hand-built zones. The library, security and fuel are all `filler`
    (e-Pulse by default: inert unless a Tamer target exists), so draws are predictable."""
    g = Game(DECK, Policy(), random.Random(0), going_first, Config())
    g.turn, g.memory, g.floor = turn, memory, -g.cfg.max_give
    g.deck = [card(filler)] * 20
    g.hand = [card(c) for c in hand]
    g.security = [card(filler)] * security
    g.opp_security = opp_security
    for ids in battle:
        st = Stack([card(c) for c in ids])
        st.can_attack_flag = True
        g.battle.append(st)
    for tid in tamers:
        g.tamers.append(TamerInPlay(card(tid)))
    for _ in range(fuel):
        g.tamers[0].fuel.append(card(filler))
    return g


class KekkomonTrickTests(unittest.TestCase):
    def test_trick_stacks_with_cougarmon_discount(self):
        g = make_game(hand=["BT25-041"], battle=[["ST23-01", "BT25-032", "ST23-03"]],
                      tamers=["ST23-13"], fuel=3, memory=0)
        g.floor = 0
        st = g.battle[0]
        g.attack(st)
        self.assertEqual(st.top.id, "BT25-041")
        self.assertEqual(g.memory, 0)               # 3 - 2 (Kekkomon) - 2 (Cougarmon) floors at 0
        self.assertEqual(g.total_fuel(), 1)         # one fuel per discount
        self.assertEqual(g.stats.kekkomon_tricks, 1)
        self.assertEqual(g.opp_security, 4)
        self.assertTrue(st.suspended)               # Murasamemon on top: its unsuspend is inherited only

    def test_trick_into_lv6_then_inherited_unsuspend(self):
        g = make_game(hand=["ST23-09"], battle=[["ST23-01", "ST23-06", "ST23-03", "BT25-041"]],
                      tamers=["ST23-13"], fuel=2, memory=3)
        st = g.battle[0]
        g.attack(st)
        self.assertEqual(st.top.id, "ST23-09")
        self.assertEqual(g.memory, 2)               # trick: 3 - 2 = 1, cheaper than Option + Arts (2)
        self.assertEqual(g.stats.kekkomon_tricks, 1)
        self.assertEqual(g.stats.arts_digivolves, 0)
        self.assertEqual(g.opp_security, 3)         # Security Attack +1
        self.assertFalse(st.suspended)              # Murasamemon's inherited end-of-attack unsuspend
        self.assertEqual(g.total_fuel(), 0)

    def test_trick_is_once_per_turn(self):
        # Monarchlizamon DUAL on top: no play/use trigger, so only the trick could digivolve it.
        g = make_game(hand=["ST23-09"], battle=[["ST23-01", "ST23-06", "ST23-03", "BT25-057"]],
                      tamers=["ST23-13"], fuel=3, memory=3)
        st = g.battle[0]
        st.used.add("kekkomon")
        g.attack(st)
        self.assertEqual(st.top.id, "BT25-057")
        self.assertEqual(g.stats.kekkomon_tricks, 0)


class ArtsDigivolveTests(unittest.TestCase):
    def test_arts_digivolve_through_murasamemon_discount(self):
        g = make_game(hand=["ST23-09"], battle=[["ST23-01", "ST23-06", "ST23-03", "BT25-041"]],
                      tamers=["ST23-13"], fuel=1, memory=3)
        st = g.battle[0]
        hand_before = len(g.hand)
        g.use_option(card("ST23-09"), g.hand, discount=3, during_attack=st, arts_target=st)
        self.assertEqual(st.top.id, "ST23-09")
        self.assertEqual(g.memory, 1)               # 5 - 3 = 2
        self.assertEqual(g.stats.arts_digivolves, 1)
        self.assertEqual(len(g.hand), hand_before)  # -1 Atratusmon, +1 digivolution draw
        self.assertEqual(len(g.trash), 0)           # Arts replaces the trashing

    def test_option_without_a_legal_target_is_trashed(self):
        g = make_game(hand=["ST23-09"], battle=[["ST23-01", "ST23-06", "ST23-03"]], memory=5)
        g.use_option(card("ST23-09"), g.hand)
        self.assertEqual(g.battle[0].level, 4)
        self.assertEqual([c.id for c in g.trash], ["ST23-09"])

    def test_murasamemon_trigger_takes_the_arts_route_when_the_trick_is_spent(self):
        g = make_game(hand=["ST23-09"], battle=[["ST23-01", "ST23-06", "ST23-03", "BT25-041"]],
                      tamers=["ST23-13"], fuel=2, memory=3)
        st = g.battle[0]
        st.used.add("kekkomon")
        g.attack(st)
        self.assertEqual(st.top.id, "ST23-09")
        self.assertEqual(g.stats.arts_digivolves, 1)
        self.assertEqual(g.memory, 1)               # Option 5 - 3 = 2
        self.assertEqual(g.opp_security, 3)         # the attack continues as Atratusmon


class InheritedUnsuspendTests(unittest.TestCase):
    def test_dual_lv5_gives_no_end_of_attack_unsuspend(self):
        g = make_game(battle=[["ST23-01", "ST23-06", "ST23-03", "BT25-057", "ST23-09"]], tamers=["ST23-13"], fuel=2)
        st = g.battle[0]
        g.attack(st)
        self.assertTrue(st.suspended)
        self.assertEqual(g.total_fuel(), 2)

    def test_non_dual_lv5_unsuspends_for_one_fuel(self):
        g = make_game(battle=[["ST23-01", "ST23-06", "ST23-03", "ST23-08", "ST23-09"]], tamers=["ST23-13"], fuel=2)
        st = g.battle[0]
        g.attack(st)
        self.assertFalse(st.suspended)
        self.assertEqual(g.total_fuel(), 1)


class HabakirimonTests(unittest.TestCase):
    STACK = ["ST23-01", "ST23-06", "ST23-03", "ST23-04", "BT25-043"]

    def test_tie_trashes_the_opponents_card(self):
        g = make_game(battle=[self.STACK], security=4, opp_security=5)
        st = g.battle[0]
        st.suspended = True
        effects.habakirimon(g, st)
        self.assertEqual(len(g.security), 5)        # Recovery +1 first
        self.assertEqual(g.opp_security, 4)         # tie at 5: their card goes
        self.assertEqual(g.stats.opp_trashed, 1)
        self.assertFalse(st.suspended)

    def test_more_than_the_opponent_trashes_own_card(self):
        g = make_game(battle=[self.STACK], security=5, opp_security=5)
        st = g.battle[0]
        st.suspended = True
        effects.habakirimon(g, st)
        self.assertEqual(len(g.security), 5)        # +1 then -1
        self.assertEqual(g.opp_security, 5)
        self.assertEqual(len(g.trash), 1)
        self.assertFalse(st.suspended)

    def test_once_per_turn(self):
        g = make_game(battle=[self.STACK], security=5, opp_security=5)
        st = g.battle[0]
        st.suspended = True
        effects.habakirimon(g, st)
        st.suspended = True
        effects.habakirimon(g, st)                  # once per turn: no second Recovery, no second trash
        self.assertEqual(len(g.security), 5)
        self.assertEqual(len(g.trash), 1)
        self.assertTrue(st.suspended)

    def test_does_not_pay_to_unsuspend_an_unsuspended_digimon(self):
        g = make_game(battle=[self.STACK], security=5, opp_security=5)
        st = g.battle[0]
        effects.habakirimon(g, st)
        self.assertEqual(len(g.security), 6)        # Recovery happened, the optional trash did not
        self.assertEqual(len(g.trash), 0)


class EndingTests(unittest.TestCase):
    def test_lethal_when_attacking_into_zero_security(self):
        g = make_game(battle=[["ST23-01", "ST23-06"]], opp_security=0)
        with self.assertRaises(GameOver):
            g.attack(g.battle[0])
        self.assertEqual(g.stats.kill_turn, 3)
        self.assertTrue(g.over)

    def test_deck_out_on_empty_draw(self):
        g = make_game()
        g.deck = []
        with self.assertRaises(GameOver):
            g.draw(1)
        self.assertEqual(g.stats.deck_out_turn, 3)


class TamerAndOptionTests(unittest.TestCase):
    def test_epulse_plays_a_tamer_then_tucks_next_turn(self):
        g = make_game(hand=["ST23-15", "BT26-089"], tamers=["ST23-13"], memory=3)
        g.use_option(card("ST23-15"), g.hand)
        self.assertEqual([t.card.id for t in g.tamers], ["ST23-13", "BT26-089"])
        self.assertEqual(g.memory, 0)
        self.assertEqual(len(g.placed), 1)
        g.turn += 1
        g.memory = 3
        effects.start_of_main(g)
        self.assertEqual(len(g.placed), 0)
        # e-Pulse tuck +1, Kyo tuck +1, Tomoro & Kyo +1 (the opponent has a Digimon by now)
        self.assertEqual(g.memory, 6)
        self.assertEqual(g.total_fuel(), 3)

    def test_tomoro_kyo_memory_needs_an_opposing_digimon(self):
        g = make_game(hand=["ST23-13"], memory=4, turn=1, going_first=True)
        g.play_card(card("ST23-13"), g.hand)
        self.assertEqual(g.memory, 0)               # paid 4, no memory back on turn 1 going first
        self.assertEqual(g.total_fuel(), 1)

    def test_armalizamon_and_tomoro_discount_options(self):
        g = make_game(hand=["ST23-15", "BT26-089"], battle=[["ST23-01", "ST23-06", "BT25-049"]],
                      tamers=["ST23-13", "BT25-090"], fuel=2, memory=0)
        g.use_option(card("ST23-15"), g.hand)
        self.assertEqual(g.memory, 0)               # 3 - 3 (Armalizamon, 1 fuel); Tomoro not needed
        self.assertEqual(g.total_fuel(), 1)
        self.assertIn("armaliza", g.battle[0].used)
        self.assertEqual([t.card.id for t in g.tamers][-1], "BT26-089")


class FullGameTests(unittest.TestCase):
    def test_games_conserve_cards_and_respect_max_give(self):
        for seed in range(300):
            g = Game(DECK, Policy(), random.Random(seed), seed % 2 == 0, Config())
            stats = g.play()
            self.assertEqual(len(g.all_cards()), 54, f"seed {seed}: cards leaked")
            self.assertTrue(all(m <= 3 for m in stats.memory_given), f"seed {seed}: gave {stats.memory_given}")
            if stats.kill_turn is not None:
                self.assertGreaterEqual(stats.checks + stats.opp_trashed, 5, f"seed {seed}")
            self.assertEqual(len(stats.checks_by_turn), stats.turns_played)


if __name__ == "__main__":
    unittest.main()
