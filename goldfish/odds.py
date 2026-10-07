"""Exact odds behind the player-math workbook (any deck): before the game (draw odds with a
realistic redraw) and during it (finding an out from the current deck, whether they hold an
answer, going all-in now versus waiting a turn).

Pure functions. tests/test_player_math.py checks them against card-by-card simulation,
and tools/check_workbook.py checks the Excel formulas against them.

Game facts used (Comprehensive Rules 2026-09-18): the opening hand is 5 cards and each
player may redraw it once, shuffling the whole hand back (5-2-1-4/5); security is the next
5 cards, face down (5-2-1-6); the first player skips the draw on their first turn
(6-3-1-1); digivolving draws 1 card.
"""

from __future__ import annotations

import math

OPENING = 5


def p_at_least(deck: int, copies: int, seen: int, k: int = 1) -> float:
    """Chance that at least k of `copies` are among `seen` random cards of `deck` (hypergeometric)."""
    seen = min(seen, deck)
    if k <= 0:
        return 1.0
    miss = sum(math.comb(copies, i) * math.comb(deck - copies, seen - i) for i in range(min(k, copies + 1)))
    return 1 - miss / math.comb(deck, seen)


def p_by_n(deck: int, copies: int, seen: int, k: int = 1, redraw: bool = True) -> float:
    """Chance to have at least k copies once you've seen `seen` cards (opening hand included).

    With `redraw`, you shuffle back an opening hand that has NONE of them and keep any hand
    that has one; the redrawn hand is a fresh deal. That is how players mulligan for a key
    card. The result is p_n + p0 * (p_n - q_n): kept hands that get there, plus redrawn
    hands as a fresh deal. For k = 1 it reduces to 1 - (1 - p5)(1 - p_n).
    """
    pn = p_at_least(deck, copies, seen, k)
    if not redraw or seen < OPENING:
        return pn
    p0 = math.comb(deck - copies, OPENING) / math.comb(deck, OPENING)  # opening has none
    qn = p_at_least(deck - OPENING, copies, seen - OPENING, k)  # the rest of the deck after such an opening
    return pn + p0 * (pn - qn)


def p_both(deck: int, a: int, b: int, seen: int) -> float:
    """At least one of group A and at least one of group B among `seen` cards (the groups don't overlap)."""
    seen = min(seen, deck)
    rest = math.comb(max(deck - a - b, 0), seen)
    return 1 - (math.comb(deck - a, seen) + math.comb(deck - b, seen) - rest) / math.comb(deck, seen)


def p_both_by_n(deck: int, a: int, b: int, seen: int, redraw: bool = True) -> float:
    """Both groups once you've seen `seen` cards, redrawing only an opening hand with no A
    (A is the card you mulligan for; a hand with A but no B is kept)."""
    pn = p_both(deck, a, b, seen)
    if not redraw or seen < OPENING:
        return pn
    c5 = math.comb(deck, OPENING)
    pa0 = math.comb(deck - a, OPENING) / c5  # opening: no A
    p00 = math.comb(max(deck - a - b, 0), OPENING) / c5  # opening: neither
    m = seen - OPENING
    qa = 1 - math.comb(deck - OPENING - a, m) / math.comb(deck - OPENING, m)  # A among the next m
    qab = p_both(deck - OPENING, a, b, m)  # both among the next m
    # kept hands (have A) that reach both  +  redrawn hands (no A) as a fresh deal
    return (pn - ((pa0 - p00) * qa + p00 * qab)) + pa0 * pn


def cards_seen(turn: int, first: bool, extra: float, deck: int) -> int:
    """Cards seen by the end of your own turn `turn`: the opening 5, one draw per turn (none on
    the first player's turn 1) and `extra` per turn (digivolve draws, searches). Capped at the
    deck minus the 5 security cards."""
    return int(min(OPENING + (turn - 1 if first else turn) + extra * turn, deck - OPENING))


def p_find(deck_left: int, security: int, bottom: int, outs: int, seen: int, k: int = 1) -> float:
    """Mid-game: chance that at least k of your `outs` are among the next `seen` cards you look at.

    `outs` counts only copies you have not seen anywhere (hand, trash, board, under Tamers,
    the bottom of the deck). The cards you don't know are the deck above the `bottom` cards
    you put there yourself, plus your face-down security: from where you sit those are one
    shuffled pile, so an out is as likely to be in security as on top of the deck. The
    bottom cards are known and out of reach, so `seen` stops at the deck above them.
    """
    reachable = max(deck_left - bottom, 0)
    return p_at_least(reachable + security, outs, min(seen, reachable), k)


def go_or_wait(p_find_by_next: float, survive: float, win_with: float, win_without: float) -> float:
    """Chance to win if you hold back a turn: survive their turn, then win with or without the out."""
    return survive * (p_find_by_next * win_with + (1 - p_find_by_next) * win_without)


def wilson(wins: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for a win rate."""
    p = wins / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def p_favored(wins: int, losses: int, threshold: float = 0.5) -> float:
    """Chance the true win rate is above `threshold`, assuming you knew nothing beforehand
    (uniform prior): the Beta(w+1, l+1) tail, which for whole numbers is a binomial sum."""
    # P(Beta(a, b) <= x) = P(Binomial(a + b - 1, x) >= a), so P(p > x) = P(Binomial(w + l + 1, x) <= w)
    n = wins + losses + 1
    return sum(math.comb(n, i) * threshold**i * (1 - threshold) ** (n - i) for i in range(wins + 1))


def p_better(wins_a: int, losses_a: int, wins_b: int, losses_b: int) -> float:
    """Chance B's true win rate is above A's (normal approximation to the two Beta posteriors)."""

    def mean_var(w, lo):
        a, b = w + 1, lo + 1
        return a / (a + b), a * b / ((a + b) ** 2 * (a + b + 1))

    ma, va = mean_var(wins_a, losses_a)
    mb, vb = mean_var(wins_b, losses_b)
    zscore = (mb - ma) / math.sqrt(va + vb)
    return 0.5 * (1 + math.erf(zscore / math.sqrt(2)))


def games_needed(p1: float, p2: float) -> int:
    """Games per version to tell win rate p1 from p2 (95% confidence, 80% power)."""
    pbar = (p1 + p2) / 2
    num = 1.96 * math.sqrt(2 * pbar * (1 - pbar)) + 0.8416 * math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    return math.ceil(num**2 / (p2 - p1) ** 2)


def bo3(p: float) -> float:
    """Match win rate in a best of 3 from a game win rate (games independent)."""
    return p * p * (3 - 2 * p)
