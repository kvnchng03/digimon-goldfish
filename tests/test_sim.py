import unittest
from pathlib import Path

from goldfish.decklist import apply_edits, parse_decklist
from goldfish.sim import compare, report, run, summarize, trace_game
from goldfish.state import Config

DECK = parse_decklist((Path(__file__).resolve().parent.parent / "decks" / "glowing_dawn.txt").read_text())


def has_lv3(ids):
    return any(DECK_CARDS[i].level == 3 for i in ids)


DECK_CARDS = {c.id: c for c in DECK.main}


class OpeningHandTests(unittest.TestCase):
    """The shuffle / draw / mulligan machinery must reproduce the hypergeometric numbers."""

    def test_opening_lv3_rate_without_mulligan(self):
        stats = run(DECK, 3000, seed=7, cfg=Config(mulligan=False, max_turns=1))
        rate = sum(has_lv3(s.opening_hand) for s in stats) / len(stats)
        self.assertAlmostEqual(rate, 0.689, delta=0.03)   # P(>=1 of 10 Lv3s in 5 of 50)

    def test_opening_lv3_rate_with_mulligan(self):
        stats = run(DECK, 3000, seed=8, cfg=Config(max_turns=1))
        rate = sum(has_lv3(s.opening_hand) for s in stats) / len(stats)
        self.assertAlmostEqual(rate, 0.904, delta=0.025)  # 1 - (1 - 0.689)^2


class ReportTests(unittest.TestCase):
    def test_summary_and_report_run(self):
        cfg = Config()
        stats = run(DECK, 100, seed=3, cfg=cfg)
        s = summarize(stats, cfg)
        text = report(s, "smoke")
        self.assertIn("Kill turn", text)
        self.assertEqual(s.games, 100)
        self.assertTrue(0.0 <= s.kill_by[5] <= 1.0)

    def test_compare_runs(self):
        cfg = Config()
        a = summarize(run(DECK, 50, seed=1, cfg=cfg), cfg)
        b = summarize(run(apply_edits(DECK, "BT26-089:+1,ST23-15:-1"), 50, seed=1, cfg=cfg), cfg)
        self.assertIn("kill by T5", compare(a, b))

    def test_trace_produces_a_log(self):
        log, stats = trace_game(DECK, seed=5)
        self.assertTrue(any("turn 1" in line for line in log))
        self.assertGreaterEqual(stats.turns_played, 1)


if __name__ == "__main__":
    unittest.main()
