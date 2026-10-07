"""Run many goldfish games and summarize them."""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass, field

from .decklist import Deck
from .engine import Game
from .policy import Policy
from .state import Config, GameStats

FIRST_MODES = ("random", "first", "second")


def _going_first(mode: str, rng: random.Random) -> bool:
    if mode == "random":
        return rng.random() < 0.5
    return mode == "first"


def run(deck: Deck, games: int, seed: int = 1, cfg: Config | None = None, first: str = "random",
        policy: Policy | None = None) -> list[GameStats]:
    cfg = cfg or Config()
    policy = policy or Policy()
    rng = random.Random(seed)
    out: list[GameStats] = []
    for _ in range(games):
        g = Game(deck, policy, random.Random(rng.getrandbits(64)), _going_first(first, rng), cfg)
        out.append(g.play())
    return out


def trace_game(deck: Deck, seed: int = 1, cfg: Config | None = None, first: str = "random",
               policy: Policy | None = None) -> tuple[list[str], GameStats]:
    rng = random.Random(seed)
    g = Game(deck, policy or Policy(), random.Random(rng.getrandbits(64)), _going_first(first, rng),
             cfg or Config(), trace=True)
    stats = g.play()
    return g.log, stats


# ---------------------------------------------------------------------- summary
@dataclass
class Summary:
    games: int
    max_turns: int
    kill_by: dict[int, float] = field(default_factory=dict)
    kill_mean: float | None = None
    kill_median: float | None = None
    no_kill: float = 0.0
    deck_out: float = 0.0
    lv6_by: dict[int, float] = field(default_factory=dict)
    brick_no_lv3_t1: float = 0.0
    no_tamer_by_t2: float = 0.0
    no_lv4_by_t3: float = 0.0
    checks_by: dict[int, float] = field(default_factory=dict)
    tricks: float = 0.0
    arts: float = 0.0
    free_chains: float = 0.0
    fuel_at_lv6: float | None = None
    memory_given: float = 0.0
    security_at_end: float = 0.0
    mulligan_rate: float = 0.0
    lv6_on_dual_base: float | None = None
    setup: dict[int, dict[str, float]] = field(default_factory=dict)   # board by end of turn
    split: dict[str, dict[str, float | None]] = field(default_factory=dict)


