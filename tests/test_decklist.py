import unittest
from pathlib import Path

from goldfish.decklist import apply_edits, parse_decklist

DECK_FILE = Path(__file__).resolve().parent.parent / "decks" / "glowing_dawn.txt"


class DecklistTests(unittest.TestCase):
    def test_parses_the_glowing_dawn_list(self):
        deck = parse_decklist(DECK_FILE.read_text())
        self.assertEqual(len(deck.main), 50)
        self.assertEqual(len(deck.eggs), 4)
        counts = deck.counts()
        self.assertEqual(counts["BT26-031"], 2)      # "_P1" alt-art suffix is stripped
        self.assertEqual(counts["ST23-13"], 4)
        self.assertEqual(sum(1 for c in deck.main if c.level == 3), 10)
        self.assertEqual(sum(1 for c in deck.main if c.level == 6), 6)
        self.assertEqual(sum(1 for c in deck.main if c.is_tamer), 8)

    def test_edits_add_and_remove(self):
        deck = parse_decklist(DECK_FILE.read_text())
        edited = apply_edits(deck, "BT26-089:+1, ST23-15:-1")
        self.assertEqual(len(edited.main), 50)
        self.assertEqual(edited.counts()["BT26-089"], 3)
        self.assertEqual(edited.counts()["ST23-15"], 3)
        self.assertEqual(deck.counts()["ST23-15"], 4)   # the original is untouched

    def test_rejects_illegal_decks(self):
        deck = parse_decklist(DECK_FILE.read_text())
        with self.assertRaises(ValueError):
            apply_edits(deck, "BT26-089:+1")               # 51 cards
        with self.assertRaises(ValueError):
            apply_edits(deck, "ST23-13:+1,ST23-15:-1")     # 5 copies
        with self.assertRaises(ValueError):
            parse_decklist("4 Nobodymon XX99-001\n")


if __name__ == "__main__":
    unittest.main()
