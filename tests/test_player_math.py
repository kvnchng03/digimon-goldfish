import random
import unittest

from goldfish import odds


def deal(rng, deck, groups):
    """A shuffled deck as a list of group labels ('a', 'b' or '-')."""
    cards = []
    for label, n in groups.items():
        cards += [label] * n
    cards += ["-"] * (deck - len(cards))
    rng.shuffle(cards)
    return cards


def sim_by_n(rng, games, deck, copies, seen, k, redraw):
    hits = 0
    for _ in range(games):
        cards = deal(rng, deck, {"a": copies})
        if redraw and "a" not in cards[:5]:
            cards = deal(rng, deck, {"a": copies})
        hits += cards[:seen].count("a") >= k
    return hits / games


def sim_both_by_n(rng, games, deck, a, b, seen, redraw):
    hits = 0
    for _ in range(games):
        cards = deal(rng, deck, {"a": a, "b": b})
        if redraw and "a" not in cards[:5]:
            cards = deal(rng, deck, {"a": a, "b": b})
        hits += "a" in cards[:seen] and "b" in cards[:seen]
    return hits / games


class DrawOdds(unittest.TestCase):
    def test_at_least_matches_simulation(self):
        rng = random.Random(1)
        for deck, copies, seen, k in ((50, 4, 5, 1), (50, 8, 9, 2), (50, 12, 7, 3), (40, 3, 10, 1)):
            exact = odds.p_at_least(deck, copies, seen, k)
            sim = sim_by_n(rng, 40000, deck, copies, seen, k, redraw=False)
            self.assertAlmostEqual(exact, sim, delta=0.012, msg=(deck, copies, seen, k))

    def test_redraw_on_none_matches_simulation(self):
        rng = random.Random(2)
        for deck, copies, seen, k in ((50, 4, 5, 1), (50, 4, 8, 1), (50, 8, 9, 2), (50, 12, 10, 3)):
            exact = odds.p_by_n(deck, copies, seen, k, redraw=True)
            sim = sim_by_n(rng, 40000, deck, copies, seen, k, redraw=True)
            self.assertAlmostEqual(exact, sim, delta=0.012, msg=(deck, copies, seen, k))

    def test_redraw_reduces_to_the_textbook_form_for_one_copy(self):
        p5 = odds.p_at_least(50, 4, 5)
        p8 = odds.p_at_least(50, 4, 8)
        self.assertAlmostEqual(odds.p_by_n(50, 4, 8, 1), 1 - (1 - p5) * (1 - p8))

    def test_both_matches_simulation(self):
        rng = random.Random(3)
        for deck, a, b, seen in ((50, 12, 8, 5), (50, 12, 8, 9), (50, 4, 4, 7)):
            for redraw, exact in ((False, odds.p_both(deck, a, b, seen)), (True, odds.p_both_by_n(deck, a, b, seen))):
                sim = sim_both_by_n(rng, 40000, deck, a, b, seen, redraw)
                self.assertAlmostEqual(exact, sim, delta=0.012, msg=(deck, a, b, seen, redraw))

    def test_cards_seen(self):
        self.assertEqual(odds.cards_seen(1, True, 0, 50), 5)   # first player: no draw on turn 1
        self.assertEqual(odds.cards_seen(1, False, 0, 50), 6)
        self.assertEqual(odds.cards_seen(2, True, 1, 50), 8)
        self.assertEqual(odds.cards_seen(40, False, 1, 50), 45)  # never past the deck minus security


def sim_midgame(rng, games, deck, copies, drawn, seen_outs, bottom_outs, look):
    """Deal for real: 5-card hand, 5 security, `drawn` more draws, then a reveal 3 that keeps one
    card and puts two on the bottom. Keep only the games that match the observation (outs seen
    in hand, draws and the kept card; outs on the bottom) and report how often the next `look`
    cards off the top hold an out. Security stays face down throughout."""
    matched = hits = 0
    for _ in range(games):
        cards = deal(rng, deck, {"a": copies})
        hand, rest = cards[:5] + cards[10:10 + drawn], cards[10 + drawn:]   # cards[5:10] is security
        reveal, rest = rest[:3], rest[3:]
        kept = reveal[0]                                      # which card you keep doesn't matter to the odds
        bottom = reveal[1:]
        rest = rest + bottom
        if (hand + [kept]).count("a") != seen_outs or bottom.count("a") != bottom_outs:
            continue
        matched += 1
        hits += "a" in rest[:look]
    return hits / matched, matched


