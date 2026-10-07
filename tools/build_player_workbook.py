"""Build the general Digimon TCG player-math workbook (any deck), and your personal log.

    python3 tools/build_player_workbook.py [--out reports/digimon-player-math.xlsx]
                                           [--log reports/digimon-player-log.xlsx] [--force-log]

Two files:
- the workbook: calculators, quiz and guides. Rebuilt every run; don't type into it.
- the log: your game log, results, guess log and deck notes. Created only if it doesn't
  exist (--force-log overwrites), so your entries survive rebuilds.

Every calculator sheet has the same shape: the question it answers, the cells to fill in,
the answer written out as a sentence, then the details. The math lives in goldfish/odds.py
(tested against card-by-card simulation); EXPECT maps cells to the values Python computes
for the default inputs and tools/check_workbook.py compares them after recalculating.
"""

from __future__ import annotations

import argparse
import datetime as dt
import math
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from puzzles import LETTERS, puzzles  # noqa: E402
from xlsx_style import (  # noqa: E402
    F_BASE,
    F_BOLD,
    F_INPUT,
    F_LINK,
    F_NOTE,
    FILL_KEY,
    NUM2,
    PCT,
    finalize,
    header,
    link,
    note,
    put,
    row_height,
    text_lines,
    title,
    widths,
)

from goldfish import odds  # noqa: E402

EXPECT: dict[str, object] = {}  # "SHEET!CELL" -> value, for both files
# (name, {"Sheet!CELL": value to type}, {"SHEET!CELL": expected value}): situations
# tools/check_workbook.py types into the built workbook before recalculating.
SCENARIOS: list[tuple[str, dict[str, object], dict[str, object]]] = []
K_MAX = 4  # "at least k" supports k up to 4
LOG_ROWS = 500
CAUSES = ["Draw", "Misplay", "Matchup", "Flip", "Other"]
SKILLS = ["Draw odds", "Memory", "Race", "Attack risk", "Record", "Deck choice"]

# Sheet names: plain questions, so the tabs read like a menu.
S = dict(puzzles="Puzzles", out="Find my out", quiz="Quiz", draw="Will I draw it", copies="How many copies",
         both="Both cards", memory="Memory plan", race="The race", risk="Attack risk", record="Is my record real",
         deck="Which deck", ideas="Key ideas", method="How to theorycraft", practice="Practice", how="How it works")
KEY = "Puzzle key"  # hidden: the answers
LOG = dict(games="Game Log", results="My Results", guesses="Guess Log", notes="Deck Notes")


# ---------------------------------------------------------------------- Excel versions of goldfish.odds
def xl_comb(n: str, k: str) -> str:
    """COMBIN that returns 0 instead of an error when k > n or k < 0 (like math.comb)."""
    return f"(IF(AND(({n})>=({k}),({k})>=0),1,0)*COMBIN(MAX({n},{k},0),MAX({k},0)))"


def xl_at_least(deck: str, copies: str, seen: str, k: str) -> str:
    miss = "+".join(f"IF({i}<({k}),1,0)*{xl_comb(copies, str(i))}*{xl_comb(f'({deck})-({copies})', f'({seen})-{i}')}"
                    for i in range(K_MAX))
    return f"(1-({miss})/COMBIN({deck},{seen}))"


def xl_by_n(deck: str, copies: str, seen: str, k: str, redraw: str) -> str:
    """odds.p_by_n: redraw an opening hand with none, keep one with any."""
    pn = xl_at_least(deck, copies, seen, k)
    p0 = f"({xl_comb(f'({deck})-({copies})', '5')}/COMBIN({deck},5))"
    qn = xl_at_least(f"({deck})-5", copies, f"({seen})-5", k)
    return f'IF({redraw}="Y",{pn}+{p0}*({pn}-{qn}),{pn})'


def xl_both(deck: str, a: str, b: str, seen: str) -> str:
    return (f"(1-({xl_comb(f'({deck})-({a})', seen)}+{xl_comb(f'({deck})-({b})', seen)}"
            f"-{xl_comb(f'({deck})-({a})-({b})', seen)})/COMBIN({deck},{seen}))")


def xl_both_by_n(deck: str, a: str, b: str, seen: str, redraw: str) -> str:
    """odds.p_both_by_n: redraw only an opening hand with no A."""
    pn = xl_both(deck, a, b, seen)
    pa0 = f"({xl_comb(f'({deck})-({a})', '5')}/COMBIN({deck},5))"
    p00 = f"({xl_comb(f'({deck})-({a})-({b})', '5')}/COMBIN({deck},5))"
    m = f"(({seen})-5)"
    qa = f"(1-{xl_comb(f'({deck})-5-({a})', m)}/COMBIN(({deck})-5,{m}))"
    qab = xl_both(f"({deck})-5", a, b, m)
    return f'IF({redraw}="Y",({pn}-(({pa0}-{p00})*{qa}+{p00}*{qab}))+{pa0}*{pn},{pn})'


def xl_wilson(w: str, n: str) -> tuple[str, str]:
    p, z = f"({w}/{n})", "1.96"
    centre = f"(({p}+{z}^2/(2*{n}))/(1+{z}^2/{n}))"
    half = f"({z}*SQRT({p}*(1-{p})/{n}+{z}^2/(4*{n}^2))/(1+{z}^2/{n}))"
    return f"{centre}-{half}", f"{centre}+{half}"


def xl_favored(w: str, lo: str) -> str:
    return f"BINOM.DIST({w},{w}+{lo}+1,0.5,TRUE)"


def xl_better(wa: str, la: str, wb: str, lb: str) -> str:
    def mv(w, lo):
        return f"(({w}+1)/({w}+{lo}+2))", f"(({w}+1)*({lo}+1)/(({w}+{lo}+2)^2*({w}+{lo}+3)))"

    ma, va = mv(wa, la)
    mb, vb = mv(wb, lb)
    return f"NORM.S.DIST(({mb}-{ma})/SQRT({va}+{vb}),TRUE)"


def xl_games_needed(p1: str, p2: str) -> str:
    pbar = f"(({p1}+{p2})/2)"
    num = f"(1.96*SQRT(2*{pbar}*(1-{pbar}))+0.8416*SQRT({p1}*(1-{p1})+{p2}*(1-{p2})))"
    return f"ROUNDUP({num}^2/({p2}-{p1})^2,0)"


def pct(cell: str) -> str:
    return f'TEXT({cell},"0%")'


# ---------------------------------------------------------------------- sheet helpers
def expect(ws, cell: str, value) -> None:
    EXPECT[f"{ws.title}!{cell}".upper()] = value


def inputs(ws, row: int, rows: list[tuple], span: int = 3) -> dict[str, str]:
    """A 'Fill in' block; returns {key: absolute cell ref}."""
    header(ws, row, 1, ["Fill in", "Value", ""] + [""] * (span - 1))
    ws.merge_cells(start_row=row, start_column=3, end_row=row, end_column=2 + span)
    refs = {}
    for i, (key, label, value, hint) in enumerate(rows):
        r = row + 1 + i
        put(ws, r, 1, label, F_BOLD, wrap=True)
        put(ws, r, 2, value, F_INPUT, align="left", fmt=PCT if isinstance(value, float) and value < 1 else None)
        put(ws, r, 3, hint, F_NOTE, wrap=True)
        ws.merge_cells(start_row=r, start_column=3, end_row=r, end_column=2 + span)
        refs[key] = f"$B${r}"
    return refs


def validate(ws, cells: str, kind: str, lo=None, hi=None, options: str | None = None) -> None:
    if kind == "list":
        dv = DataValidation(type="list", formula1=f'"{options}"', allow_blank=True)
    else:
        dv = DataValidation(type=kind, operator="between", formula1=str(lo), formula2=str(hi), allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(cells)


def section(ws, row: int, text: str, last_col: int = 5) -> None:
    header(ws, row, 1, [text] + [""] * (last_col - 1))
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)


def answer(ws, row: int, formula: str, last_col: int = 5) -> None:
    """A shaded sentence that reads the result back in words."""
    put(ws, row, 1, formula, F_BOLD, fill=FILL_KEY, wrap=True, align="left")
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
    ws.row_dimensions[row].height = 30


def notes(ws, row: int, lines: list[str], last_col: int = 5) -> int:
    section(ws, row, "Good to know", last_col)
    for text in lines:
        row += 1
        put(ws, row, 1, text, F_NOTE, wrap=True)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=last_col)
    return row


# ---------------------------------------------------------------------- start here
MENU = [
    ("puzzles", "What is the best play here? Glowing Dawn situations, with the answer and why."),
    ("out", "Mid-game: will I find my out, should I wait for it, do they hold their answer?"),
    ("quiz", "How good are my instincts?"),
    ("draw", "Will I have this card by a certain turn?"),
    ("copies", "How many copies do I need to run?"),
    ("both", "Will I have both cards I need?"),
    ("memory", "Where does my turn end, and what do they start with?"),
    ("race", "Who kills first if we both just attack?"),
    ("risk", "What can their security do to my attacker?"),
    ("record", "Does my win-loss record mean anything yet?"),
    ("deck", "Which deck gives me the best shot at this field?"),
    ("ideas", "What do strong players count?"),
    ("method", "How do I break down a deck or a matchup?"),
    ("practice", "What do I practice, and how often?"),
    ("how", "What rules and math is this built on?"),
]


def sheet_start(wb, stamp, log_name):
    ws = wb.active
    ws.title = "Start Here"
    title(ws, "Digimon TCG player math", f"Practice decisions and see yourself improve. Puzzles are for Glowing Dawn; the calculators work for any deck. Built {stamp}.")
    r = 4
    header(ws, r, 1, ["Start with these", "Why", ""])
    for key, why in (("puzzles", "Real situations with one best play. Pick, then read why and the rule behind it."),
                     ("out", "During a game: will your out show up in time, and is waiting a turn worth it?"),
                     ("memory", "Plan a turn so you don't hand the opponent a free one.")):
        r += 1
        link(ws, r, 1, S[key])
        put(ws, r, 2, why, wrap=True)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
    r += 2
    header(ws, r, 1, ["All sheets", "The question it answers", ""])
    for key, q in MENU:
        r += 1
        link(ws, r, 1, S[key])
        put(ws, r, 2, q)
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
    r += 2
    section(ws, r, "Your log file", 3)
    for text in (f"{log_name} is next to this file. Log your games there; it works out your win rates and why you lose.",
                 "It is never overwritten, so your entries are safe."):
        r += 1
        put(ws, r, 1, text, wrap=True)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    r += 2
    section(ws, r, "How to read a sheet", 3)
    for text, font, fill in (("Blue text: type here. Every sheet has example numbers in it; change them to your own.", F_INPUT, None),
                             ("Shaded: the answer, written out in words.", F_BOLD, FILL_KEY),
                             ("Gray italic: extra detail you can skip.", F_NOTE, None)):
        r += 1
        put(ws, r, 1, text, font, fill=fill)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    widths(ws, {"A": 26, "B": 70, "C": 12})


