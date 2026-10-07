"""Decision puzzles for the player workbook: Glowing Dawn situations with one best play.

Each answer comes from the research behind the theorycraft workbook (research_data.RULES and
PLAYBOOKS, research/*.md) or from printed card text, and carries the same evidence tags.
The odds puzzles compute their numbers with goldfish.odds, so the text can't drift from the
math. A puzzle only goes in when the answer is clear from its evidence; contested lines
(chipping Jupitermon to race, going first or second) stay out until the matchup sims settle them.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import NamedTuple

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from research_data import SECURITY_LINKS  # noqa: E402

from goldfish import odds  # noqa: E402

LETTERS = "ABCD"
TOHO = 2  # matchup index in research_data


class Puzzle(NamedTuple):
    matchup: str
    skill: str
    situation: str
    question: str
    options: tuple[str, ...]
    answer: str
    why: str
    rule: str
    evidence: str
    source: str


def security_rate(label: str, matchup: int) -> float:
    return next(rates[matchup] for name, _, rates in SECURITY_LINKS if name.startswith(label))


def closest(options: list[float], value: float) -> str:
    return LETTERS[min(range(len(options)), key=lambda i: abs(options[i] - value))]


def puzzles() -> list[Puzzle]:
    keep = odds.p_at_least(45, 8, 4)   # no Tamer in the opening 5; 2 draws + 2 digivolve draws by end of T2
    redraw = odds.p_at_least(50, 8, 9)  # a fresh 5 plus the same 4 cards
    toho_kills_lv4 = security_rate("P(security Digimon >= 5000)", TOHO)
    toho_free = security_rate("P(free play / resource from security)", TOHO)

    go_now, survive, win_with, win_without, find = 0.45, 0.70, 0.80, 0.30, 0.35
    wait = odds.go_or_wait(find, survive, win_with, win_without)

    unknown, plasment, hand = 50 - 15, 3, 5
    holds = odds.p_at_least(unknown, plasment, hand)
    hold_opts = [plasment / unknown, holds, 0.60, 0.85]

    out = odds.p_find(28, 4, 2, 1, 3)
    naive = odds.p_at_least(28, 2, 3)
    out_opts = [out, naive, 0.30]

    p = [
        Puzzle(
            "Any", "Opening",
            "Going second. Your opening hand: Liollmon BT26-025, Cougarmon BT25-035, Monarchlizamon BT25-057, Murasamemon ST23-04, "
            "Atratusmon. No Tamer, no e-Pulse, and no Lv3 that searches (Gekkomon or Liollmon BT25-032).",
            "Keep or redraw?",
            ("Keep: you have a Lv3 and a full line to Lv6.",
             "Redraw.",
             "Keep and dig: 8 Tamers in the other 45 cards will turn up."),
            "B",
            f"The deck runs on fuel under Tamers, and a Tamer that lands after turn 2 never banks enough for the kill. "
            f"Keeping, you have a Tamer by the end of turn 2 only {keep:.0%} of the time (draws and digivolve draws, before searchers). "
            f"A fresh 5 gets there {redraw:.0%} of the time. The redraw can be worse in other ways, but the Tamer-less game is the one you lose.",
            "Keep a Lv3 plus a Tamer or a way to find one (e-Pulse, Gekkomon, Liollmon BT25-032). Otherwise redraw.",
            "STATED + OBSERVED",
            "TCGplayer and cardsrealm guides; both losses in the GAO and Security Check games had no Tamer until turn 3-4. Odds: goldfish/odds.py.",
        ),
        Puzzle(
            "Any", "Opening",
            "You go first. Turn 1, 0 memory: you hatched Kekkomon and digivolved it into Gekkomon for 0 in the breeding area. "
            "Hand: Tomoro Tenma & Kyo Sawashiro (costs 4), Kyo Sawashiro (costs 3), Cougarmon ST23-03, e-Pulse. Their battle area is empty.",
            "What do you do with your 0 memory?",
            ("Pass: they start with 3.",
             "Tomoro & Kyo: they start with 4, but it's your core Tamer.",
             "Kyo: they start with 3."),
            "C",
            "Passing hands them 3 anyway, so Kyo for 3 is free: a Tamer at no tempo cost. "
            "Tomoro & Kyo hands them 4, and its +1 memory needs them to have a Digimon in the battle area, which they don't yet. "
            "Gekkomon into Cougarmon in breeding for 2 (they start with 2) is the other good play. Tomoro & Kyo waits until it pays.",
            "Turn 1 going first: Kyo (gives 3, the same as passing) or Lv3 to Lv4 in breeding (gives 2). Never Tomoro & Kyo.",
            "SIM",
            "Goldfish simulator: reserving setup memory for a Tamer cut no-Tamer-by-turn-2 games from 22% to 14%.",
        ),
        Puzzle(
            "Any", "Opening",
            "You go second. They passed you 3 and kept their Lv3 in their breeding area. You hatched Kekkomon and digivolved into "
            "Liollmon BT25-032 for 0. Hand: Tomoro Tenma & Kyo Sawashiro (4), Kyo Sawashiro (3), Cougarmon ST23-03, Atratusmon.",
            "Which line?",
            ("Tomoro & Kyo: they start with 1.",
             "Kyo, then Liollmon into Cougarmon in breeding for 2: they start with 2.",
             "Kyo, then pass: they start with 3."),
            "A",
            "Tomoro & Kyo is the core Tamer: every turn it puts a card of fuel under itself, plus 1 memory once they have a Digimon out. "
            "Playing it for 4 from 3 ends your turn at -1, so they start with just 1. "
            "Kyo then Cougarmon gives them 2 and leaves the better Tamer in hand. It gains no memory today, and it doesn't need to.",
            "Turn 1 going second (3 memory): hatch, Lv3, Tomoro & Kyo for 4 ending at -1. Otherwise Kyo for 3, then a Lv4 in breeding.",
            "SIM",
            "Goldfish simulator (Play Rules sheet of glowing-dawn-theorycraft.xlsx).",
        ),
        Puzzle(
            "vs TS Mervamon", "Memory",
            "Their board: 2 Homeros and Mervamon. Nothing else of theirs gains memory at the start of their turn. "
            "You've done everything you need this turn and can end it handing them any amount you like.",
            "How much memory should they start their turn with?",
            ("2 memory", "3 memory", "4 memory", "6 memory"),
            "C",
            "Homeros: at the start of their main phase it gains 1 memory, then at 5 or more it suspends itself and draws 1. "
            "A suspended Homeros can't pay for its end-of-turn replay of Mervamon's effect. "
            "From 4, the first Homeros takes them to 5 and suspends, the second to 6 and suspends: no replays. "
            "From 3, one Homeros stops at 4 and stays up. From 6, both still suspend, but you've given away 2 memory. Each Homeros that suspends draws them a card; that's the price.",
            "Pass Homeros exactly 4: every Homeros reaches 5 and suspends itself. 5 or more only gifts memory.",
            "COUNTED + STATED",
            "Homeros BT24-102 card text; DigiCarding JSnmWFvks5E and the Melbourne report say 4-5.",
        ),
        Puzzle(
            "vs Toho Braves", "Attacking",
            "Your turn 3. They have 5 security and no blockers. Your Cougarmon ST23-03 (4000 DP, Barrier) came off e-Pulse last turn with "
            "nothing under it and can attack for 1 check. You can't win this turn; next turn is your kill turn.",
            "Attack with Cougarmon?",
            ("Yes: free damage, one fewer card to clear next turn.",
             "No: hold it and build for the kill.",
             "Yes: Barrier keeps it alive if the check is big."),
            "B",
            f"Against Toho a check is a gift. Each card it flips goes to their trash, where Kaguyamon replays Puppets and, pilots say, Susanoomon counts names. "
            f"{toho_free:.0%} of their cards give them a free play from security, and {toho_kills_lv4:.0%} beat a 4000 DP attacker. "
            "Barrier only saves Cougarmon by trashing your own security card, which you want on the kill turn. Take all 5 in one turn instead.",
            "You can't chip. Go for the kill or sit back; against Toho take all 5 security in one turn.",
            "STATED + COUNTED",
            "Peoria qjWEEf2UKxM ('chipping into Tamer security is how you lose'); Madrid vWJCKCJVDy0; Kaguyamon EX12-065 text; rates from Vaelthas's list.",
        ),
        Puzzle(
            "vs DATA SQUAD", "Board",
            "You go first. Your turn 2: Cougarmon ST23-03 (on Liollmon, on Kekkomon) is in your breeding area, a Tamer is out, and "
            "Murasamemon BT25-041 is in hand. Their turn 2 is next.",
            "What do you do with the Cougarmon stack?",
            ("Move it out and attack: Kekkomon's trick digivolves it cheaply.",
             "Move it out but don't attack.",
             "Digivolve it to Murasamemon in breeding and move it next turn."),
            "C",
            "Their turn 2 is built to delete a Lv4 or lower: Peckmon (x4) and Crowmon (x4) both do it, with 2-4 removals that turn. "
            "Anything at Lv4 in the battle area is gone. The breeding area can't be touched, so raise to Lv5 there and move on turn 3. "
            "Digivolving in breeding costs full memory instead of the Kekkomon discount; losing the stack costs more.",
            "Raise to Lv5 in breeding vs Toho Braves and DATS: both delete a Lv4 on sight on their turn 2. Move on turn 3.",
            "COUNTED + OBSERVED",
            "Peckmon BT26-072 and Crowmon BT26-076 text; Rayquon's list; DDOUGHY -_59naRfz6c, G-rvjwxTjIA.",
        ),
        Puzzle(
            "vs Jupitermon", "Attacking",
            "Your kill turn. They have Jupitermon: Wrath Mode and Aegiochusmon: Holy out, and 3 security. Your attackers: Atratusmon "
            "(on the field since last turn, so its immunity has run out) and Murasamemon BT25-041 (7000 DP).",
            "Who attacks first?",
            ("Murasamemon: let it soak up their triggers.",
             "Atratusmon.",
             "It doesn't matter: the triggers fire either way."),
            "B",
            "When their security is removed, Holy gives 3 of your Digimon -5000 and Wrath Mode gives one -15000 (each once per turn), "
            "and they pick the targets. Atratusmon's immunity starts only when it attacks or digivolves. "
            "If Murasamemon checks first, the -15000 goes on Atratusmon before it is immune, and Atratusmon dies. "
            "Atratusmon first: its When Attacking makes it immune before the first check.",
            "Make Atratusmon immune before the first check of the turn: attack with it first.",
            "OBSERVED + COUNTED",
            "Barcelona commentary mZ4GiLpJzEs ('the one crack'); Aegiochusmon: Holy BT26-029 and Wrath Mode BT26-103 text.",
        ),
        Puzzle(
            "vs Toho Braves", "Removal",
            "Kaguyamon (12000 DP, with cards under it) is their biggest Digimon and gives their TB and Puppet Digimon Blocker and Retaliation. "
            "You have memory for either Option side in hand: Eclipse Impact (Atratusmon) or Habakiri (Habakirimon). Atratusmon can attack.",
            "How do you deal with Kaguyamon?",
            ("Eclipse Impact: suspend it, then bottom-deck it.",
             "Attack with Atratusmon and let Kaguyamon block: the 12000s trade.",
             "Habakiri: -8000, then trash a security card for -5000 to all, and it's deleted."),
            "A",
            "Deleting Kaguyamon is what it wants: Fortitude plays it back, its On Deletion bottom-decks your lowest-level Digimon, "
            "and in battle Retaliation takes your attacker too. Bottom-decking isn't a deletion, so none of that fires and Evade can't save it. "
            "Expect Sanmyojin Arrival to drop a replacement when it leaves; it is still the best of the three.",
            "Bottom-deck, don't delete: Eclipse Impact on Kaguyamon, Ryugumon and Sirenmon-protected bodies.",
            "COUNTED + OBSERVED",
            "Kaguyamon EX12-065, Sanmyojin Arrival EX12-070 and Eclipse Impact ST23-09 text; Sao Paulo top 8 olBMZIKhl5g.",
        ),
        Puzzle(
            "vs TS Mervamon", "Removal",
            "Your attack turn. Minervamon (13000 DP with Homeros) is unsuspended and gives their Iliad Digimon Blocker on your turn. "
            "You have Armalizamon BT25-049 in hand with a Lv3 to digivolve, and Habakirimon's Option side (Habakiri).",
            "What do you do with Minervamon?",
            ("Habakiri it: -8000, then -5000 to all, and it's deleted.",
             "Digivolve into Armalizamon and suspend it.",
             "Attack, make it block, then finish it off."),
            "B",
            "Minervamon's On Deletion pays them: it plays a cost-5-or-lower Iliad card from hand for free, then De-Digivolves one of yours "
            "once for each Digimon they have. It also stocks the trash that Mervamon replays from. "
            "Suspended, it can't block this turn and nothing fires.",
            "Suspend Minervamon, don't delete it.",
            "OBSERVED + COUNTED",
            "KnTElixar 0iT08uRH52Q; GAO u0z_9HckvRM; Minervamon BT24-041 and Armalizamon BT25-049 text.",
        ),
        Puzzle(
            "vs Toho Braves", "Card choice",
            "Next turn you make your first Lv6 on Murasamemon BT25-041. Atratusmon and Habakirimon are both in hand and both cost 3 to "
            "digivolve. Their threats: Shishimamon, Amaterasumon, Susanoomon.",
            "Which Lv6?",
            ("Habakirimon: it trashes their security and has 'doesn't leave' protection.",
             "Whichever leaves more memory after the turn.",
             "Atratusmon."),
            "C",
            "Toho's removal is all Digimon effects: Amaterasumon's delete, Shishimamon's -3000 and Security Attack -1, Susanoomon's -DP to "
            "everything and placing your Digimon into their security. Atratusmon's immunity blanks every one. "
            "Habakirimon's 'doesn't leave' costs a security card each time and doesn't stop -DP. Watch for Ryugumon: pilots name it as Toho's answer.",
            "Atratusmon is the Lv6 in all four matchups. Habakirimon second.",
            "OBSERVED + COUNTED",
            "Sao Paulo top 8 7JFJMCXLEA0 (Atratusmon won game 1); Shishimamon EX12-046 and Susanoomon EX12-076 text; Brisbane H40YtjjjJbE.",
        ),
        Puzzle(
            "vs DATA SQUAD", "Card choice",
            "You have 4 memory for one Tamer this turn. In hand: Tomoro Tenma BT25-090 and Tomoro Tenma & Kyo Sawashiro ST23-13. "
            "They've shown Lilamon and Rosemon.",
            "Which Tamer?",
            ("Tomoro Tenma: +2 fuel whenever any Digimon suspends.",
             "Tomoro & Kyo.",
             "Neither: they'll just get locked."),
            "B",
            "Lilamon and Rosemon suspend your Tamers, and Lilamon and Rosemon: Burst Mode stop them from unsuspending. "
            "Tomoro pays for its +2 fuel by suspending itself, so a locked Tomoro makes nothing. "
            "Tomoro & Kyo's start-of-main fuel and memory has no suspend cost and keeps working while locked.",
            "Vs DATS, protect the Tamers, not the hand: lean on Tomoro & Kyo and have 2 Tamers out before their turn 2-3.",
            "COUNTED + OBSERVED",
            "Tomoro BT25-090, Tomoro & Kyo ST23-13, Lilamon ST24-10 and Rosemon: Burst Mode BT26-050 text; KnTElixar qiM2Bz92Vd0 (lost to double Rosemon).",
        ),
        Puzzle(
            "Any", "Card choice",
            "Cougarmon ST23-03 is your attacker. Next turn you want Atratusmon on top of a Lv5, attacking twice. In hand: Murasamemon BT26-031 "
            "(DUAL, 8000 DP), Monarchlizamon BT25-057 (DUAL, 8000 DP), Murasamemon BT25-041 (7000 DP). You'll have fuel for the unsuspend.",
            "Which Lv5 goes under Atratusmon?",
            ("Murasamemon BT26-031: the most DP.",
             "Monarchlizamon BT25-057.",
             "Murasamemon BT25-041."),
            "C",
            "The second attack comes from the Lv5's inherited [End of Attack] unsuspend (1 fuel). Murasamemon BT25-041 has it; the DUAL Lv5s don't, "
            "because a DUAL card's lower text is its Option side, not an inherited effect. "
            "On a DUAL base Atratusmon attacks once: 2 checks instead of 4. Keep the DUALs for their Option sides.",
            "Put the Lv6 on a non-DUAL Lv5 (Murasamemon ST23-04 / BT25-041, Monarchlizamon ST23-08): DUALs give no unsuspend.",
            "COUNTED + SIM",
            "Card text; Comprehensive Rules 2-3-11-5-1. Goldfish: the first Lv6 lands on a DUAL base in 30% of games.",
        ),
        Puzzle(
            "Any", "Odds",
            f"The Calculator says going all-in now wins about {go_now:.0%}. If you hold back, you think you survive their turn {survive:.0%} "
            f"of the time. Next turn you'd win {win_with:.0%} with your out and {win_without:.0%} without it, and you find it by then {find:.0%} of the time.",
            "Which line wins more often?",
            ("Go now.", "Wait for the out.", "About the same."),
            "A",
            f"Waiting: {survive:.0%} x ({find:.0%} x {win_with:.0%} + {1 - find:.0%} x {win_without:.0%}) = {wait:.0%}. Going now: {go_now:.0%}. "
            "Waiting feels safe because next turn's best case is high, but you only get there if you survive and find the out. "
            "Write the four numbers down and the choice is usually clear.",
            "Wait only if survive x (find x win with + miss x win without) beats your chance now.",
            "MATH",
            "goldfish/odds.py go_or_wait. Put your own numbers into Find my out.",
        ),
        Puzzle(
            "vs TS Mervamon", "Odds",
            f"They run {plasment} Wide Plasment (deletes all your lowest-DP Digimon) and you haven't seen one. "
            f"You've seen 15 of their 50 cards (board, trash, under stacks). They hold {hand} cards.",
            "Roughly how likely is it that they hold at least one?",
            tuple(f"About {x:.0%}" for x in hold_opts),
            closest(hold_opts, holds),
            f"Their unknown cards are deck, hand and security together: 50 - 15 = {unknown}, with {plasment} Wide Plasment among them. "
            f"A random {hand} of those {unknown} holds one {holds:.0%} of the time. {plasment / unknown:.0%} is the chance for a single card. "
            "This treats their hand as random: if they've searched, or held cards for turns, lean higher.",
            "Count their unknown pile (deck, hand and security together) before you decide to play around a card.",
            "MATH",
            "Wide Plasment x3 in the TS Mervamon list (digimonmeta guide). goldfish/odds.py; try it on Find my out.",
        ),
        Puzzle(
            "Any", "Odds",
            "You need Atratusmon and run 3. One is in your trash. One went to the bottom of your deck last turn with the other card "
            "Liollmon revealed and didn't take. Your deck has 28 cards, you have 4 face-down security cards, and you'll see 3 new cards next turn.",
            "Chance one of the 3 is Atratusmon?",
            tuple(f"About {x:.0%}" for x in out_opts),
            closest(out_opts, out),
            f"Only 1 Atratusmon is still unknown: the bottomed one is out of reach. The unknown pile is the 26 cards above the bottom two plus "
            f"your 4 security cards, 30 in all. 3 of 30 is {out:.0%}. Counting 2 copies in 28 cards gives {naive:.0%}: it forgets the bottomed "
            "copy, and that your out could be in security.",
            "Your outs are the copies you haven't seen. Your face-down security is part of the pile; cards you bottomed are not.",
            "MATH",
            "goldfish/odds.py p_find, tested against card-by-card simulation. Try it on Find my out.",
        ),
    ]
    for q in p:
        assert q.answer in LETTERS[:len(q.options)], q.question
        assert 2 <= len(q.options) <= 4, q.question
    assert math.isclose(out, 0.1), out
    return p