class MidGame(unittest.TestCase):
    def test_find_matches_conditioned_simulation(self):
        rng = random.Random(4)
        for copies, drawn, seen_outs, bottom_outs, look in ((3, 4, 1, 1, 3), (4, 6, 0, 0, 5), (8, 2, 2, 1, 4)):
            sim, n = sim_midgame(rng, 200000, 50, copies, drawn, seen_outs, bottom_outs, look)
            deck_left = 50 - 10 - drawn - 3 + 2   # minus hand, security, draws, the reveal; plus the 2 bottomed
            exact = odds.p_find(deck_left, 5, 2, copies - seen_outs - bottom_outs, look)
            self.assertGreater(n, 5000)
            self.assertAlmostEqual(exact, sim, delta=0.015, msg=(copies, drawn, seen_outs, bottom_outs, look, n))

    def test_find_ignores_security_and_bottom_mistakes(self):
        # 1 unseen out, 28 in deck with 2 bottomed, 4 security, look at 3: 3 of the 30 unknown cards.
        self.assertAlmostEqual(odds.p_find(28, 4, 2, 1, 3), 3 / 30)
        # Looking past the cards above the bottom stops at them.
        self.assertAlmostEqual(odds.p_find(5, 0, 3, 1, 9), 1.0)
        self.assertEqual(odds.p_find(28, 4, 2, 0, 3), 0.0)

    def test_go_or_wait(self):
        self.assertAlmostEqual(odds.go_or_wait(0.35, 0.7, 0.8, 0.3), 0.7 * (0.35 * 0.8 + 0.65 * 0.3))
        self.assertAlmostEqual(odds.go_or_wait(1.0, 1.0, 0.8, 0.0), 0.8)


class Statistics(unittest.TestCase):
    def test_wilson_contains_the_rate_and_narrows(self):
        lo, hi = odds.wilson(6, 10)
        self.assertLess(lo, 0.6)
        self.assertGreater(hi, 0.6)
        lo2, hi2 = odds.wilson(60, 100)
        self.assertLess(hi2 - lo2, hi - lo)

    def test_p_favored_matches_numeric_integration(self):
        w, lo = 7, 3
        grid = 200000
        num = sum((i / grid) ** w * (1 - i / grid) ** lo for i in range(grid // 2, grid)) / grid
        den = sum((i / grid) ** w * (1 - i / grid) ** lo for i in range(grid)) / grid
        self.assertAlmostEqual(odds.p_favored(w, lo), num / den, places=3)
        self.assertAlmostEqual(odds.p_favored(0, 0), 0.5)

    def test_p_better_is_symmetric_and_sane(self):
        self.assertAlmostEqual(odds.p_better(5, 5, 5, 5), 0.5)
        self.assertGreater(odds.p_better(5, 5, 9, 1), 0.9)
        self.assertAlmostEqual(odds.p_better(9, 1, 5, 5) + odds.p_better(5, 5, 9, 1), 1.0)

    def test_games_needed(self):
        self.assertEqual(odds.games_needed(0.5, 0.6), 388)  # standard two-proportion result
        self.assertGreater(odds.games_needed(0.5, 0.55), odds.games_needed(0.5, 0.6))

    def test_bo3(self):
        self.assertAlmostEqual(odds.bo3(0.5), 0.5)
        self.assertAlmostEqual(odds.bo3(0.6), 0.648)
        self.assertGreater(odds.bo3(0.7), 0.7)
        self.assertLess(odds.bo3(0.3), 0.3)


if __name__ == "__main__":
    unittest.main()