# ---------------------------------------------------------------------- calculators
def sheet_draw(wb):
    ws = wb.create_sheet(S["draw"])
    title(ws, "Will I draw it", "Chance to have a card, or any card from a group, by the end of a turn.")
    d = dict(deck=50, copies=4, k=1, extra=1, mull="Y")
    ref = inputs(ws, 4, [
        ("deck", "Deck size", d["deck"], "main deck, without Digi-Eggs"),
        ("copies", "Copies of the card", d["copies"], "one card is at most 4; for a job, use the group, like all 8 Tamers"),
        ("k", "How many you need", d["k"], "1 to 4"),
        ("extra", "Extra cards seen per turn", d["extra"], "digivolve draws and searches; usually 1"),
        ("mull", "Redraw a hand with none", d["mull"], "Y or N; you keep a hand that has one"),
    ])
    validate(ws, ref["mull"].replace("$", ""), "list", options="Y,N")
    validate(ws, ref["k"].replace("$", ""), "whole", 1, K_MAX)
    N, K, k, e, m = ref["deck"], ref["copies"], ref["k"], ref["extra"], ref["mull"]
    tab = 16
    first_turn = tab + 2  # row of Turn 1
    row_of = lambda t: first_turn + t - 1  # noqa: E731
    section(ws, 11, "Answer")
    answer(ws, 12, f'="In your opening hand: "&{pct(f"B{tab + 1}")}&IF({m}="Y"," (counting the redraw)","")')
    answer(ws, 13, f'="By the end of your turn 2: "&{pct(f"B{row_of(2)}")}&" going first, "&{pct(f"C{row_of(2)}")}&" going second"')
    answer(ws, 14, f'="By the end of your turn 4: "&{pct(f"B{row_of(4)}")}&" going first, "&{pct(f"C{row_of(4)}")}&" going second"')
    header(ws, tab, 1, ["By the end of your", "Going first", "Going second", "Cards seen, first", "Cards seen, second"])
    r = tab + 1
    put(ws, r, 1, "Opening hand", F_BOLD)
    put(ws, r, 4, 5)
    put(ws, r, 5, 5)
    for col in (2, 3):
        put(ws, r, col, "=" + xl_by_n(N, K, "5", k, m), fmt=PCT)
        expect(ws, f"{'BC'[col - 2]}{r}", odds.p_by_n(d["deck"], d["copies"], 5, d["k"]))
    for t in range(1, 7):
        r = row_of(t)
        put(ws, r, 1, f"Turn {t}", F_BOLD)
        for col, first in ((2, True), (3, False)):
            draws = f"{t - 1}" if first else f"{t}"
            seen_cell = f"{'DE'[col - 2]}{r}"
            put(ws, r, col + 2, f"=MIN(5+{draws}+ROUNDDOWN({e}*{t},0),{N}-5)")
            put(ws, r, col, "=" + xl_by_n(N, K, seen_cell, k, m), fmt=PCT)
            n = odds.cards_seen(t, first, d["extra"], d["deck"])
            expect(ws, seen_cell, n)
            expect(ws, f"{'BC'[col - 2]}{r}", odds.p_by_n(d["deck"], d["copies"], n, d["k"]))
    notes(ws, r + 2, [
        "Going first you skip your first draw, so you see one card fewer each turn.",
        "Your 5 security cards are face down and random, so they don't change these odds.",
    ])
    widths(ws, {"A": 30, "B": 16, "C": 16, "D": 16, "E": 18})


def sheet_copies(wb):
    ws = wb.create_sheet(S["copies"])
    title(ws, "How many copies", "How many cards that do a job you need, to have one by a turn as often as you want.")
    d = dict(deck=50, turn=2, order="First", extra=1, target=0.85, mull="Y", limit=4)
    ref = inputs(ws, 4, [
        ("deck", "Deck size", d["deck"], ""),
        ("turn", "By the end of your turn", d["turn"], "1 to 6"),
        ("order", "Going", d["order"], "First or Second"),
        ("extra", "Extra cards seen per turn", d["extra"], "digivolve draws and searches"),
        ("target", "How often you want it", d["target"], "85% = miss about 1 game in 7"),
        ("mull", "Redraw a hand with none", d["mull"], "Y or N"),
        ("limit", "Most copies allowed of one card", d["limit"], "4 normally; 1 if it is on the restricted list"),
    ])
    validate(ws, ref["order"].replace("$", ""), "list", options="First,Second")
    validate(ws, ref["mull"].replace("$", ""), "list", options="Y,N")
    validate(ws, ref["turn"].replace("$", ""), "whole", 1, 6)
    validate(ws, ref["limit"].replace("$", ""), "whole", 1, 4)
    N, T, o, e, tgt, m, lim = (ref[key] for key in ("deck", "turn", "order", "extra", "target", "mull", "limit"))
    seen_row, ans_row, tab = 16, 17, 19
    seen = f"$B${seen_row}"
    A = f"B{ans_row}"
    when = f'" by the end of turn "&{T}&" going "&LOWER({o})&", "&{pct(tgt)}&" of the time."'
    section(ws, 13, "Answer")
    answer(ws, 14, f'=IF(ISNUMBER({A}),IF({A}<={lim},"Run "&{A}&" copies of it to have one"&{when},'
                   f'"One card can\'t do it (the limit is "&{lim}&" copies). You need "&{A}&" cards that do the same job, so at least "'
                   f'&ROUNDUP({A}/{lim},0)&" different cards, to have one"&{when}),'
                   f'"Even 16 cards isn\'t enough. Lower the chance you want, or count cards that search for it.")')
    put(ws, seen_row, 1, "Cards you'll have seen by then", F_BOLD)
    put(ws, seen_row, 2, f'=MIN(5+{T}-IF({o}="First",1,0)+ROUNDDOWN({e}*{T},0),{N}-5)')
    n_py = odds.cards_seen(d["turn"], True, d["extra"], d["deck"])
    expect(ws, f"B{seen_row}", n_py)
    put(ws, ans_row, 1, "Fewest cards that get you there", F_BOLD)
    header(ws, tab, 1, ["Cards that do the job", "Chance to have one", "Enough?", "Share of the deck", "Different cards needed"])
    r = tab
    hits = []
    for K in range(1, 17):
        r += 1
        put(ws, r, 1, K, align="left")
        put(ws, r, 2, "=" + xl_by_n(N, str(K), seen, "1", m), fmt=PCT)
        put(ws, r, 3, f'=IF(B{r}>={tgt},"yes","")', align="center")
        put(ws, r, 4, f"={K}/{N}", fmt=PCT)
        put(ws, r, 5, f"=ROUNDUP({K}/{lim},0)")
        py = odds.p_by_n(d["deck"], K, n_py)
        expect(ws, f"B{r}", py)
        expect(ws, f"E{r}", math.ceil(K / d["limit"]))
        hits.append((K, py))
    first, last = tab + 1, r
    put(ws, ans_row, 2, f'=IFERROR(INDEX($A${first}:$A${last},MATCH("yes",$C${first}:$C${last},0)),"more than 16")',
        F_BOLD, align="left")
    expect(ws, f"B{ans_row}", next((K for K, p in hits if p >= d["target"]), "more than 16"))
    notes(ws, r + 2, [
        "One card number is capped at 4 copies (1 if it is on the restricted list; banned cards can't be played at all).",
        "Above the cap you are counting a group: different cards that do the same job, like all your Tamers or all your Lv3 searchers.",
        "Every card you add takes a slot from something else. 'Share of the deck' shows the cost in deck space.",
    ])
    widths(ws, {"A": 30, "B": 20, "C": 12, "D": 18, "E": 22})


def sheet_both(wb):
    ws = wb.create_sheet(S["both"])
    title(ws, "Both cards", "Chance to have at least one of card 1 AND at least one of card 2.")
    d = dict(deck=50, a=12, b=8, mull="Y")
    ref = inputs(ws, 4, [
        ("deck", "Deck size", d["deck"], ""),
        ("a", "Card 1 copies", d["a"], "the one you'd redraw for, like all your Lv3s"),
        ("b", "Card 2 copies", d["b"], "like all your Tamers; the two groups must be different cards"),
        ("mull", "Redraw a hand without card 1", d["mull"], "Y or N; a hand with card 1 but no card 2 is kept"),
    ])
    validate(ws, ref["mull"].replace("$", ""), "list", options="Y,N")
    N, A, B, m = ref["deck"], ref["a"], ref["b"], ref["mull"]
    tab = 13
    row_of = lambda n: tab + n - 4  # noqa: E731  (seen 5 -> tab + 1)
    section(ws, 10, "Answer")
    answer(ws, 11, f'="Opening hand: "&{pct(f"B{row_of(5)}")}&" have both. By about turn 2: "&{pct(f"B{row_of(8)}")}&"."')
    header(ws, tab, 1, ["Cards seen", "Chance to have both", "When that is"])
    when = {5: "opening hand", 6: "turn 1 going second", 7: "turn 2 going first", 8: "about turn 2 going second", 10: "about turn 3-4"}
    for n in range(5, 13):
        r = row_of(n)
        put(ws, r, 1, n, align="left")
        put(ws, r, 2, "=" + xl_both_by_n(N, A, B, str(n), m), fmt=PCT)
        put(ws, r, 3, when.get(n, ""), F_NOTE)
        expect(ws, f"B{r}", odds.p_both_by_n(d["deck"], d["a"], d["b"], n))
    notes(ws, r + 2, [
        "Use it for openings (a Lv3 and a Tamer) and two-card combos.",
        "If the number is low, add copies to the smaller group or add cards that search for it.",
    ], last_col=3)
    widths(ws, {"A": 30, "B": 20, "C": 30, "D": 14, "E": 14})


