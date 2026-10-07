"""Command line entry point: python -m goldfish [options]."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .decklist import apply_edits, parse_decklist
from .sim import FIRST_MODES, compare, report, run, summarize, trace_game
from .state import Config

DEFAULT_DECK = Path(__file__).resolve().parent.parent / "decks" / "glowing_dawn.txt"


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="goldfish", description="Goldfish simulator for the Glowing Dawn deck.")
    p.add_argument("--deck", type=Path, default=DEFAULT_DECK, help="decklist file (count name id per line)")
    p.add_argument("--games", type=int, default=10000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--first", choices=FIRST_MODES, default="random", help="who goes first")
    p.add_argument("--edit", default="", help='card edits, e.g. "BT26-089:+1,ST23-15:-1"')
    p.add_argument("--compare", action="store_true", help="run the deck with and without --edit and diff them")
    p.add_argument("--trace", action="store_true", help="print one game turn by turn instead of a summary")
    p.add_argument("--max-give", type=int, default=3, help="never hand the opponent more memory than this")
    p.add_argument("--max-turns", type=int, default=10)
    p.add_argument("--min-security", type=int, default=2, help="keep at least this much security when spending it")
    p.add_argument("--opp-board-turn", type=int, default=2,
                   help="the opponent has a battle-area Digimon from this many of its turns on")
    p.add_argument("--no-mulligan", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg = Config(max_give=args.max_give, max_turns=args.max_turns, min_security=args.min_security,
                 opp_board_turn=args.opp_board_turn, mulligan=not args.no_mulligan)
    deck = parse_decklist(args.deck.read_text())
    edited = apply_edits(deck, args.edit) if args.edit else None

    if args.trace:
        log, stats = trace_game(edited or deck, args.seed, cfg, args.first)
        print("\n".join(log))
        print()
        print(f"result: kill turn {stats.kill_turn}, deck-out turn {stats.deck_out_turn}, "
              f"checks {stats.checks}, tricks {stats.kekkomon_tricks}, arts {stats.arts_digivolves}")
        return 0

    settings = (f"games={args.games} seed={args.seed} first={args.first} max_give={cfg.max_give} "
                f"max_turns={cfg.max_turns} min_security={cfg.min_security} opp_board_turn={cfg.opp_board_turn}")
    if args.compare:
        if edited is None:
            print("--compare needs --edit", file=sys.stderr)
            return 2
        a = summarize(run(deck, args.games, args.seed, cfg, args.first), cfg)
        b = summarize(run(edited, args.games, args.seed, cfg, args.first), cfg)
        print(settings)
        print(f"edit: {args.edit}")
        print()
        print(compare(a, b))
        return 0

    target = edited or deck
    print(settings + (f" edit={args.edit}" if args.edit else ""))
    print()
    print(report(summarize(run(target, args.games, args.seed, cfg, args.first), cfg)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
