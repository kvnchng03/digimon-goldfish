# digimon-goldfish

A goldfish simulator for the Digimon Card Game, built for the Glowing Dawn (Tomoro / Kyo, Digimon Beatbreak) card pool.
It plays the deck thousands of times against an opponent who does nothing and reports how fast and how consistently the deck does its own job.

Everything is standard-library Python 3.12+.
No install step.

## Quick start

```sh
python3 -m goldfish                                   # 10,000 games, random first/second
python3 -m goldfish --first second --games 20000      # always on the draw
python3 -m goldfish --trace --seed 11                 # one game, turn by turn
python3 -m goldfish --compare --edit "BT26-089:+1,ST23-15:-1"   # 3rd Kyo for an e-Pulse
python3 -m unittest discover -s tests                 # the test suite
```

The decklist lives in `decks/glowing_dawn.txt` in the plain `count name id` format (alt-art suffixes like `_P1` are ignored).
`--deck` points at another file; `--edit` applies `ID:+N` / `ID:-N` changes without touching the file.

## Workbook and research tools

The [visual improvement guide](guide/README.md) is a TypeScript app with general strategy lessons, short drills, a weekly practice routine, and Glowing Dawn checklists, matchups and decision puzzles.
Use the **Improve** tab for skills that apply to any deck.
A GitHub Actions workflow builds, tests and deploys the guide to GitHub Pages, with phone installation and offline reading support.
See the [GitHub Pages and PWA setup](guide/README.md#deploy-with-github-pages) for deployment steps.
Run it with `cd guide && npm ci && npm run dev`, or open the [offline guide](.lavish/glowing-dawn-guide.html) after building.

The simulator itself needs nothing beyond the standard library.
The workbook and research tools use a project venv:

```sh
python3 -m venv .venv && .venv/bin/pip install openpyxl formulas ruff
.venv/bin/python tools/build_workbook.py              # reports/glowing-dawn-theorycraft.xlsx (~30 s, runs the sim live)
.venv/bin/python tools/build_player_workbook.py       # reports/digimon-player-math.xlsx (general player math) + creates reports/digimon-player-log.xlsx once (your log; never overwritten)
.venv/bin/python tools/check_workbook.py [PATH]       # recalculates every formula and checks results against Python; exit 1 on any problem
.venv/bin/python tools/check_workbook.py --render DIR # one PNG per sheet (macOS Quick Look) to eyeball layout
    [--recalc] [--scenario NAME]                      # ...with evaluated values, or after typing in a builder scenario
python3 tools/fetch_card_text.py BT24-101             # card text from the fandom wiki, cached in data/cardtext.json
python3 research/tools/fetch_transcripts.py fetch ID  # YouTube transcripts (needs youtube-transcript-api)
.venv/bin/ruff check .                                # lint (rules in pyproject.toml)
```

`tools/research_data.py` holds everything the workbook takes from the research notes in `research/`: opponent timings, real win rates, play rules and the per-matchup playbooks.
Every value carries an evidence tag (OBSERVED, STATED, INFERRED, COUNTED, SIM), so edit the data there and rebuild rather than editing the workbook.

`reports/digimon-player-math.xlsx` is the player workbook. Every calculator sheet has the same shape: the question it answers, the cells to fill in, the answer written out as a sentence, then the details. Sheets: Puzzles, Find my out, Quiz, Will I draw it, How many copies, Both cards, Memory plan, The race, Attack risk, Is my record real, Which deck, Key ideas, How to theorycraft, Practice, How it works.
Puzzles are Glowing Dawn decisions with one best play (mulligans, memory passes, attack order, removal, card choice, odds); the answer, why, rule and evidence appear once you type a pick.
They live in `tools/puzzles.py`, each tied to card text, the research notes or the simulator, with the same evidence tags as the theorycraft workbook; a puzzle only goes in when its evidence settles the answer.
Find my out is the mid-game calculator: odds of seeing an out from the current deck (face-down security counts as unknown, cards you bottomed don't), going all-in now versus waiting a turn, and whether they hold an answer.
Its math is `goldfish/odds.py`, tested against card-by-card simulation in `tests/test_player_math.py`, and `tools/check_workbook.py` compares every expected cell of the built file (and of a fresh log file) with Python, then types in the builder's scenarios (every puzzle right, every puzzle wrong, edge-case inputs) and checks those too.
The log file `reports/digimon-player-log.xlsx` (Game Log, My Results, Guess Log, Deck Notes) is created once and never overwritten unless you pass `--force-log`.

The workbook's Calculator sheet gives the odds for one attack turn: their security, what can stop you, and your attackers in order, against their real 50-card list.
Its formulas are generated from `goldfish/calc.py`, which is tested against a card-by-card simulation (`tests/test_calc.py`), and `tools/check_workbook.py` sets several situations on the sheet and checks every result cell against the Python model.

## What the report means

- **Kill turn**: the turn on which the sixth hit lands (five security cards plus one direct attack).
  `by turn` is cumulative.
- **Checks dealt**: mean cumulative security cards removed by the end of each turn.
- **First Lv6**: when a Lv6 first reaches the field (battle or breeding area).
- **Bricks**: no Lv3 digivolve on turn 1, no Tamer out by the end of turn 2, no Lv4 by the end of turn 3.
- **Engine usage**: how often the deck's signature plays actually happen per game.
  Kekkomon's attack-time digivolve, Arts Digivolves, and Cougarmon BT25-035's free chain.
- **Own security at game end**: how much of your own security the policy burned on Barrier-style costs.
  In a goldfish game that is free; in a real game it is not.

Every proportion carries sampling noise of roughly `sqrt(p(1-p)/n)`.
`--compare` prints that noise next to each delta.
A delta smaller than about twice the noise is not evidence of anything.

## What is modeled

All 22 cards in the list, with their printed text (transcribed from the Digimon Card Game wiki on 2026-10-06).
The DUAL card and Arts Digivolve rules follow Bandai's Comprehensive Rules (2026-09-18), sections 4-6 and 4-20.
The Monarchlizamon BT25-057 Option half uses the errata'd wording (+5000 DP for the turn only).

Specifically:

- Trait-route digivolution (0 / 2 / 3 / 3 within [Glowing Dawn]), the digivolution draw, [On Play] vs [When Digivolving] vs [When Moving] timing.
- Fuel: face-down cards under Tamers, every source and every sink in the list.
- Kekkomon's attack-time digivolve, Cougarmon ST23-03's stacking -2, Cougarmon BT25-035's free chain.
- DUAL cards used as Options with Armalizamon / Tomoro / Murasamemon / Cougarmon BT26-026 discounts, then Arts Digivolve.
- DUAL Lv5s have no inherited effect (their lower text is Option information), so a Lv6 on top of one does not get the end-of-attack unsuspend.
- Habakirimon's Recovery and "trash the top security of the player with the most" (ties go to the opponent's card).
- Alliance, Security Attack +1, Rush from the Monarchlizamon Option, once-per-turn tracking.
- Kyo's and Tomoro's triggers, e-Pulse's tuck, Glowing Dawn's Delay.
- Deck-out.

## What is not modeled (and why the numbers are optimistic)

The opponent is a goldfish.
It never plays a card, never attacks, never blocks, and its security never fights back.
Consequences:

- Nothing ever dies, so every board survives to the next turn.
- Security checks never delete your attacker, and no [Security] effect ever fires.
- Kyo's and Tomoro's "when the opponent attacks" triggers never happen, which understates your fuel.
- Effects that only touch the opponent's board (DP minus, suspend, delete, De-Digivolve, immunity) are no-ops.
- The opponent passes every turn, so you start each turn with 3 memory.
  To stop the policy from spending 10 memory a turn for free, it never hands the opponent more than `--max-give` memory (default 3, i.e. never worse than passing).
  Raise it to see how much speed overspending buys.
- The opponent is assumed to have a Digimon in its battle area from its second turn (`--opp-board-turn`), which is what drives Tomoro & Kyo's memory gain.

Goldfish numbers measure speed and consistency.
They say nothing about win rate against interaction.

## Arguing with the policy

All decisions live in `goldfish/policy.py`.
The engine (`goldfish/engine.py`) enforces rules and never chooses.
Run `--trace` on a seed, read the bracketed `[...]` lines (each is a policy decision), and change the heuristic you disagree with.
The main knobs:

- `breeding_phase`: when to move a Lv3 out.
- `TAMER_PRIO` / `EVO_PRIO`: what the development phase reaches for first.
- `tamer_reserve`: setup spending leaves room for a Tamer still in hand.
- `evo_pref`: which Lv4 / Lv5 / Lv6 to digivolve into when several are in hand.
- `plan_discounted_play`: what the Murasamemon / Monarchlizamon -3 trigger is spent on.
- `card_value`: what the reveal effects pick and what Kyo tucks.

## Layout

```
goldfish/cards.py     card data (costs, levels, colors, keywords)
goldfish/effects.py   every card effect, keyed by card id
goldfish/engine.py    rules: zones, costs, triggers, the turn loop
goldfish/policy.py    decisions
goldfish/sim.py       batch runner, summary, report, compare
goldfish/calc.py      exact odds for one attack turn into a real list's security (the workbook Calculator)
goldfish/odds.py      draw odds with a realistic redraw, two-card odds, mid-game outs, go-or-wait, Wilson / Bayesian record stats, games needed (the player workbook)
goldfish/__main__.py  CLI
decks/                decklists
tests/                unittest suite (engine rules, decklist parsing, hypergeometric sanity)
tools/                workbook builders + checker, research data, puzzles, card-text fetcher
research/             research notes (round 1 timings, round 2 playbooks), cached transcripts, fetch tool
reports/              generated workbook
```