def sheet_memory(wb):
    ws = wb.create_sheet(S["memory"])
    title(ws, "Memory plan", "Write your plays in order. See where your turn ends and what the opponent starts with.")
    put(ws, 4, 1, "Memory you start with", F_BOLD)
    put(ws, 4, 2, 3, F_INPUT, align="left")
    note(ws, 4, 3, "3 if they passed, otherwise what they handed you")
    header(ws, 6, 1, ["Play, in order", "Cost", "Memory it gains", "Memory after", "What happens"])
    plays = [("Digivolve Lv3 to Lv4", 2, 0), ("Tamer: costs 2, gains 1 on play", 2, 1), ("Play an Option", 3, 0), ("Digivolve Lv4 to Lv5", 3, 0)]
    plays += [("", None, None)] * 6
    first = 7
    mem, over = 3, False
    for i, (name, cost, gain) in enumerate(plays):
        r = first + i
        put(ws, r, 1, name, F_INPUT)
        put(ws, r, 2, cost, F_INPUT, align="right")
        put(ws, r, 3, gain, F_INPUT, align="right")
        prev = "$B$4" if i == 0 else f"D{r - 1}"
        prev_over = "FALSE" if i == 0 else f'COUNTIF($E${first}:E{r - 1},"Turn*")>0'
        put(ws, r, 4, f'=IF(A{r}="",{prev},IF({prev_over},{prev},MAX({prev}-N(B{r})+N(C{r}),-10)))')
        put(ws, r, 5, f'=IF(A{r}="","",IF({prev_over},"Not played",IF(D{r}<0,"Turn ends: they start with "&MIN(-D{r},10),"")))', align="left")
        if name:
            if over:
                status = "Not played"
            else:
                mem = max(mem - cost + gain, -10)
                status = f"Turn ends: they start with {min(-mem, 10)}" if mem < 0 else ""
                over = mem < 0
            expect(ws, f"E{r}", status)
    last = first + len(plays) - 1
    section(ws, 18, "Answer")
    val = 20
    answer(ws, 19, f'=IF(B{val}="","Your turn hasn\'t ended yet. If you pass now, they start with 3.","They start their turn with "&B{val}&" memory.")')
    put(ws, val, 1, "They start their turn with", F_BOLD)
    put(ws, val, 2, f'=IFERROR(MIN(-INDEX(D{first}:D{last},MATCH("Turn*",E{first}:E{last},0)),10),"")', align="left")
    note(ws, val, 3, "blank means your turn hasn't ended")
    expect(ws, f"B{val}", 3)
    header(ws, 22, 1, ["Stopping their best play", "Value", "", "", ""])
    ws.merge_cells(start_row=22, start_column=3, end_row=22, end_column=5)
    put(ws, 23, 1, "Their best play costs", F_BOLD)
    put(ws, 23, 2, 5, F_INPUT, align="left")
    put(ws, 24, 1, "Memory they gain at the start of their turn", F_BOLD, wrap=True)
    put(ws, 24, 2, 1, F_INPUT, align="left")
    put(ws, 24, 3, "Tamers and start-of-turn effects; 0 if none", F_NOTE)
    put(ws, 25, 1, "Leave them at most", F_BOLD)
    put(ws, 25, 2, "=MAX(B23-1-B24,0)", F_BOLD, align="left")
    expect(ws, "B25", 3)
    answer(ws, 26, '="Leave them "&B25&" or less and they can\'t make that play. That means spending down to "&(-B25)&" on your side."')
    notes(ws, 28, [
        "A card's own memory gain goes on the same row as its cost: the turn only ends after the whole play resolves.",
        "At 0 memory you still get one more play. Make it the one that matters.",
    ])
    widths(ws, {"A": 34, "B": 12, "C": 18, "D": 14, "E": 32})


def sheet_race(wb):
    ws = wb.create_sheet(S["race"])
    title(ws, "The race", "Who wins if both players just attack every turn.")
    header(ws, 4, 1, ["Fill in", "You", "Them", ""])
    rows = [
        ("security", "Security left", 5, 4, ""),
        ("attacks", "Attackers each turn", 2, 2, "count a second attack from an unsuspend"),
        ("checks", "Checks per attack", 1, 1, "1, or more with Security Attack +"),
        ("blocks", "Blockers ready each turn", 1, 0, "each one stops one attack per turn"),
        ("start", "First turn you can attack", 2, 2, "your own turn number"),
    ]
    ref = {}
    for i, (key, label, you, them, hint) in enumerate(rows):
        r = 5 + i
        put(ws, r, 1, label, F_BOLD, wrap=True)
        put(ws, r, 2, you, F_INPUT, align="right")
        put(ws, r, 3, them, F_INPUT, align="right")
        put(ws, r, 4, hint, F_NOTE, wrap=True)
        ref[key] = (f"$B${r}", f"$C${r}")
    put(ws, 10, 1, "You go", F_BOLD)
    put(ws, 10, 2, "First", F_INPUT, align="right")
    validate(ws, "B10", "list", options="First,Second")
    order = "$B$10"
    tab = 15
    out_rows = {}
    labels = (("needed", "Attacks needed to win"), ("per_turn", "Attacks that get through per turn"),
              ("own_turns", "Turns of attacking needed"), ("kill_own", "Wins on own turn number"), ("kill_game", "Wins on game turn"))
    for i, (key, _) in enumerate(labels):
        out_rows[key] = tab + 1 + i
    yk, tk = f"B{out_rows['kill_game']}", f"C{out_rows['kill_game']}"
    section(ws, 12, "Answer", 4)
    answer(ws, 13, f'=IF(AND({yk}="never",{tk}="never"),"Nobody gets through.",IF({tk}="never","You win, on game turn "&{yk}&".",'
                   f'IF({yk}="never","They win, on game turn "&{tk}&".",IF({yk}<{tk},"You win first, on game turn "&{yk}&" (they would need until turn "&{tk}&").",'
                   f'"They win first, on game turn "&{tk}&" (you would need until turn "&{yk}&")."))))', last_col=4)
    header(ws, tab, 1, ["Details", "You", "Them", ""])
    for key, label in labels:
        put(ws, out_rows[key], 1, label, F_BOLD, wrap=True)
    put(ws, out_rows["needed"], 4, "clear their security, then one more to connect", F_NOTE)
    for side, other in ((0, 1), (1, 0)):
        col = "BC"[side]
        sec_other = ref["security"][other]
        att, chk, blk_other, start = ref["attacks"][side], ref["checks"][side], ref["blocks"][other], ref["start"][side]
        nd, pt, ot, ko = (f"{col}{out_rows[key]}" for key in ("needed", "per_turn", "own_turns", "kill_own"))
        put(ws, out_rows["needed"], 2 + side, f"=ROUNDUP({sec_other}/MAX({chk},1),0)+1")
        put(ws, out_rows["per_turn"], 2 + side, f"=MAX({att}-{blk_other},0)")
        put(ws, out_rows["own_turns"], 2 + side, f'=IF({pt}=0,"never",ROUNDUP({nd}/{pt},0))')
        put(ws, out_rows["kill_own"], 2 + side, f'=IF({pt}=0,"never",{start}+{ot}-1)')
        goes_first = f'{order}="First"' if side == 0 else f'{order}="Second"'
        put(ws, out_rows["kill_game"], 2 + side, f'=IF({pt}=0,"never",IF({goes_first},2*{ko}-1,2*{ko}))')

    def race(sec_other, att, chk, blk_other, start, first):
        needed = math.ceil(sec_other / max(chk, 1)) + 1
        per = max(att - blk_other, 0)
        if per == 0:
            return needed, per, "never", "never", "never"
        own = math.ceil(needed / per)
        ko = start + own - 1
        return needed, per, own, ko, 2 * ko - 1 if first else 2 * ko

    you = race(4, 2, 1, 0, 2, True)
    them = race(5, 2, 1, 1, 2, False)
    for key, idx in (("needed", 0), ("per_turn", 1), ("own_turns", 2), ("kill_own", 3), ("kill_game", 4)):
        expect(ws, f"B{out_rows[key]}", you[idx])
        expect(ws, f"C{out_rows[key]}", them[idx])
    notes(ws, tab + len(labels) + 2, [
        "This assumes every attack connects and nobody removes anything. It is the clock, not the whole game.",
        "One ready blocker takes one attack away from the other side every turn. Behind on the clock? Don't race: block or remove.",
    ], last_col=4)
    widths(ws, {"A": 36, "B": 12, "C": 12, "D": 44})


def sheet_risk(wb):
    ws = wb.create_sheet(S["risk"])
    title(ws, "Attack risk", "What their face-down security can do to your attacker this turn.")
    d = dict(deck=50, seen=12, killers=10, killers_seen=2, tamers=10, tamers_seen=3, checks=2)
    ref = inputs(ws, 4, [
        ("deck", "Their deck size", d["deck"], ""),
        ("seen", "Cards of theirs you've seen", d["seen"], "board, trash, cards under their stacks; not their hand"),
        ("killers", "Cards in their deck that beat your attacker", d["killers"], "DP equal or higher, or a security effect that deletes it"),
        ("killers_seen", "...of those, already seen", d["killers_seen"], "they can't be in security"),
        ("tamers", "Tamers in their deck that play free from security", d["tamers"], ""),
        ("tamers_seen", "...of those, already seen", d["tamers_seen"], ""),
        ("checks", "Checks you plan to make", d["checks"], "1 to 5"),
    ])
    N, Sn, K, Ks, T, Ts, C = (ref[key] for key in ("deck", "seen", "killers", "killers_seen", "tamers", "tamers_seen", "checks"))
    validate(ws, C.replace("$", ""), "whole", 1, 5)
    tab = 20
    first, last = tab + 1, tab + 5
    section(ws, 13, "Answer")
    answer(ws, 14, f'="With "&{C}&" checks: "&{pct(f"INDEX(B{first}:B{last},{C})")}&" chance a card beats your attacker, and "'
                   f'&{pct(f"INDEX(C{first}:C{last},{C})")}&" chance they flip a free Tamer."')
    put(ws, 16, 1, "Cards still unknown", F_BOLD)
    put(ws, 16, 2, f"={N}-{Sn}")
    put(ws, 16, 3, "their deck, hand and security together", F_NOTE)
    put(ws, 17, 1, "Attacker-beaters still unknown", F_BOLD)
    put(ws, 17, 2, f"=MAX({K}-{Ks},0)")
    put(ws, 18, 1, "Free Tamers still unknown", F_BOLD)
    put(ws, 18, 2, f"=MAX({T}-{Ts},0)")
    U, Ku, Tu = "$B$16", "$B$17", "$B$18"
    u, ku, tu = d["deck"] - d["seen"], d["killers"] - d["killers_seen"], d["tamers"] - d["tamers_seen"]
    expect(ws, "B16", u)
    header(ws, tab, 1, ["Checks", "A card beats your attacker", "They flip a free Tamer", "Nothing bad happens", "Free Tamers on average"])
    for c in range(1, 6):
        r = tab + c
        put(ws, r, 1, c, align="left")
        put(ws, r, 2, f"=1-{xl_comb(f'{U}-{Ku}', str(c))}/COMBIN({U},{c})", fmt=PCT)
        put(ws, r, 3, f"=1-{xl_comb(f'{U}-{Tu}', str(c))}/COMBIN({U},{c})", fmt=PCT)
        put(ws, r, 4, f"={xl_comb(f'{U}-{Ku}-{Tu}', str(c))}/COMBIN({U},{c})", fmt=PCT)
        put(ws, r, 5, f"={c}*{Tu}/{U}", fmt=NUM2)
        expect(ws, f"B{r}", odds.p_at_least(u, ku, c))
        expect(ws, f"C{r}", odds.p_at_least(u, tu, c))
        expect(ws, f"D{r}", 1 - odds.p_at_least(u, ku + tu, c))
        expect(ws, f"E{r}", c * tu / u)
    notes(ws, last + 2, [
        "Count from their decklist. A top regional list for that deck is a good stand-in until you see their cards.",
        "An attacker that dies stops checking. Barrier trades one of your security cards for its life.",
    ])
    widths(ws, {"A": 38, "B": 20, "C": 20, "D": 18, "E": 18})