def _rate(xs: list[bool]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _mean(xs: list[float]) -> float | None:
    return statistics.fmean(xs) if xs else None


def summarize(stats: list[GameStats], cfg: Config | None = None) -> Summary:
    cfg = cfg or Config()
    n = len(stats)
    s = Summary(games=n, max_turns=cfg.max_turns)
    kills = [x.kill_turn for x in stats if x.kill_turn is not None]
    for t in range(3, cfg.max_turns + 1):
        s.kill_by[t] = _rate([x.kill_turn is not None and x.kill_turn <= t for x in stats])
        s.lv6_by[t] = _rate([x.first_level_turn.get(6, 99) <= t for x in stats])
        s.checks_by[t] = statistics.fmean(x.checks_at_end_of(t) for x in stats)
    s.kill_mean = _mean(kills)
    s.kill_median = statistics.median(kills) if kills else None
    s.no_kill = _rate([x.kill_turn is None for x in stats])
    s.deck_out = _rate([x.deck_out_turn is not None for x in stats])
    s.brick_no_lv3_t1 = _rate([x.first_level_turn.get(3) != 1 for x in stats])
    s.no_tamer_by_t2 = _rate([x.first_tamer_turn is None or x.first_tamer_turn > 2 for x in stats])
    s.no_lv4_by_t3 = _rate([x.first_level_turn.get(4, 99) > 3 for x in stats])
    s.tricks = statistics.fmean(x.kekkomon_tricks for x in stats)
    s.arts = statistics.fmean(x.arts_digivolves for x in stats)
    s.free_chains = statistics.fmean(x.free_digivolves for x in stats)
    s.fuel_at_lv6 = _mean([x.fuel_at_first_lv6 for x in stats if x.fuel_at_first_lv6 is not None])
    given = [m for x in stats for m in x.memory_given]
    s.memory_given = statistics.fmean(given) if given else 0.0
    s.security_at_end = statistics.fmean(x.security_at_end for x in stats)
    s.mulligan_rate = _rate([x.mulliganed for x in stats])
    bases = [x.lv6_base_dual for x in stats if x.lv6_base_dual is not None]
    s.lv6_on_dual_base = _rate(bases) if bases else None
    for t in range(1, min(6, cfg.max_turns) + 1):
        tamers = [GameStats.at_end_of(x.tamers_by_turn, t) or 0 for x in stats]
        fuel = [GameStats.at_end_of(x.fuel_by_turn, t) or 0 for x in stats]
        top = [GameStats.at_end_of(x.top_level_by_turn, t) or 0 for x in stats]
        s.setup[t] = {
            "tamers1": _rate([v >= 1 for v in tamers]),
            "tamers2": _rate([v >= 2 for v in tamers]),
            "fuel_mean": statistics.fmean(fuel),
            "fuel3": _rate([v >= 3 for v in fuel]),
            "top4": _rate([v >= 4 for v in top]),
            "top5": _rate([v >= 5 for v in top]),
            "top6": _rate([v >= 6 for v in top]),
        }
    for label, flag in (("first", True), ("second", False)):
        part = [x for x in stats if x.going_first == flag]
        if not part:
            continue
        pk = [x.kill_turn for x in part if x.kill_turn is not None]
        s.split[label] = {
            "games": len(part),
            "kill_mean": _mean(pk),
            "kill_by_5": _rate([x.kill_turn is not None and x.kill_turn <= 5 for x in part]),
            "lv6_by_4": _rate([x.first_level_turn.get(6, 99) <= 4 for x in part]),
        }
    return s


def _se(p: float, n: int) -> float:
    return math.sqrt(max(p * (1 - p), 0.0) / n) if n else 0.0


def _pct(p: float | None) -> str:
    return "  n/a" if p is None else f"{100 * p:5.1f}%"


def _num(x: float | None, nd: int = 2) -> str:
    return " n/a" if x is None else f"{x:.{nd}f}"


def report(s: Summary, title: str = "") -> str:
    lines: list[str] = []
    if title:
        lines.append(title)
    turns = [t for t in sorted(s.kill_by) if t <= min(8, s.max_turns)]
    lines.append(f"games: {s.games}   (proportions carry about ±{100 * _se(0.5, s.games):.1f} pts of noise)")
    lines.append("")
    lines.append("Kill turn (6 hits: 5 security + 1 direct)")
    lines.append("  by turn:   " + "  ".join(f"T{t}" for t in turns))
    lines.append("             " + "  ".join(_pct(s.kill_by[t]).strip().rjust(len(f"T{t}") + 4) for t in turns))
    lines.append(f"  mean {_num(s.kill_mean)}   median {_num(s.kill_median, 1)}"
                 f"   no kill by T{s.max_turns}: {_pct(s.no_kill).strip()}"
                 f"   deck-out: {_pct(s.deck_out).strip()}")
    lines.append("")
    lines.append("Checks dealt (cumulative, mean)")
    lines.append("  end of:    " + "  ".join(f"T{t}" for t in turns))
    lines.append("             " + "  ".join(f"{s.checks_by[t]:.2f}".rjust(len(f"T{t}") + 4) for t in turns))
    lines.append("")
    lines.append("First Lv6 on the field")
    lines.append("  by turn:   " + "  ".join(f"T{t}" for t in turns[:4]))
    lines.append("             " + "  ".join(_pct(s.lv6_by[t]).strip().rjust(len(f"T{t}") + 4) for t in turns[:4]))
    if s.setup:
        turns_s = sorted(s.setup)
        lines.append("")
        lines.append("Board by end of turn (a finished game keeps its final board)")
        lines.append("  " + "turn".ljust(14) + "".join(f"T{t}".rjust(8) for t in turns_s))
        for label, key, fmt in (("1+ Tamers", "tamers1", "pct"), ("2+ Tamers", "tamers2", "pct"),
                                ("fuel (mean)", "fuel_mean", "num"), ("fuel >= 3", "fuel3", "pct"),
                                ("Lv4+ out", "top4", "pct"), ("Lv5+ out", "top5", "pct"), ("Lv6 out", "top6", "pct")):
            cells = [f"{100 * s.setup[t][key]:.0f}%" if fmt == "pct" else f"{s.setup[t][key]:.1f}" for t in turns_s]
            lines.append("  " + label.ljust(14) + "".join(c.rjust(8) for c in cells))
        if s.lv6_on_dual_base is not None:
            lines.append("  first Lv6 placed on a DUAL Lv5 (no inherited unsuspend): "
                         + _pct(s.lv6_on_dual_base).strip())
    lines.append("")
    lines.append("Bricks")
    lines.append(f"  no Lv3 digivolve on turn 1: {_pct(s.brick_no_lv3_t1).strip()}"
                 f"   (mulliganed {_pct(s.mulligan_rate).strip()})")
    lines.append(f"  no Tamer by end of turn 2:  {_pct(s.no_tamer_by_t2).strip()}")
    lines.append(f"  no Lv4 by end of turn 3:    {_pct(s.no_lv4_by_t3).strip()}")
    lines.append("")
    lines.append("Engine usage per game")
    lines.append(f"  Kekkomon attack-time digivolves {_num(s.tricks)}   Arts Digivolves {_num(s.arts)}"
                 f"   Cougarmon BT25 free chains {_num(s.free_chains)}")
    lines.append(f"  fuel at the start of the first Lv6 turn: {_num(s.fuel_at_lv6, 1)}"
                 f"   memory handed over per turn: {_num(s.memory_given)}"
                 f"   own security at game end: {_num(s.security_at_end, 1)}")
    if s.split:
        lines.append("")
        lines.append("Going first vs second")
        for label, d in s.split.items():
            lines.append(f"  {label:<6} games {int(d['games']):>5}   kill mean {_num(d['kill_mean'])}"
                         f"   kill by T5 {_pct(d['kill_by_5']).strip()}   Lv6 by T4 {_pct(d['lv6_by_4']).strip()}")
    return "\n".join(lines)


def compare(a: Summary, b: Summary, label_a: str = "baseline", label_b: str = "edited") -> str:
    """Side-by-side of the numbers that matter, with the noise floor stated."""
    rows: list[tuple[str, float | None, float | None, bool]] = []
    for t in (4, 5, 6, 7):
        if t in a.kill_by:
            rows.append((f"kill by T{t}", a.kill_by[t], b.kill_by[t], True))
    rows.append(("kill turn mean", a.kill_mean, b.kill_mean, False))
    rows.append(("no kill", a.no_kill, b.no_kill, True))
    for t in (4, 5):
        rows.append((f"Lv6 by T{t}", a.lv6_by[t], b.lv6_by[t], True))
    for t in (4, 5):
        rows.append((f"checks by T{t}", a.checks_by[t], b.checks_by[t], False))
    rows.append(("no Lv3 turn 1", a.brick_no_lv3_t1, b.brick_no_lv3_t1, True))
    rows.append(("no Tamer by T2", a.no_tamer_by_t2, b.no_tamer_by_t2, True))
    if 3 in a.setup and 3 in b.setup:
        rows.append(("2+ Tamers by T3", a.setup[3]["tamers2"], b.setup[3]["tamers2"], True))
        rows.append(("fuel>=3 by T3", a.setup[3]["fuel3"], b.setup[3]["fuel3"], True))
    rows.append(("deck-out", a.deck_out, b.deck_out, True))
    rows.append(("tricks / game", a.tricks, b.tricks, False))
    rows.append(("Arts / game", a.arts, b.arts, False))
    out = [f"{'metric':<18}{label_a:>12}{label_b:>12}{'delta':>10}{'noise':>9}"]
    for name, x, y, is_pct in rows:
        if x is None or y is None:
            out.append(f"{name:<18}{'n/a':>12}{'n/a':>12}")
            continue
        if is_pct:
            noise = math.sqrt(_se(x, a.games) ** 2 + _se(y, b.games) ** 2) * 100
            out.append(f"{name:<18}{100 * x:>11.1f}%{100 * y:>11.1f}%{100 * (y - x):>+9.1f}%{noise:>7.1f}pt")
        else:
            out.append(f"{name:<18}{x:>12.2f}{y:>12.2f}{y - x:>+10.2f}")
    out.append("")
    out.append("A delta smaller than about twice the noise column is not evidence of anything.")
    return "\n".join(out)