def sheet_record(wb):
    ws = wb.create_sheet(S["record"])
    title(ws, "Is my record real", "A few games tell you less than you think. See what your record really says.")
    header(ws, 4, 1, ["Fill in", "Wins", "Losses", "Win rate", "Could be as low as", "Could be as high as", "Chance it's a winning deck"])
    rec = {"Version A": (6, 4), "Version B": (11, 9)}
    rows = {}
    for i, (name, (w, lo)) in enumerate(rec.items()):
        r = 5 + i
        rows[name] = r
        put(ws, r, 1, name, F_INPUT)
        put(ws, r, 2, w, F_INPUT, align="right")
        put(ws, r, 3, lo, F_INPUT, align="right")
        put(ws, r, 4, f"=B{r}/(B{r}+C{r})", fmt=PCT)
        low, high = xl_wilson(f"B{r}", f"(B{r}+C{r})")
        put(ws, r, 5, "=" + low, fmt=PCT)
        put(ws, r, 6, "=" + high, fmt=PCT)
        put(ws, r, 7, "=" + xl_favored(f"B{r}", f"C{r}"), fmt=PCT)
        pl, ph = odds.wilson(w, w + lo)
        expect(ws, f"E{r}", pl)
        expect(ws, f"F{r}", ph)
        expect(ws, f"G{r}", odds.p_favored(w, lo))
    a, b = rows["Version A"], rows["Version B"]
    section(ws, 8, "Answer", 7)
    for i, r in enumerate((a, b)):
        answer(ws, 9 + i, f'=A{r}&": "&{pct(f"D{r}")}&" so far, but the true rate could be anywhere from "&{pct(f"E{r}")}&" to "&{pct(f"F{r}")}'
                          f'&". Chance it is really a winning deck: "&{pct(f"G{r}")}&"."', last_col=7)
    put(ws, 11, 1, "Chance B is actually better than A", F_BOLD)
    put(ws, 11, 2, "=" + xl_better(f"B{a}", f"C{a}", f"B{b}", f"C{b}"), F_BOLD, fmt=PCT, align="left")
    note(ws, 11, 3, "near 50% = can't tell yet; above 90% or below 10% = a real difference")
    expect(ws, "B11", odds.p_better(6, 4, 11, 9))
    header(ws, 13, 1, ["To prove an improvement", "", "", "", "", "", ""])
    ws.merge_cells(start_row=13, start_column=1, end_row=13, end_column=7)
    header(ws, 14, 1, ["Your win rate now", "Win rate you hope for", "Games per version", "", "", "", ""])
    put(ws, 15, 1, 0.5, F_INPUT, fmt=PCT, align="left")
    put(ws, 15, 2, 0.6, F_INPUT, fmt=PCT, align="left")
    put(ws, 15, 3, "=" + xl_games_needed("A15", "B15"), F_BOLD)
    expect(ws, "C15", odds.games_needed(0.5, 0.6))
    answer(ws, 16, f'="To tell "&{pct("A15")}&" from "&{pct("B15")}&" apart you need about "&C15&" games with each version."', last_col=7)
    header(ws, 18, 1, ["If a change adds", "Games per version (from 50%)", "", "", "", "", ""])
    for i, gain in enumerate((0.05, 0.10, 0.15, 0.20)):
        r = 19 + i
        put(ws, r, 1, gain, fmt=PCT, align="left")
        put(ws, r, 2, "=" + xl_games_needed("0.5", f"(0.5+A{r})"))
        expect(ws, f"B{r}", odds.games_needed(0.5, 0.5 + gain))
    notes(ws, 24, [
        "'Could be as low / high as' is the range the true rate is 95% likely to be in.",
        "Test one change at a time and log every game. Trust big effects (+15% or more) sooner than small ones.",
    ], last_col=7)
    widths(ws, {"A": 34, "B": 20, "C": 18, "D": 12, "E": 16, "F": 16, "G": 22})


def sheet_deck(wb):
    ws = wb.create_sheet(S["deck"])
    title(ws, "Which deck", "Which deck gives you the best chance against the decks you expect to face. Example numbers: replace them.")
    put(ws, 4, 1, "Match format", F_BOLD)
    put(ws, 4, 2, "Bo3", F_INPUT, align="left")
    validate(ws, "B4", "list", options="Bo1,Bo3")
    put(ws, 5, 1, "Rounds", F_BOLD)
    put(ws, 5, 2, 6, F_INPUT, align="left")
    validate(ws, "B5", "whole", 1, 10)
    put(ws, 6, 1, "Wins you need (for the cut)", F_BOLD)
    put(ws, 6, 2, 5, F_INPUT, align="left")
    validate(ws, "B6", "whole", 0, 10)
    header(ws, 8, 1, ["Opponent deck", "How often you'll face it", "Deck A: game win rate", "Deck B: game win rate",
                      "Deck A: match win rate", "Deck B: match win rate"])
    meta = [("Deck 1", 0.25, 0.42, 0.55), ("Deck 2", 0.20, 0.16, 0.45), ("Deck 3", 0.20, 0.41, 0.50),
            ("Deck 4", 0.15, 0.46, 0.40), ("Everything else", 0.20, 0.55, 0.50)] + [("", None, None, None)] * 3
    first = 9
    for i, (name, share, pa, pb) in enumerate(meta):
        r = first + i
        put(ws, r, 1, name, F_INPUT)
        put(ws, r, 2, share, F_INPUT, fmt=PCT)
        put(ws, r, 3, pa, F_INPUT, fmt=PCT)
        put(ws, r, 4, pb, F_INPUT, fmt=PCT)
        for col, src in ((5, "C"), (6, "D")):
            put(ws, r, col, f'=IF({src}{r}="","",IF($B$4="Bo3",{src}{r}^2*(3-2*{src}{r}),{src}{r}))', fmt=PCT)
    last = first + len(meta) - 1
    exp_row = last + 2
    header(ws, exp_row - 1, 1, ["", "Share counted", "Deck A", "Deck B", "", ""])
    put(ws, exp_row, 1, "Expected match win rate", F_BOLD)
    put(ws, exp_row, 2, f"=SUM(B{first}:B{last})", fmt=PCT)
    for col, src in ((3, "E"), (4, "F")):
        put(ws, exp_row, col, f"=SUMPRODUCT(B{first}:B{last},{src}{first}:{src}{last})/SUM(B{first}:B{last})", F_BOLD, fmt=PCT)
    shares = [m[1] for m in meta if m[1] is not None]
    qa = sum(s * odds.bo3(m[2]) for s, m in zip(shares, meta, strict=False)) / sum(shares)
    qb = sum(s * odds.bo3(m[3]) for s, m in zip(shares, meta, strict=False)) / sum(shares)
    expect(ws, f"C{exp_row}", qa)
    expect(ws, f"D{exp_row}", qb)
    rec_head = exp_row + 6
    top = rec_head + 1
    section(ws, exp_row + 2, "Answer", 6)
    answer(ws, exp_row + 3, f'="Deck A is expected to win "&{pct(f"C{exp_row}")}&" of matches, Deck B "&{pct(f"D{exp_row}")}&"."', last_col=6)
    answer(ws, exp_row + 4, f'="Chance of at least "&$B$6&" wins in "&$B$5&" rounds: Deck A "&{pct(f"INDEX(C{top}:C{top + 10},$B$6+1)")}'
                            f'&", Deck B "&{pct(f"INDEX(E{top}:E{top + 10},$B$6+1)")}&"."', last_col=6)
    header(ws, rec_head, 1, ["Wins out of the rounds", "Deck A: exactly", "Deck A: at least", "Deck B: exactly", "Deck B: at least", ""])
    for w in range(0, 11):
        r = top + w
        put(ws, r, 1, w, align="left")
        for col, q in ((2, f"$C${exp_row}"), (4, f"$D${exp_row}")):
            put(ws, r, col, f'=IF({w}>$B$5,"",COMBIN($B$5,{w})*{q}^{w}*(1-{q})^($B$5-{w}))', fmt=PCT)
            L = "B" if col == 2 else "D"
            put(ws, r, col + 1, f'=IF({w}>$B$5,"",SUM({L}{r}:{L}{top + 10}))', fmt=PCT)
        if w <= 6:
            for col, q in (("C", qa), ("E", qb)):
                expect(ws, f"{col}{r}", sum(math.comb(6, x) * q**x * (1 - q) ** (6 - x) for x in range(w, 7)))
    notes(ws, top + 12, [
        "A deck with no bad matchups often beats one with a great matchup and a terrible one.",
        "Not in the math: how well YOU play each deck. A deck you know beats one that is 3% better on paper.",
    ], last_col=6)
    widths(ws, {"A": 28, "B": 20, "C": 20, "D": 20, "E": 20, "F": 20})


# ---------------------------------------------------------------------- puzzles
PUZZLE_WIDTH = {"A": 12, "B": 22, "C": 22, "D": 22, "E": 22, "F": 22}


def merged(ws, row: int, text, font=None, fill=None, fmt=None, first: int = 2, last: int = 6, height_text: str | None = None):
    """A wrapped cell across columns first..last. Formula cells can't be autofit, so
    `height_text` sizes the row for the longest text the formula can show."""
    put(ws, row, first, text, font or F_BASE, fill=fill, fmt=fmt, wrap=True, align="left")
    ws.merge_cells(start_row=row, start_column=first, end_row=row, end_column=last)
    if height_text:
        width = sum(PUZZLE_WIDTH[chr(ord("A") + c - 1)] for c in range(first, last + 1))
        lines = text_lines(height_text, width, (font.sz if font else 11) or 11)
        ws.row_dimensions[row].height = row_height(lines)


def sheet_puzzles(wb):
    """One block per puzzle; the answer, why and rule come from the hidden key sheet and show
    only once a pick is typed, so reading down the sheet doesn't give the answers away."""
    ws = wb.create_sheet(S["puzzles"])
    key = wb.create_sheet(KEY)
    key.sheet_state = "hidden"
    title(ws, "Puzzles", "Glowing Dawn situations with one best play. Type A, B, C or D under each one; "
                         "the answer, why, and the rule behind it appear once you pick.")
    title(key, "Puzzle key", "Hidden on purpose: the answers. The Puzzles sheet reads them from here.")
    header(key, 4, 1, ["#", "Answer", "Why", "Rule", "Evidence", "Source", "Skill", "Right", "Answered"])
    ps = puzzles()
    skills = list(dict.fromkeys(q.skill for q in ps))
    k_first, k_last = 5, 4 + len(ps)
    rng = lambda col: f"'{KEY}'!${col}${k_first}:${col}${k_last}"  # noqa: E731

    score, tab = 5, 7
    section(ws, 4, "Your score", 6)
    total_ans, total_right = f"SUM({rng('I')})", f"SUM({rng('H')})"
    answer(ws, score, f'=IF({total_ans}=0,"Pick an answer under each puzzle. You see why after you pick.",'
                      f'"Right: "&{total_right}&" of "&{total_ans}&" answered. "&IF({total_right}={total_ans},"No misses so far.",'
                      f'"Reread the rule under each miss, then redo those puzzles in a week."))', last_col=6)
    expect(ws, f"A{score}", "Pick an answer under each puzzle. You see why after you pick.")
    header(ws, tab, 1, ["Skill", "Puzzles", "Answered", "Right"])
    for i, s in enumerate(skills):
        r = tab + 1 + i
        put(ws, r, 1, s, F_BOLD)
        put(ws, r, 2, sum(q.skill == s for q in ps))
        put(ws, r, 3, f'=SUMIF({rng("G")},"{s}",{rng("I")})')
        put(ws, r, 4, f'=SUMIF({rng("G")},"{s}",{rng("H")})')
        expect(ws, f"C{r}", 0)
    skill_row = {s: tab + 1 + i for i, s in enumerate(skills)}

    right_all, wrong_all, want_right, want_wrong = {}, {}, {}, {}
    r = tab + len(skills) + 2
    for n, q in enumerate(ps, 1):
        k = k_first + n - 1
        header(ws, r, 1, [f"Puzzle {n}", q.matchup if q.matchup != "Any" else "Any matchup", "", q.skill, "", ""])
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        ws.merge_cells(start_row=r, start_column=4, end_row=r, end_column=6)
        put(ws, r + 1, 1, "Situation", F_BOLD)
        merged(ws, r + 1, q.situation)
        put(ws, r + 2, 1, "Question", F_BOLD)
        merged(ws, r + 2, q.question, F_BOLD)
        for i, opt in enumerate(q.options):
            put(ws, r + 3 + i, 1, LETTERS[i], F_BOLD, align="center")
            merged(ws, r + 3 + i, opt)
        pick_row = r + 3 + len(q.options)
        pick = f"$B${pick_row}"
        put(ws, pick_row, 1, "Your pick", F_BOLD)
        put(ws, pick_row, 2, None, F_INPUT, align="center")
        validate(ws, f"B{pick_row}", "list", options=",".join(LETTERS[:len(q.options)]))
        ans = f"'{KEY}'!$B${k}"
        verdict = f"Not this one: the best play is {q.answer}."
        hint = f"Type {', '.join(LETTERS[:len(q.options) - 1])} or {LETTERS[len(q.options) - 1]} in the cell to the left."
        merged(ws, pick_row, f'=IF({pick}="","{hint}",IF({pick}={ans},"Right.","Not this one: the best play is "&{ans}&"."))',
               F_BOLD, fill=FILL_KEY, first=3)
        expect(ws, f"C{pick_row}", hint)
        put(ws, pick_row + 1, 1, "Why", F_BOLD)
        merged(ws, pick_row + 1, f'=IF({pick}="","Pick an answer first.",\'{KEY}\'!$C${k})', height_text=q.why)
        expect(ws, f"B{pick_row + 1}", "Pick an answer first.")
        put(ws, pick_row + 2, 1, "Rule", F_BOLD)
        merged(ws, pick_row + 2, f'=IF({pick}="","",\'{KEY}\'!$D${k})', F_BOLD, height_text=q.rule)
        put(ws, pick_row + 3, 1, "Evidence", F_BOLD)
        evidence = f"{q.evidence}: {q.source}"
        merged(ws, pick_row + 3, f'=IF({pick}="","",\'{KEY}\'!$E${k}&": "&\'{KEY}\'!$F${k})', F_NOTE, height_text=evidence)

        for col, v in enumerate((n, q.answer, q.why, q.rule, q.evidence, q.source, q.skill), 1):
            put(key, k, col, v, wrap=col in (3, 4, 6))
        put(key, k, 8, f'=IF(\'{S["puzzles"]}\'!{pick}="","",IF(\'{S["puzzles"]}\'!{pick}=B{k},1,0))')
        put(key, k, 9, f'=IF(\'{S["puzzles"]}\'!{pick}="",0,1)')

        wrong = next(x for x in LETTERS[:len(q.options)] if x != q.answer)
        sheet = S["puzzles"].upper()
        right_all[f"{S['puzzles']}!B{pick_row}"] = q.answer
        wrong_all[f"{S['puzzles']}!B{pick_row}"] = wrong
        want_right[f"{sheet}!C{pick_row}"] = "Right."
        want_right[f"{sheet}!B{pick_row + 1}"] = q.why
        want_right[f"{sheet}!B{pick_row + 3}"] = evidence
        want_wrong[f"{sheet}!C{pick_row}"] = verdict
        want_wrong[f"{sheet}!B{pick_row + 2}"] = q.rule
        r = pick_row + 5

    sheet = S["puzzles"].upper()
    want_right[f"{sheet}!A{score}"] = f"Right: {len(ps)} of {len(ps)} answered. No misses so far."
    want_wrong[f"{sheet}!A{score}"] = f"Right: 0 of {len(ps)} answered. Reread the rule under each miss, then redo those puzzles in a week."
    for s, row in skill_row.items():
        count = sum(q.skill == s for q in ps)
        want_right[f"{sheet}!C{row}"] = count
        want_right[f"{sheet}!D{row}"] = count
        want_wrong[f"{sheet}!D{row}"] = 0
    SCENARIOS.append(("puzzles: every pick right", right_all, want_right))
    SCENARIOS.append(("puzzles: every pick wrong", wrong_all, want_wrong))
    widths(ws, PUZZLE_WIDTH)
    widths(key, {"A": 5, "B": 8, "C": 80, "D": 60, "E": 20, "F": 60, "G": 14, "H": 8, "I": 10})


# ---------------------------------------------------------------------- find my out
def sheet_out(wb):
    ws = wb.create_sheet(S["out"])
    title(ws, "Find my out", "Mid-game: will the card you need show up in time, is waiting a turn worth it, and do they hold their answer?")
    d = dict(deck=28, sec=4, bottom=2, copies=3, seen=1, bottomed=1, now=1, next=3)
    ref = inputs(ws, 4, [
        ("deck", "Cards left in your deck", d["deck"], ""),
        ("sec", "Your face-down security cards", d["sec"], "you haven't seen them, so your outs can be there"),
        ("bottom", "Cards you've put on the bottom of your deck", d["bottom"], "from reveals: known, and out of reach"),
        ("copies", "Copies of the card in your list", d["copies"], "or the whole group, like all your Lv6s"),
        ("seen", "...of those, seen (not on the bottom)", d["seen"], "hand, trash, board, under Tamers"),
        ("bottomed", "...of those, on the bottom", d["bottomed"], ""),
        ("now", "Cards you'll still see this turn", d["now"], "draws, digivolve draws; a reveal 3 counts 3"),
        ("next", "Cards you'll see next turn", d["next"], "your draw, digivolve draws and reveals"),
    ])
    for key in ref:
        validate(ws, ref[key].replace("$", ""), "whole", 0, 60)
    pool_row, outs_row, reach_row = 17, 18, 19
    U, K, R = f"$B${pool_row}", f"$B${outs_row}", f"$B${reach_row}"
    now_row, next_row = 21, 22

    def p_cell(n: str, k: str = "1") -> str:
        return "=" + xl_at_least(U, K, f"MAX(MIN({n},{R}),0)", k)

    section(ws, 14, "Answer")
    past = " That looks past the cards above your bottomed ones; the odds stop there."
    answer(ws, 15, f'="Find it this turn: "&{pct(f"B{now_row}")}&". By the end of next turn: "&{pct(f"B{next_row}")}&"."'
                   f'&IF({ref["now"]}+{ref["next"]}>{R},"{past}","")')
    put(ws, pool_row, 1, "Cards you don't know", F_BOLD)
    put(ws, pool_row, 2, f"=MAX({ref['deck']}-{ref['bottom']},0)+{ref['sec']}")
    note(ws, pool_row, 3, "the deck above your bottomed cards, plus your security")
    put(ws, outs_row, 1, "Copies still unknown", F_BOLD)
    put(ws, outs_row, 2, f"=MAX({ref['copies']}-{ref['seen']}-{ref['bottomed']},0)")
    put(ws, reach_row, 1, "Cards you can reach", F_BOLD)
    put(ws, reach_row, 2, f"=MAX({ref['deck']}-{ref['bottom']},0)")
    note(ws, reach_row, 3, "the deck above your bottomed cards")
    put(ws, now_row, 1, "Find it this turn", F_BOLD)
    put(ws, now_row, 2, p_cell(ref["now"]), F_BOLD, fmt=PCT)
    put(ws, next_row, 1, "Find it by the end of next turn", F_BOLD)
    put(ws, next_row, 2, p_cell(f"({ref['now']}+{ref['next']})"), F_BOLD, fmt=PCT)
    find = lambda seen, k=1: odds.p_find(d["deck"], d["sec"], d["bottom"], d["copies"] - d["seen"] - d["bottomed"], seen, k)  # noqa: E731
    expect(ws, f"B{pool_row}", 30)
    expect(ws, f"B{now_row}", find(d["now"]))
    expect(ws, f"B{next_row}", find(d["now"] + d["next"]))
    expect(ws, "A15", f"Find it this turn: {find(d['now']):.0%}. By the end of next turn: {find(d['now'] + d['next']):.0%}.")
    tab = 24
    header(ws, tab, 1, ["Cards you look at", "At least 1", "At least 2"])
    for n in range(1, 11):
        r = tab + n
        put(ws, r, 1, n, align="left")
        put(ws, r, 2, p_cell(str(n)), fmt=PCT)
        put(ws, r, 3, p_cell(str(n), "2"), fmt=PCT)
        expect(ws, f"B{r}", find(n))
        expect(ws, f"C{r}", find(n, 2))
    p_next = f"$B${next_row}"

    # Go now or wait
    g = dict(now=0.45, survive=0.70, win_with=0.80, win_without=0.30)
    top = tab + 12
    section(ws, top, "Go now or wait")
    gr = inputs(ws, top + 1, [
        ("now", "Chance you win if you go all-in now", g["now"], "the Calculator in the Glowing Dawn workbook, or a guess"),
        ("survive", "If you wait: chance you survive their turn", g["survive"], "every deck in this format bursts on its own turn 2"),
        ("with", "Chance you win next turn with the out", g["win_with"], ""),
        ("without", "...and without it", g["win_without"], ""),
    ])
    wait_row = top + 7
    put(ws, wait_row, 1, "Find the out by next turn", F_BOLD)
    put(ws, wait_row, 2, f"={p_next}", fmt=PCT)
    note(ws, wait_row, 3, "from above")
    put(ws, wait_row + 1, 1, "Chance you win if you wait", F_BOLD)
    W = f"$B${wait_row + 1}"
    put(ws, wait_row + 1, 2, f"={gr['survive']}*({p_next}*{gr['with']}+(1-{p_next})*{gr['without']})", F_BOLD, fmt=PCT)
    wait = odds.go_or_wait(find(d["now"] + d["next"]), g["survive"], g["win_with"], g["win_without"])
    expect(ws, f"B{wait_row + 1}", wait)
    diff = f'TEXT(ABS({gr["now"]}-{W})*100,"0")'
    answer(ws, wait_row + 2, f'="Go now: "&{pct(gr["now"])}&". Wait: "&{pct(W)}&". "&IF(ROUND({gr["now"]}-{W},2)=0,"About the same.",'
                             f'IF({gr["now"]}>{W},"Go now, by "&{diff}&" points.","Wait, by "&{diff}&" points."))')
    expect(ws, f"A{wait_row + 2}", f"Go now: {g['now']:.0%}. Wait: {wait:.0%}. Go now, by {abs(g['now'] - wait) * 100:.0f} points.")

    # Do they have it
    h = dict(deck=50, seen=15, copies=3, copies_seen=0, hand=5)
    top = wait_row + 4
    section(ws, top, "Do they have it")
    hr = inputs(ws, top + 1, [
        ("deck", "Their deck size", h["deck"], ""),
        ("seen", "Cards of theirs you've seen", h["seen"], "board, trash, under their stacks, cards they revealed"),
        ("copies", "Copies of the answer in their list", h["copies"], "a top list for that deck is a good stand-in"),
        ("copies_seen", "...of those, already seen", h["copies_seen"], ""),
        ("hand", "Cards in their hand", h["hand"], ""),
    ])
    hu, hk = f"({hr['deck']}-{hr['seen']})", f"MAX({hr['copies']}-{hr['copies_seen']},0)"
    unknown = h["deck"] - h["seen"]
    held = lambda n: odds.p_at_least(unknown, h["copies"] - h["copies_seen"], n)  # noqa: E731
    ans_row = top + 8
    put(ws, ans_row, 1, "Chance they hold at least one", F_BOLD)
    put(ws, ans_row, 2, f"=1-{xl_comb(f'{hu}-{hk}', hr['hand'])}/COMBIN({hu},{hr['hand']})", F_BOLD, fmt=PCT)
    expect(ws, f"B{ans_row}", held(h["hand"]))
    answer(ws, ans_row + 1, f'="With "&{hr["hand"]}&" cards in hand they hold at least one "&{pct(f"B{ans_row}")}&" of the time, if their hand is random."')
    htab = ans_row + 3
    header(ws, htab, 1, ["Cards in their hand", "At least one"])
    for n in range(1, 9):
        r = htab + n
        put(ws, r, 1, n, align="left")
        put(ws, r, 2, f"=1-{xl_comb(f'{hu}-{hk}', str(n))}/COMBIN({hu},{n})", fmt=PCT)
        expect(ws, f"B{r}", held(n))
    notes(ws, htab + 10, [
        "Your outs are the copies you haven't seen. Your face-down security is part of the unknown pile; cards you bottomed are not.",
        "Their hand isn't random once they've searched or held cards for turns: if they skipped a play they could have made, lean higher.",
        "These are odds, not a verdict. Weigh what playing around the card costs you against the chance it's there.",
        "Waiting for an out is only as good as your chance to survive their turn. Write all four numbers down before you choose.",
    ])
    sheet = S["out"]
    SCENARIOS.append((
        "find my out: looking past the bottomed cards, a 0-card hand",
        {f"{sheet}!{ref['next'].replace('$', '')}": 40, f"{sheet}!{hr['hand'].replace('$', '')}": 0},
        {f"{sheet.upper()}!A15": f"Find it this turn: {find(d['now']):.0%}. By the end of next turn: {find(d['now'] + 40):.0%}.{past}",
         f"{sheet.upper()}!B{next_row}": find(d["now"] + 40),
         f"{sheet.upper()}!B{ans_row}": 0.0},
    ))
    widths(ws, {"A": 44, "B": 16, "C": 18, "D": 18, "E": 18})


# ---------------------------------------------------------------------- quiz
def quiz_questions():
    """(question, Excel answer formula, Python answer, number format, sheet key to study)."""
    return [
        ("50-card deck, 4 copies of a card. Chance of at least one in your opening 5, no redraw?",
         "=" + xl_at_least("50", "4", "5", "1"), odds.p_at_least(50, 4, 5), PCT, "draw"),
        ("Same card, but you redraw a hand with none. Chance of at least one in your opening hand now?",
         "=" + xl_by_n("50", "4", "5", "1", '"Y"'), odds.p_by_n(50, 4, 5), PCT, "draw"),
        ("8 Tamers in 50. Chance of at least one by the end of turn 2 going second (9 cards seen), redrawing a hand with none?",
         "=" + xl_by_n("50", "8", "9", "1", '"Y"'), odds.p_by_n(50, 8, 9), PCT, "copies"),
        ("12 Lv3s and 8 Tamers in 50. Chance the opening 5 has both, no redraw?",
         "=" + xl_both("50", "12", "8", "5"), odds.p_both(50, 12, 8, 5), PCT, "both"),
        ("You have 1 memory and play a 2-cost Tamer that gains 1 memory on play. Your memory after it resolves?",
         "=1-2+1", 0, None, "memory"),
        ("You're at 2 memory and use a 3-cost Option. How much memory do they start their turn with?",
         "=-(2-3)", 1, None, "memory"),
        ("They have 3 security. Your attackers make 1 check each. How many attacks do you need to win this turn?",
         "=ROUNDUP(3/1,0)+1", 4, None, "race"),
        ("40 of their cards are unknown, 8 of them beat your attacker. You make 2 checks. Chance at least one beats it?",
         f"=1-{xl_comb('40-8', '2')}/COMBIN(40,2)", odds.p_at_least(40, 8, 2), PCT, "risk"),
        ("You went 7-3 with a new card. Chance it is really better than a coin flip?",
         "=" + xl_favored("7", "3"), odds.p_favored(7, 3), PCT, "record"),
        ("Your game win rate is 60%. Match win rate in a best of 3?",
         "=0.6^2*(3-2*0.6)", odds.bo3(0.6), PCT, "deck"),
        ("A quarter of the field is a deck you beat 40% of the time; the rest you beat 55%. Expected game win rate?",
         "=0.25*0.4+0.75*0.55", 0.25 * 0.4 + 0.75 * 0.55, PCT, "deck"),
        ("10 free Tamers among their 50 unknown cards. You make 3 checks. Free Tamers on average?",
         "=3*10/50", 3 * 10 / 50, NUM2, "risk"),
        ("A change adds 10% to a 50% win rate. Games per version to prove it?",
         "=" + xl_games_needed("0.5", "0.6"), odds.games_needed(0.5, 0.6), None, "record"),
        ("12 copies in 50. Chance of at least 2 by the end of turn 3 going first (10 cards seen), redrawing a hand with none?",
         "=" + xl_by_n("50", "12", "10", "2", '"Y"'), odds.p_by_n(50, 12, 10, 2), PCT, "draw"),
    ]


def sheet_quiz(wb):
    ws = wb.create_sheet(S["quiz"])
    title(ws, "Quiz", "Type your guess, then look at the answer. For percent questions type 35 for 35%. Blank guesses are skipped.")
    header(ws, 4, 1, ["#", "Question", "Your guess", "Answer", "Off by", "Study this"])
    questions = quiz_questions()
    first = 5
    pct_rows = []
    for i, (q, formula, ans, fmt, key) in enumerate(questions, 1):
        r = first + i - 1
        put(ws, r, 1, i, align="center")
        put(ws, r, 2, q, wrap=True)
        put(ws, r, 3, None, F_INPUT, align="right")
        put(ws, r, 4, formula, fmt=fmt)
        if fmt == PCT:
            put(ws, r, 5, f'=IF(C{r}="","",ABS(C{r}/100-D{r}))', fmt=PCT)
            pct_rows.append(r)
        else:
            put(ws, r, 5, f'=IF(C{r}="","",ABS(C{r}-D{r}))', fmt=fmt)
        link(ws, r, 6, S[key])
        expect(ws, f"D{r}", ans)
    last = first + len(questions) - 1
    cells = ",".join(f"E{x}" for x in pct_rows)
    count_rows = [x for x in range(first, last + 1) if x not in pct_rows]
    r = last + 2
    section(ws, r, "Your score", 6)
    answer(ws, r + 1, f'=IFERROR("Average miss on the percent questions: "&TEXT(AVERAGE({cells})*100,"0")&" points. "'
                      f'&IF(AVERAGE({cells})<0.05,"Good instincts.",IF(AVERAGE({cells})<0.15,"Decent. Study your biggest miss.","Spend an hour on the sheets in the Study column.")),'
                      f'"No guesses yet. Type a guess next to each question.")', last_col=6)
    put(ws, r + 2, 1, "Biggest miss: question", F_BOLD)
    ws.merge_cells(start_row=r + 2, start_column=1, end_row=r + 2, end_column=3)
    put(ws, r + 2, 4, f'=IFERROR(INDEX($A${first}:$A${last},MATCH(MAX({cells}),$E${first}:$E${last},0)),"")', F_BOLD)
    put(ws, r + 3, 1, "Counting questions exactly right", F_BOLD)
    ws.merge_cells(start_row=r + 3, start_column=1, end_row=r + 3, end_column=3)
    put(ws, r + 3, 4, "=" + "+".join(f"IF(E{x}=0,1,0)" for x in count_rows) + f'&" of {len(count_rows)}"', F_BOLD)
    expect(ws, f"D{r + 3}", f"0 of {len(count_rows)}")
    notes(ws, r + 5, [
        "Under 5 points average miss is good table instinct. Over 15 means the sheet in the Study column is worth an hour.",
        f"Log your misses on the {LOG['guesses']} sheet of your log file and redo the quiz in a month. The trend is the point.",
    ], last_col=6)
    widths(ws, {"A": 5, "B": 80, "C": 12, "D": 12, "E": 12, "F": 18})


# ---------------------------------------------------------------------- guides
CONCEPTS = [
    ("Card advantage", "Having more useful cards than the opponent.", "Count cards before a trade. 1 of yours for 3 of theirs is a win.", "draw"),
    ("Tempo", "Getting more done per turn and per memory than they do.", "Prefer cheap plays that cost them a lot to answer.", "memory"),
    ("Memory is shared", "Memory you spend past 0 is memory they start with.", "Decide what you want them to start with, then spend down to it.", "memory"),
    ("Memory denial", "Leaving them less than their best play costs.", "If their best play costs 4, leaving them 3 can beat making one more play.", "memory"),
    ("Security is a lottery", "Each security card is a life point AND a random effect for them.", "Count what their deck can flip before you attack.", "risk"),
    ("Known cards", "Their trash and board are known. Deck, hand and security are one unknown pile.", "If 2 of their 4 killers are already out, only 2 can be in security.", "risk"),
    ("Clock", "Turns until you win if nothing changes. Theirs: turns until they do.", "Faster clock: race. Slower: block or remove.", "race"),
    ("Lethal", "Attacks needed = clear their security, plus 1 to connect, minus their blocks.", "Count it before the first attack, not after.", "race"),
    ("Chip damage", "Taking some security without winning.", "Only chip if it really speeds up your clock. Each flip can give them a free card.", "risk"),
    ("Outs", "The cards that win or save you.", "Count the copies you haven't seen, security included, and the odds of one in time.", "out"),
    ("Overextending", "Putting more on the board than you need, into a wipe.", "Hold back what you don't need to win.", "method"),
    ("Breeding area", "Safe from attacks and most removal.", "Build there while they have removal ready. Move out when you can win.", "method"),
    ("Effect types", "Protection names what it stops: Digimon effects, Options, or battles.", "Read the exact words. Immune to Digimon effects still dies to an Option.", "method"),
    ("Inherited effects", "Cards under a Digimon give it their inherited effects.", "Plan what ends up under your attacker.", "method"),
    ("Turn order", "First: no first draw, but you act first. Second: one extra card every turn.", "Check both columns on Will I draw it.", "draw"),
    ("Sample size", "10 games tell you almost nothing.", "Judge by the likely range, not the record.", "record"),
    ("Expected value", "The average result of a choice over all outcomes.", "Pick the line with the best chance to win, not the best best-case.", "deck"),
    ("Calibration", "How close your gut is to the real odds.", "Guess before you calculate. Log the miss.", "quiz"),
]


def sheet_ideas(wb):
    ws = wb.create_sheet(S["ideas"])
    title(ws, "Key ideas", "What strong players count. Each one points to the sheet that measures it.")
    header(ws, 4, 1, ["Idea", "What it means", "What to do", "Try it on"])
    for i, (name, means, do, key) in enumerate(CONCEPTS):
        r = 5 + i
        put(ws, r, 1, name, F_BOLD, wrap=True)
        put(ws, r, 2, means, wrap=True)
        put(ws, r, 3, do, wrap=True)
        link(ws, r, 4, S[key])
    widths(ws, {"A": 22, "B": 52, "C": 60, "D": 20})


METHOD = [
    ("1. Win condition", "What you need on the board to win, and by which turn. That turn is your clock.", "race"),
    ("2. Resources", "What each card gives and costs: memory, cards, board, security.", "memory"),
    ("3. Consistency", "How often you have your start and your combo when they matter.", "copies"),
    ("4. The field", "Which decks you'll face, how often, and your result against each.", "deck"),
    ("5. Their plan", "Their win condition, their key turn, their clock.", "race"),
    ("6. Their removal", "Sort it by type (Digimon effect, Option, battle, -DP, suspend, hand, security). Match each to your protection.", "ideas"),
    ("7. Your outs", "Which cards answer each threat, and the odds of having one in time.", "draw"),
    ("8. Key turns", "Plan the turns that decide games: memory, attack counts, what stays in breeding.", "risk"),
    ("9. Test", "Change one thing at a time. Log every game.", "record"),
    ("10. Review", "Sort losses: draw, misplay, matchup, flip. Fix the biggest one you control.", "practice"),
]
WORKSHEET = [
    "How it wins", "Its key turn (own turn number)", "Its clock (turn it usually kills)",
    "Removal it has, by type", "Blockers and protection", "How it uses memory", "What it flips from security",
    "My plan: turns 1-2", "My plan: the kill turn", "My outs to its key threat", "What I pass them at end of turn",
    "Last updated",
]


def sheet_method(wb, log_name):
    ws = wb.create_sheet(S["method"])
    title(ws, "How to theorycraft", "Ten steps to break down any deck or matchup.")
    header(ws, 4, 1, ["Step", "Work out", "Measure it on"])
    for i, (step, what, key) in enumerate(METHOD):
        put(ws, 5 + i, 1, step, F_BOLD)
        put(ws, 5 + i, 2, what, wrap=True)
        link(ws, 5 + i, 3, S[key])
    r = 5 + len(METHOD) + 1
    section(ws, r, "Deck notes", 3)
    r += 1
    put(ws, r, 1, f"Fill one column per top deck on the {LOG['notes']} sheet of {log_name}. The fields:", wrap=True)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    for field in WORKSHEET[:-1]:
        r += 1
        put(ws, r, 2, field)
    widths(ws, {"A": 22, "B": 80, "C": 20})


DRILLS = [
    ("Puzzles", "Do the Puzzles sheet. Decide before you read the options. Redo your misses a week later.", "Weekly"),
    ("Opening hands", "Shuffle, draw 5, decide keep or redraw in 10 seconds. Do 20. Compare with Will I draw it.", "Daily, 5 minutes"),
    ("Goldfish", "Play your deck alone for 4 turns, 10 times. Note the turn you could win.", "Weekly"),
    ("Guess, then check", "Before any calculator, write your guess. Log the miss on the Guess Log.", "Every session"),
    ("Lethal count", "Lay out a random board for both sides. Count attacks needed vs available in 15 seconds.", "Daily"),
    ("Exact memory", "Pick a target ('they start with 2') and plan a turn that ends exactly there.", "Weekly"),
    ("Predict their turn", "Before each opponent turn, guess their main play. Score yourself.", "Every game"),
    ("Loss review", "After a loss, log the deciding turn and its cause: draw, misplay, matchup, or flip.", "After every loss"),
    ("Watch and pause", "Watch a top player. Pause at each big decision, pick your play, then compare.", "Weekly"),
    ("Deck notes", "Fill one in for each top deck. Update after you play the matchup.", "Monthly"),
    ("One change at a time", "Change one card, log the games until Is my record real says the difference is real.", "When building"),
]


def sheet_practice(wb):
    ws = wb.create_sheet(S["practice"])
    title(ws, "Practice", "Routines that build the skills these sheets measure.")
    header(ws, 4, 1, ["Drill", "How", "How often"])
    for i, (name, how, often) in enumerate(DRILLS):
        put(ws, 5 + i, 1, name, F_BOLD)
        put(ws, 5 + i, 2, how, wrap=True)
        put(ws, 5 + i, 3, often, F_LINK)
    widths(ws, {"A": 22, "B": 80, "C": 18})


RULES = [
    "Opening hand: 5 cards. Each player may redraw once: shuffle the whole hand back and draw 5 new cards.",
    "Security: the next 5 cards of the deck, face down. You don't see them, so they don't change your draw odds.",
    "The player going first skips the draw on their first turn. Digivolving draws 1 card.",
    "Your turn ends when memory is 1 or more on the opponent's side, checked after a play fully resolves. Passing gives them 3.",
    "You win when an attack connects while they have 0 security. Removing their last card isn't a win; the next attack is.",
    "Up to 4 copies of a card number per deck. Bandai's banned and restricted list (a separate document) sets some cards to 1 copy or 0.",
]
PLAN = [
    ("Week 1: decisions", "Puzzles: all of them, reading every Why. Key ideas. Drill: opening hands.", "puzzles"),
    ("Week 2: resources", "Memory plan, The race. Drills: exact memory, lethal count. Replay two turns from real games.", "memory"),
    ("Week 3: risk", "Find my out, Attack risk, Quiz. Drill: guess then check. Start the Guess Log.", "out"),
    ("Week 4: judgement", "Is my record real, Which deck, How to theorycraft. Fill in Deck Notes. Review the Game Log. Redo missed puzzles.", "record"),
]


def sheet_how(wb):
    ws = wb.create_sheet(S["how"])
    title(ws, "How it works", "The rules and math behind the sheets, and a plan if you want one.")
    r = 4
    section(ws, r, "Game rules used (official Comprehensive Rules)", 3)
    for text in RULES:
        r += 1
        put(ws, r, 1, text, wrap=True)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    r += 2
    section(ws, r, "How the math is checked", 3)
    for text in ("The formulas live in one Python file (goldfish/odds.py), tested by dealing thousands of hands card by card.",
                 "Every number in this workbook is recalculated and compared with those Python answers before it is released.",
                 "The redraw is modeled the way people play: shuffle back a hand with none of the card, keep a hand with one.",
                 "Mid-game, your face-down security and the deck above the cards you bottomed are one unknown pile; that is tested by dealing games out card by card.",
                 "Each puzzle answer carries its evidence: card text, the research notes behind the Glowing Dawn workbook, or the goldfish simulator."):
        r += 1
        put(ws, r, 1, text, wrap=True)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=3)
    r += 2
    header(ws, r, 1, ["If you want a plan", "What to do", "Start on"])
    for name, what, key in PLAN:
        r += 1
        put(ws, r, 1, name, F_BOLD)
        put(ws, r, 2, what, wrap=True)
        link(ws, r, 3, S[key])
    widths(ws, {"A": 26, "B": 90, "C": 18})


# ---------------------------------------------------------------------- the log file
EXAMPLE_GAMES = [
    (dt.date(2026, 10, 6), "Glowing Dawn", "Jupitermon", "Second", "W", 4, "", "example row: delete it"),
    (dt.date(2026, 10, 6), "Glowing Dawn", "Toho Braves", "First", "L", 5, "Misplay", "example row: chipped into a Tamer"),
]
EXAMPLE_DECKS = ["Jupitermon", "TS Mervamon", "Toho Braves", "DATA SQUAD Ravemon"]


def log_games(wb):
    ws = wb.active
    ws.title = LOG["games"]
    title(ws, "Game log", f"One row per game. {LOG['results']} reads this sheet. The two example rows show how; delete them.")
    header(ws, 4, 1, ["Date", "My deck", "Opponent deck", "Went", "Result", "Decided on turn", "Cause of loss", "Notes"])
    first, last = 5, 4 + LOG_ROWS
    for r in range(first, last + 1):
        for c in range(1, 9):
            put(ws, r, c, None, F_INPUT)
        ws.cell(row=r, column=1).number_format = "yyyy-mm-dd"
    for i, row in enumerate(EXAMPLE_GAMES):
        for c, v in enumerate(row, 1):
            put(ws, first + i, c, v, F_INPUT)
        ws.cell(row=first + i, column=1).number_format = "yyyy-mm-dd"
    validate(ws, f"D{first}:D{last}", "list", options="First,Second")
    validate(ws, f"E{first}:E{last}", "list", options="W,L,T")
    validate(ws, f"G{first}:G{last}", "list", options=",".join(CAUSES))
    validate(ws, f"F{first}:F{last}", "whole", 1, 30)
    widths(ws, {"A": 12, "B": 18, "C": 22, "D": 10, "E": 8, "F": 16, "G": 14, "H": 60})
    return first, last


def log_results(wb, first, last):
    ws = wb.create_sheet(LOG["results"])
    title(ws, "My results", "Type your opponent decks in the blue cells, spelled as in the game log. Everything else fills itself in.")
    g = LOG["games"]
    opp, res, went, cause = (f"'{g}'!${c}${first}:${c}${last}" for c in "CEDG")
    header(ws, 4, 1, ["Opponent deck", "Games", "Wins", "Losses", "Ties", "Win rate", "Could be as low as", "Could be as high as",
                      "Chance you're favored"] + [f"Lost to: {c.lower()}" for c in CAUSES])
    r = 4
    for i in range(10):
        r += 1
        put(ws, r, 1, EXAMPLE_DECKS[i] if i < len(EXAMPLE_DECKS) else None, F_INPUT)
        put(ws, r, 2, f'=IF(A{r}="","",COUNTIF({opp},A{r}))')
        for col, code in ((3, "W"), (4, "L"), (5, "T")):
            put(ws, r, col, f'=IF(A{r}="","",COUNTIFS({opp},A{r},{res},"{code}"))')
        n = f"(N(C{r})+N(D{r}))"
        blank = f'OR(A{r}="",{n}=0)'
        put(ws, r, 6, f'=IF({blank},"",C{r}/{n})', fmt=PCT, fill=FILL_KEY)
        low, high = xl_wilson(f"N(C{r})", n)
        put(ws, r, 7, f'=IF({blank},"",{low})', fmt=PCT)
        put(ws, r, 8, f'=IF({blank},"",{high})', fmt=PCT)
        put(ws, r, 9, f'=IF({blank},"",{xl_favored(f"N(C{r})", f"N(D{r})")})', fmt=PCT)
        for j, c in enumerate(CAUSES):
            put(ws, r, 10 + j, f'=IF(A{r}="","",COUNTIFS({opp},A{r},{res},"L",{cause},"{c}"))')
    expect(ws, "B5", 1)
    expect(ws, "C5", 1)
    expect(ws, "D7", 1)
    expect(ws, "K7", 1)
    r += 2
    put(ws, r, 1, "All games", F_BOLD)
    put(ws, r, 2, f'=COUNTIF({res},"W")+COUNTIF({res},"L")+COUNTIF({res},"T")')
    for col, code in ((3, "W"), (4, "L"), (5, "T")):
        put(ws, r, col, f'=COUNTIF({res},"{code}")')
    n = f"(C{r}+D{r})"
    put(ws, r, 6, f'=IF({n}=0,"",C{r}/{n})', fmt=PCT, fill=FILL_KEY)
    low, high = xl_wilson(f"C{r}", n)
    put(ws, r, 7, f'=IF({n}=0,"",{low})', fmt=PCT)
    put(ws, r, 8, f'=IF({n}=0,"",{high})', fmt=PCT)
    put(ws, r, 9, f'=IF({n}=0,"",{xl_favored(f"C{r}", f"D{r}")})', fmt=PCT)
    for j, c in enumerate(CAUSES):
        put(ws, r, 10 + j, f'=COUNTIFS({res},"L",{cause},"{c}")')
    expect(ws, f"B{r}", 2)
    expect(ws, f"F{r}", 0.5)
    r += 2
    header(ws, r, 1, ["Going", "Games", "Wins", "Losses", "Ties", "Win rate"])
    for side in ("First", "Second"):
        r += 1
        put(ws, r, 1, side, F_BOLD)
        put(ws, r, 2, f'=COUNTIFS({went},"{side}",{res},"W")+COUNTIFS({went},"{side}",{res},"L")+COUNTIFS({went},"{side}",{res},"T")')
        for col, code in ((3, "W"), (4, "L"), (5, "T")):
            put(ws, r, col, f'=COUNTIFS({went},"{side}",{res},"{code}")')
        put(ws, r, 6, f'=IF(C{r}+D{r}=0,"",C{r}/(C{r}+D{r}))', fmt=PCT)
    notes(ws, r + 2, [
        "'Could be as low / high as' is the range your true win rate is 95% likely to be in. 'Chance you're favored' = chance it is above 50%.",
        "The 'Lost to' columns say what to work on. Misplay is the one you control. Draw and Flip are luck. Matchup is a deck question.",
    ], last_col=9)
    widths(ws, {"A": 24, "B": 8, "C": 8, "D": 8, "E": 8, "F": 10, "G": 14, "H": 14, "I": 18,
                **{chr(ord("J") + j): 14 for j in range(len(CAUSES))}})


def log_guesses(wb):
    ws = wb.create_sheet(LOG["guesses"])
    title(ws, "Guess log", "Every time you guess an odd and then check it, log it here. Your misses should shrink over the months.")
    header(ws, 4, 1, ["Date", "Skill", "Situation", "Your guess (%)", "Real odds (%)", "Off by (points)", "Entry #"])
    first, last = 5, 4 + LOG_ROWS
    for r in range(first, last + 1):
        for c in range(1, 6):
            put(ws, r, c, None, F_INPUT)
        ws.cell(row=r, column=1).number_format = "yyyy-mm-dd"
        put(ws, r, 6, f'=IF(OR(D{r}="",E{r}=""),"",ABS(D{r}-E{r}))')
        put(ws, r, 7, f'=IF(D{r}="","",COUNTA($D${first}:D{r}))', F_NOTE)
    real = round(100 * odds.p_at_least(50, 4, 5), 1)
    put(ws, first, 1, dt.date(2026, 10, 6), F_INPUT)
    ws.cell(row=first, column=1).number_format = "yyyy-mm-dd"
    put(ws, first, 2, "Draw odds", F_INPUT)
    put(ws, first, 3, "example row, delete it: a 4-of in the opening 5, no redraw", F_INPUT)
    put(ws, first, 4, 40, F_INPUT)
    put(ws, first, 5, real, F_INPUT)
    expect(ws, f"F{first}", abs(40 - real))
    validate(ws, f"B{first}:B{last}", "list", options=",".join(SKILLS))
    validate(ws, f"D{first}:E{last}", "decimal", 0, 100)
    off, skill, entry = (f"${c}${first}:${c}${last}" for c in "FBG")
    header(ws, 4, 9, ["Summary", "Average miss (points)"])
    r = 5
    put(ws, r, 9, "All entries", F_BOLD)
    put(ws, r, 10, f'=IFERROR(AVERAGE({off}),"")', F_BOLD, fill=FILL_KEY)
    expect(ws, f"J{r}", abs(40 - real))
    r += 1
    put(ws, r, 9, "Your first 10", F_BOLD)
    put(ws, r, 10, f'=IFERROR(AVERAGEIFS({off},{entry},"<=10"),"")')
    r += 1
    put(ws, r, 9, "Your latest 10", F_BOLD)
    put(ws, r, 10, f'=IFERROR(AVERAGEIFS({off},{entry},">"&(COUNTA($D${first}:$D${last})-10)),"")')
    for s in SKILLS:
        r += 1
        put(ws, r, 9, s, F_BOLD)
        put(ws, r, 10, f'=IFERROR(AVERAGEIFS({off},{skill},"{s}"),"")')
    widths(ws, {"A": 12, "B": 14, "C": 52, "D": 14, "E": 14, "F": 14, "G": 8, "H": 3, "I": 20, "J": 22})


def log_notes(wb):
    ws = wb.create_sheet(LOG["notes"])
    title(ws, "Deck notes", "One column per deck you expect to face. Update after you play the matchup.")
    header(ws, 4, 1, ["Field"] + [f"Deck {i}" for i in range(1, 5)])
    put(ws, 5, 1, "Their deck", F_BOLD)
    for j, name in enumerate(EXAMPLE_DECKS):
        put(ws, 5, 2 + j, name, F_INPUT)
    for i, field in enumerate(WORKSHEET):
        r = 6 + i
        put(ws, r, 1, field, F_BOLD, wrap=True)
        for j in range(4):
            put(ws, r, 2 + j, None, F_INPUT, wrap=True)
        ws.row_dimensions[r].height = 45
    widths(ws, {"A": 30, "B": 36, "C": 36, "D": 36, "E": 36})


def build_log(path: Path, force: bool = False) -> Path | None:
    """Your personal log. Created only if missing, unless `force`."""
    if path.exists() and not force:
        return None
    wb = Workbook()
    first, last = log_games(wb)
    log_results(wb, first, last)
    log_guesses(wb)
    log_notes(wb)
    finalize(wb)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path


def build(out: Path, log_name: str = "digimon-player-log.xlsx") -> Path:
    wb = Workbook()
    stamp = dt.date.today().isoformat()
    sheet_start(wb, stamp, log_name)
    sheet_puzzles(wb)
    sheet_out(wb)
    sheet_quiz(wb)
    sheet_draw(wb)
    sheet_copies(wb)
    sheet_both(wb)
    sheet_memory(wb)
    sheet_race(wb)
    sheet_risk(wb)
    sheet_record(wb)
    sheet_deck(wb)
    sheet_ideas(wb)
    sheet_method(wb, log_name)
    sheet_practice(wb)
    sheet_how(wb)
    wb.move_sheet(KEY, offset=len(wb.sheetnames) - 1 - wb.sheetnames.index(KEY))
    finalize(wb)
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", type=Path, default=ROOT / "reports" / "digimon-player-math.xlsx")
    ap.add_argument("--log", type=Path, default=ROOT / "reports" / "digimon-player-log.xlsx")
    ap.add_argument("--force-log", action="store_true", help="overwrite the log file (your entries are lost)")
    args = ap.parse_args(argv)
    print(f"wrote {build(args.out, args.log.name)}")
    made = build_log(args.log, args.force_log)
    print(f"wrote {made}" if made else f"kept {args.log} (your log; --force-log to replace it)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
