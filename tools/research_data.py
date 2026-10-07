"""Research-derived data for the theorycraft workbook.

Everything here comes from `research/round1-timings.md`, `research/round2-playbooks.md`
and card text (`data/cardtext.json`, `tools/fetch_card_text.py`). Each value carries an
evidence tag so the workbook can show how much to trust it:

    OBSERVED  seen in a recorded game (n = number of games when small)
    STATED    a pilot or written guide says so
    INFERRED  reconstructed or estimated; the least certain
    COUNTED   counted from the regional list or read off card text; exact for that list
    SIM       measured by the goldfish simulator

Turn numbers are always the deck's OWN turns: "T2" = that player's second turn.
"""

from __future__ import annotations

from typing import NamedTuple

TAGS = {
    "OBSERVED": ("Seen in a recorded game. n = number of games when small.", "C6EFCE"),
    "STATED": ("A pilot or a written guide says so.", "DDEBF7"),
    "INFERRED": ("Reconstructed or estimated. The least certain; argue with these first.", "FCE4D6"),
    "COUNTED": ("Counted from the regional list or read off card text. Exact for that list.", "EDEDED"),
    "SIM": ("Measured by the goldfish simulator.", "E4DFEC"),
}


class Cell(NamedTuple):
    value: object
    tag: str
    source: str = ""


class Row(NamedTuple):
    label: str
    cells: tuple[Cell, Cell, Cell, Cell]
    basis: str = ""
    was: tuple | None = None  # the pre-research (list-inferred) value, per matchup


def c(value, tag, source=""):
    return Cell(value, tag, source)


ZERO = c(0, "COUNTED", "no such effect in the regional list")

# ------------------------------------------------------------------ win rates
# DigiLab matchup records from Glowing Dawn's side (wins, losses, ties; None = not shown).
# Win rate = W / (W + L), the way DigiLab reports it.
WINRATES = [
    ("Jupitermon", 105, 147, None, "Jupitermon page: 147-105 (58.3%); an earlier snapshot showed 57.8% over 238.", "Jupitermon also won Dusseldorf (Fish, 7-1)."),
    ("TS Mervamon (Homeros control)", 4, 21, 4, "TS Mervamon page: 21-4-4 (84%).", "Our worst matchup. 4 ties in 29 = time draws. A BT26 retrospective puts it at 37%; the small n makes both plausible."),
    ("Toho Braves (TB)", 62, 88, 14, "Toho Braves page: 88-62-14 (58.7%).", "Toho won Sao Paulo (Yuri, beat Glowing Dawn 2-1 in the top 8)."),
    ("DATA SQUAD Ravemon (Rose Rave)", 11, 13, 5, "DATA SQUAD page: 13-11-5 (54.2%).", "Closest matchup; n is small."),
]
EVENT_RESULTS = [
    ("Dusseldorf 2026-10-04 (181 players)", "11 Glowing Dawn pilots, 40% combined. The 4th place (Quang-Minh, 6-0-2) was one strong pilot.", "OBSERVED"),
    ("Sao Paulo 2026-09-19 (118 players)", "15 Glowing Dawn pilots, 36% combined.", "OBSERVED"),
    ("Gen Con 2026 (153 players, BT25 format)", "Glowing Dawn 3rd/5th/7th/8th. The drop since coincides with BT26 bringing TS Mervamon and boosting Jupitermon and Toho.", "OBSERVED"),
]

# ------------------------------------------------------------------ sim profiles
# The security rows are live formulas into the Matchups sheet (keys = its probability labels).
SECURITY_LINKS = [
    ("P(security Digimon >= 12000): kills Atratusmon / Habakirimon", "Kills a 12000 attacker (Atratusmon, Habakirimon)", (0.20, 0.34, 0.20, 0.20)),
    ("P(security Digimon >= 7000): kills a 7000 Lv5", "Kills a 7000 Lv5 attacker", (0.36, 0.38, 0.34, 0.34)),
    ("P(security Digimon >= 5000): kills a 4000 Lv4", "Kills a 4000 Lv4 attacker", (0.52, 0.52, 0.54, 0.50)),
    ("P(free Tamer from security)", "Gives them a free Tamer", (0.20, 0.20, 0.04, 0.20)),
    ("P(free play / resource from security)", "Free play / resource for them", (0.02, 0.04, 0.14, 0.08)),
    ("P(Crimson Blaze: wipe our <= 6000)", "Wipes our <= 6000 DP Digimon", (0.04, 0.00, 0.04, 0.00)),
]

PROFILE_SECTIONS = [
    ("Tempo", "Their own turn numbers. Research says every one of these decks bursts on its T2.", [
        Row("What their T1 does", (
            c("Lv4 in breeding (Tsunomon, Elecmon, Aegiomon), Inori. No attack.", "OBSERVED n=1", "DDOUGHY feature match kv58ncMwTMU, Jupitermon going second"),
            c("Tamer (Dan & Kanan), Central Town, a Lv3.", "OBSERVED n=1", "DDOUGHY casual -jFZg3bprFk"),
            c("Setup only: Lv3 in breeding, Island search, set Arrival or Analog Youth. Passes 2-3.", "OBSERVED ~20 games", "Sao Paulo top 8 7JFJMCXLEA0, final LtKXMou-Ju0, Singapore final Ky_clVcx92s; medium-high confidence"),
            c("1-2 Tamers (dual Tamer via DNA Charge or GeoGreymon).", "OBSERVED n=3", "-_59naRfz6c, G-rvjwxTjIA, -jFZg3bprFk"),
        )),
        Row("First turn they have a battle-area Digimon (switches on Tomoro & Kyo's memory)", (
            c(2, "OBSERVED n=1", "Aegiomon leaves breeding on J-T2 (kv58ncMwTMU)"),
            c(2, "INFERRED", "T1 plays a Lv3; whether it leaves breeding is not recorded"),
            c(2, "OBSERVED", "T1 keeps the Lv3 in breeding"),
            c(2, "INFERRED", "not recorded"),
        ), "drives the sim's opp_board_turn", (2, 2, 2, 2)),
        Row("Burst turn: first Lv6 and first removal", (
            c("T2", "OBSERVED n=1", "Lv5, Lv6 and Lv7 (Wrath Mode) in one turn, kv58ncMwTMU"),
            c("T2", "OBSERVED n=1", "Minervamon plays Homeros and removes the same turn, -jFZg3bprFk"),
            c("T2", "OBSERVED", "Shishimamon (Lv5), Execute, then a Lv6; game T3 on the play, T4 on the draw"),
            c("T2", "OBSERVED n=2-3", "Peckmon/Crowmon/Ravemon chain. STATED (G-iNe0mpPC4): 'turn three is probably more likely'"),
        ), "the turn to brace for", ("T4", "T4-T5", "T3", "T4")),
        Row("First attack", (
            c("T2", "OBSERVED n=1", "2 checks, then a Wrath Mode end-of-turn swing: 4 checks that turn"),
            c("T3", "OBSERVED n=1", "Mervamon -DP then Alliance swings. STATED (JSnmWFvks5E): attacks only when safe"),
            c("T2", "OBSERVED", "with Execute"),
            c("T2", "INFERRED", "attack on the combo turn not recorded"),
        ), "", ("T4", "T5+", "T3", "T3")),
        Row("Fastest win seen", (
            c("T3", "OBSERVED n=1", "won J-T3 going second (game T6) vs Toho"),
            c("T5+ or a time draw", "STATED", "JSnmWFvks5E: 'goes to time constantly'; 4 ties in 29 vs Glowing Dawn"),
            c("T3", "OBSERVED", "game T5 on the play, T6 on the draw; their losses run T6-T9"),
            c("T4-T5", "OBSERVED n=3, very low confidence", "games ended game T7-T9 either way"),
        ), "", ("T5-6", "T6+", "T5", "T5-6")),
    ]),
    ("Removal (by effect type)", "Atratusmon's immunity stops Digimon effects only; Barrier stops battle deletion only; Habakirimon's 'doesn't leave' does not stop -DP.", [
        Row("Removal effects on their burst turn (all types)", (
            c("2 on T2, about 5 on T3", "OBSERVED n=1", "kv58ncMwTMU"),
            c("1 on T2, then 2+ per turn", "OBSERVED n=1", "-jFZg3bprFk; the later rate is qualitative"),
            c("1-2 on T2; Susanoomon wipe from T3", "OBSERVED", "about 20 game narrations"),
            c("2-4 on T2", "OBSERVED n=2-3", "-_59naRfz6c, G-rvjwxTjIA"),
        )),
        Row("Delete Lv4 or lower (Digimon effect)", (
            ZERO, ZERO,
            c("1 per turn from T2", "COUNTED", "Kokeshimon x4 (deletes one of their own as the cost), Musyamon"),
            c("1-2 on T2", "OBSERVED", "Peckmon x4, Crowmon x4 on the combo turn"),
        ), "our Kekkomon / Cougarmon base dies on sight", ("0", "0", "1 from T2", "1 from T2")),
        Row("Delete lowest DP (Digimon effect)", (
            c("0.3 per turn from T3", "INFERRED", "Dianamon x1 (deletes an unsuspended Digimon), Chronomon x1; not seen in a game"),
            c("1 per turn from T3", "INFERRED", "Bacchusmon: deletes our lowest DP whenever a Digimon is played or digivolved by effect; plan B per DigiCarding"),
            c("1 per turn from T2", "OBSERVED", "Amaterasumon is a common T2 Lv6; blanked by Atratusmon at Sao Paulo"),
            ZERO,
        ), "", ("0", "1 from T4", "1 from T4", "0")),
        Row("Big -DP or delete our highest (Digimon effect)", (
            c("1 on T2, 2-3 on T3", "OBSERVED n=1", "Jupitermon -13000 and Wrath Mode -15000; both last until OUR turn ends"),
            c("1 per turn from T3", "OBSERVED n=1", "Mervamon -4000 per Iliad/TS card; lasts until our turn ends"),
            c("all of ours -15000 to -18000 from T3", "OBSERVED", "Susanoomon (-3000 per color under it, their turn only); late if the trash lacks names"),
            c("1 on T2, repeatable", "OBSERVED", "Ravemon deletes our highest DP (when digivolving / end of attack, 2 fuel per repeat)"),
        ), "", ("1 from T4", "0", "0", "1 from T4")),
        Row("De-Digivolve (Digimon effect)", (
            c("0.5 per turn from T2", "INFERRED", "Aegiochusmon: Blue x2 and Holy's inherit; chosen 'by need' (cardsrealm guide)"),
            c("1+ per turn from T2", "OBSERVED n=1", "Minervamon: De-Digivolve 1 for each Digimon they have"),
            ZERO, ZERO,
        ), "", ("0", "2 from T4", "0", "0")),
        Row("Option removal (ignores Atratusmon's immunity)", (
            c("0.5 per turn from T3", "INFERRED", "Wide Plasment used on J-T3 (n=1); Fish runs 1 Wide Plasment, 2 Crimson Blaze, 1 Blinding Ray"),
            c("0.5 per turn from T3", "STATED", "Wide Plasment x3 deletes all our lowest DP; costs 1 more per their security, so they burn security first (digimonmeta guide); Kanan / Dan & Kanan cast it at end of turn"),
            c("0.3 per turn from T2", "INFERRED", "Crimson Blaze x2, Kunlun's Imperial Decree x1"),
            ZERO,
        ), "", ("0.3 from T3", "0.5 from T5", "0.3 from T3", "0")),
        Row("Place our Digimon into their security (Digimon effect)", (
            ZERO, ZERO,
            c("1 per Susanoomon attack from T3", "OBSERVED", "Susanoomon When Attacking; Atratusmon immunity and Habakirimon's 'doesn't leave' both stop it"),
            ZERO,
        )),
    ]),
    ("Locks and disruption", "", [
        Row("Suspend / can't-attack locks on our Digimon", (
            c("0.3 per turn", "INFERRED", "Dianamon's inherit: one of ours can't suspend"),
            c("0.5 per turn from T3", "OBSERVED", "Bacchusmon suspends whatever digivolves (GAO LCQ u0z_9HckvRM); Chaosmon x1"),
            c("1 per turn from T2 with Ryugumon", "COUNTED + STATED", "Ryugumon: whenever they play or digivolve, 1 of ours can't suspend or use When Digivolving until our turn ends. Shellmon from security: can't attack or block"),
            c("1 per turn from T2-T3", "OBSERVED, low confidence", "Lilamon, Rosemon, Rosemon Burst Mode"),
        ), "", ("0", "0.5 from T5", "0.3 from T3", "0.7 from T4")),
        Row("Tamer lock / stun (switches off Tomoro's and Kyo's fuel triggers, which pay by suspending the Tamer)", (
            ZERO, ZERO,
            c("0.5 per turn from T2", "STATED", "Karakurumon suspends a Tamer and it can't unsuspend: TB's only way to touch Tamers (Brisbane profile H40YtjjjJbE)"),
            c("1 per turn from T2-T3", "OBSERVED + STATED", "Rosemon / Lilamon suspend Tamers; Romulo (TR9dZjK9XH0) calls this the worst problem for Glowing Dawn"),
        )),
        Row("Execute / extra attacks into our board", (
            c("1 per turn from T2", "OBSERVED n=1", "Wrath Mode end-of-turn attack"),
            c("late only", "STATED", "Dianamon unsuspends an attacker, Dan & Kanan extra attack, Alliance"),
            c("1 per attack turn from T2", "OBSERVED + STATED", "Onibimon egg Execute"),
            c("0.5 per turn from T2", "INFERRED", "Keenan Crier grants Execute when our hand or their Tamer stack is trashed"),
        ), "", ("0", "0", "1 from T3", "0.5 from T4")),
        Row("Hand rip", (
            ZERO, ZERO, ZERO,
            c("2-6 cards on T2-T3", "OBSERVED + STATED", "Crowmon / Ravemon / Peckmon; about 9 memory rips 6 (Japanese guide). Glowing Dawn refills with e-Pulse / Makoto"),
        )),
        Row("Leave-protection on their key Digimon", (
            c("Jupitermon 'doesn't leave' by trashing security; Barrier inherits; Holy shields 1 Digimon from -DP and bounce", "STATED + COUNTED", "cardsrealm guide; card text"),
            c("Sirenmon dies instead of any other Iliad body leaving; Jupitermon DUAL saves to security; Reboot + Blocker on every Iliad body", "STATED + COUNTED", "digimonmeta guide, DigiCarding; card text"),
            c("Arrival plays a Lv6 when a Lv5+ leaves (bottom-deck included); Kaguyamon rebuys Puppets; Ryugumon Evade + Barrier", "OBSERVED + COUNTED", "Sao Paulo games; card text"),
            c("Lilamon inherit 'doesn't leave'; Ravemon replays from security at the end of our turn", "OBSERVED + COUNTED", "card text"),
        )),
    ]),
    ("Their defence on our turn", "", [
        Row("Blockers after their T2", (
            c(1, "OBSERVED n=1", "Wrath Mode"),
            c(2, "INFERRED", "every Iliad Digimon has Blocker + Reboot under Minervamon / Mervamon"),
            c("1, or 4 with Kaguyamon (all Retaliation)", "STATED", "Kaguyamon is the default T2 Lv6 (Brisbane H40YtjjjJbE, Rotherham MDqMIDDu1Jo)"),
            c(1, "COUNTED + STATED", "Peckmon; 'no meaningful blocker plan' (East I__Sik4t_A0)"),
        ), "", (1, 2, 1, 2)),
        Row("Blockers after their T3", (
            c("2-3", "INFERRED", ""),
            c("4-5", "STATED", "board of Homeros, 2 Jupitermon, Mervamon, Sirenmon by about T4 (DigiCarding JSnmWFvks5E)"),
            c("3-4", "INFERRED", ""),
            c(1, "INFERRED", ""),
        ), "", (3, 5, 3, 3)),
        Row("Blocker DP (typical)", (
            c("8000 (Blue) / 16000 (Wrath)", "COUNTED"),
            c("13000+ (Mervamon aura +2000)", "COUNTED"),
            c("16000 (Susanoomon); Puppets 5000-12000", "COUNTED"),
            c("5000 (Peckmon)", "COUNTED"),
        ), "", (8000, 13000, 16000, 5000)),
    ]),
    ("Their attacks into us", "Checks into our security per turn.", [
        Row("Checks on their T2", (
            c(4, "OBSERVED n=1", "two attacks plus the Wrath Mode end-of-turn swing"),
            c(0, "OBSERVED n=1", ""),
            c("1-2", "OBSERVED", "Ryugumon attack + unsuspend is 'virtually two checks'"),
            c(1, "INFERRED", ""),
        ), "", (0, 0, 1, 1)),
        Row("Checks on their T3", (
            c("lethal", "OBSERVED n=1", ""),
            c("1-2", "OBSERVED n=1", "Alliance swings"),
            c("lethal if Susanoomon resolves", "OBSERVED", ""),
            c(2, "INFERRED", ""),
        ), "", (1, 0, 2, 1)),
        Row("Checks on their T4+", (
            c("lethal", "OBSERVED n=1", ""),
            c("2+ when safe", "STATED", "DigiCarding: 'the point of no return'"),
            c("lethal", "OBSERVED", ""),
            c("2+; Rosemon Burst Mode trashes security repeatedly", "OBSERVED", "-jFZg3bprFk"),
        ), "", (2, 1, 3, 2)),
        Row("Attacker DP (early / late)", (
            c("5000 / 16000", "COUNTED"), c("8000 / 13000", "COUNTED"), c("7000 / 16000", "COUNTED"), c("7000 / 12000", "COUNTED"),
        ), "", ("5000 / 13000", "8000 / 13000", "7000 / 12000", "7000 / 12000")),
        Row("Punish when WE check their security", (
            c("trash our top security; Holy: 3 of ours -5000; Wrath: 1 of ours -15000", "COUNTED", "Jupitermon [All Turns], Aegiochusmon: Holy [All Turns], Wrath Mode [All Turns], each once per turn"),
            ZERO, ZERO, ZERO,
        ), "", (1, 0, 0, 0)),
    ]),
    ("Memory", "", [
        Row("Memory they pass us", (
            c("7 on T2; another pilot choked Glowing Dawn to 1", "OBSERVED", "kv58ncMwTMU; V-Tamer DhHn8jxncWY"),
            c("about 7 early, about 3 later", "STATED", "digimonmeta guide"),
            c("2-3", "OBSERVED + STATED", "'not good with memory'; Yuri passed Glowing Dawn 3 instead of 4-5"),
            c("low", "OBSERVED", "deliberately avoided gaining memory to pass less (OyZ9g4jRbe0)"),
        ), "the sim assumed 3"),
        Row("Memory they gain per turn (beyond our pass)", (
            c(3, "OBSERVED n=1", "3 Tamers out on J-T2; Inori gains 1 only at 4 or less"),
            c(3, "INFERRED", "Homeros x4 gain 1 (then self-suspend at 5+); Kanan gains 1 at 4 or less"),
            c(1, "COUNTED", "Kunlun x2; Analog Youth regains memory after Execute deletions"),
            c(2, "INFERRED", "Keenan / Yoshino tuck: draw 1 + 1 memory each; dual Tamer +1 when we have a Digimon"),
        ), "", (2, 3, 1, 2)),
        Row("Our best end-of-turn pass to them", (
            c("as low as possible; 6 lost a game to a double swing", "OBSERVED", "DhHn8jxncWY"),
            c("exactly 4", "COUNTED + STATED", "Homeros: +1, then at 5+ it suspends and loses its end-of-turn replay. They order Homeros first, so 4 suspends every copy; each memory past 4 is a gift"),
            c("as low as possible", "STATED", "Brisbane: 'you cannot give this deck copious amounts of memory'"),
            c("as low as possible", "STATED", "their T2 combo costs about 8-11 memory (G-iNe0mpPC4)"),
        )),
    ]),
    ("Their security", "", [
        Row("How they use their own security", (
            c("Burns it as fuel (Inori, Wrath, Jupitermon costs its security count); wants 1-3; at 0 Inori and the inherits switch off", "STATED", "cardsrealm guide; Security Check WSfJyTi8zh4"),
            c("Takes it early so Wide Plasment is cheap", "STATED", "digimonmeta guide; DigiCarding"),
            c("Susanoomon trashes ours and recovers theirs; Island recovers; a security Shellmon / Island play stops our attack", "STATED + OBSERVED", "Brisbane H40YtjjjJbE; Sao Paulo 7JFJMCXLEA0"),
            c("Ravemon goes face-up into security and replays at the end of our turn", "OBSERVED", ""),
        )),
    ]),
]

# ------------------------------------------------------------------ play rules
# (rule, what to do, number or evidence behind it, tag)
RULES = [
    ("Mulligan for a Tamer", "Keep a Lv3 plus a Tamer or a way to find one (e-Pulse, Gekkomon, Liollmon). Pilots: a Tamer later than T1-T2 never banks enough fuel; a no-Tamer game is 'a wrap' in Bo1.",
     "Goldfish: P(Lv3 in 5) 69%, 90% with the Lv3 mulligan. Both losses in the GAO and Security Check games had no Tamer until T3-4.", "STATED + SIM"),
    ("T1 going first (0 memory)", "Hatch, Lv3 for 0, then Kyo (gives 3, same as passing) or Lv3 -> Lv4 in breeding for 2 (gives 2, better than passing). Never Tomoro & Kyo: giving 4 for a Tamer that pays nothing until their board exists.",
     "Goldfish: no-Tamer-by-T2 fell from 22% to 14% once setup spending reserved memory for the Tamer.", "SIM"),
    ("T1 going second (3 memory)", "Hatch, Lv3, Tomoro & Kyo for 4 ending at -1. Otherwise Kyo for 3, then Lv4 in breeding.", "Going second kills 0.4 turns faster (3.94 vs 4.35).", "SIM"),
    ("T2", "Move the Lv4 (or the Lv3 if a Tamer is out), attack first because it is free, let Kekkomon digivolve at -2, then the second Tamer, then spend down to -3. Exception: against Toho and DATS keep it in breeding (below).",
     "Attack-time digivolve costs 0-1 vs 3 pre-attack.", "SIM"),
    ("Never pre-digivolve a stack that still has Kekkomon's trick", "Pre-attack digivolving only for stacks without Kekkomon (e-Pulse bodies, recursion) or at 0 fuel.", "Trick + Cougarmon ST23-03: 3 - 2 - 2 = 0.", "SIM"),
    ("Don't spend fuel early", "Fuel is the kill. Count what the kill needs (4-5 fuel plus 4 memory; 4 fuel with BT25 Murasamemon paying with security) and know what is under each Tamer.",
     "Pilots (cardsrealm, Peoria, Nima). Goldfish: fuel >= 3 at end of T2 only 20%.", "STATED + SIM"),
    ("You can't chip", "Go for the kill or sit back. A 1-check poke gives Jupitermon, Mervamon or DATS a free Tamer 20% of the time, costs us a security card vs Jupitermon, and feeds Toho's Susanoomon trash.",
     "Free-Tamer rate from the lists; 'chipping into Tamer security is how you lose' (Peoria qjWEEf2UKxM). One dissent: Nima would chip Jupitermon to 2-4 and race.", "COUNTED + STATED"),
    ("Leave 1-2 spare memory on the kill turn", "Take the line with slack over the exact-memory line, so a Tamer flipped from their security doesn't end the turn.", "Peoria took the slack line and hit a security Tamer.", "OBSERVED"),
    ("Build the attacking stack on a Barrier base", "Liollmon BT25-032 -> Cougarmon ST23-03 -> non-DUAL Lv5 -> Lv6: two Barriers, the -2, and the unsuspend.", "4-check turn flips a 12000+ security Digimon 59% (81% vs Mervamon).", "COUNTED"),
    ("Enter the Lv6 turn with 4+ security against the meta", "Barrier saves and Habakirimon's protection each cost a security card. Skip Cougarmon BT26-026 and Habakirimon self-trash costs when behind on security.",
     "Goldfish policy burned to 2; against the meta that is the losing resource.", "SIM"),
    ("Atratusmon is the Lv6 in all four matchups", "Its immunity blanks Jupitermon, Ravemon, Amaterasumon, Shishimamon and Susanoomon (-DP and security placement are all Digimon effects). Habakirimon second: vs Toho for the security trash and 'doesn't leave', vs Jupitermon for its Option side.",
     "Atratusmon won Sao Paulo top-8 game 1 vs Toho; a guide calls it 'brutal' for Toho. Corrects the old 'Habakirimon into Toho' rule.", "OBSERVED + COUNTED"),
    ("Make Atratusmon immune before the first check of the turn", "Attack with Atratusmon first. Every check against Jupitermon fires Holy (-5000 to 3) and Wrath Mode (-15000 to 1); -DP that lands before the immunity stays ('the one crack').",
     "Barcelona commentary (mZ4GiLpJzEs); card text.", "OBSERVED + COUNTED"),
    ("Bottom-deck, don't delete", "Use Eclipse Impact (Atratusmon's Option side) on Kaguyamon, Ryugumon and Sirenmon-protected bodies: no Retaliation, no On Deletion, Evade can't save it. It still triggers Toho's Arrival.",
     "Card text; Sao Paulo top 8 (olBMZIKhl5g). Corrects the research note that credited the bottom-deck to Habakirimon.", "COUNTED + OBSERVED"),
    ("Raise to Lv5 in breeding vs Toho Braves and DATS", "Both delete a Lv4 on sight on their T2. Move on T3 instead of T2.", "Peckmon x4, Crowmon x4 (DATS T2 combo); Kokeshimon x4, Musyamon.", "COUNTED + OBSERVED"),
    ("Pass Homeros exactly 4", "Against TS Mervamon end your turn handing over 4: every Homeros gains 1, hits 5 and suspends itself, so none can replay Mervamon / Minervamon at their end of turn. 5+ only gifts memory.",
     "Homeros card text; JSnmWFvks5E and the Melbourne report say 4-5.", "COUNTED + STATED"),
    ("Suspend Minervamon, don't delete it", "Deleting it replays an Iliad card and De-Digivolves, and fills the trash for Mervamon's replay. Armalizamon suspends a blocker; remove Sirenmon first (it saves every other Iliad body).",
     "KnTElixar 0iT08uRH52Q; GAO u0z_9HckvRM; card text.", "OBSERVED + COUNTED"),
    ("End your turn with Jupitermon at 0 security", "At 0, Inori and the Aegiochusmon inherits can't trigger. Leaving them at 3 loses to Wrath Mode. Their Jupitermon recovers 2 at 1 or fewer, so finish the turn at 0, not 1.",
     "Security Check WSfJyTi8zh4 (opponent's view); card text.", "STATED + COUNTED"),
    ("Vs DATS, protect the Tamers, not the hand", "Hand rip doesn't matter (e-Pulse / Makoto refill). The Rosemon Tamer lock is the loss: it shuts off Tomoro's and Kyo's suspend-paid fuel, so lean on Tomoro & Kyo (no suspend needed), have 2 Tamers before their T2-T3 and keep a second attacker.",
     "KnTElixar qiM2Bz92Vd0: Glowing Dawn shrugged off the rip and lost to double Rosemon; Romulo TR9dZjK9XH0.", "OBSERVED + STATED"),
    ("Keep a second attacker", "Lilamon, Rosemon BM, Chaosmon, Karakurumon and Ryugumon each pin one stack (no unsuspend, no attack).", "Ryugumon pins one of ours each time they play or digivolve.", "COUNTED"),
]
FLAWS = [
    ("Half the Lv5s are DUALs", "First Lv6 lands on a DUAL base 30% of games: no unsuspend, no -3 trigger. A 4-check Atratusmon turn becomes 2.", "4th BT25-041 and 2nd ST23-04 for one of each DUAL; the regional list runs 6 non-DUAL."),
    ("Fuel lags the curve", "Fuel >= 3 at end of T2 only 20% (15% going first); 50% at end of T3. Multi-attack turns are a T4 feature.", "Reina Sakuya gains fuel on their attacks too."),
    ("Tamer-less starts", "14% no Tamer by T2; a third of going-first games have fewer than 2 Tamers by end of T3.", "+1 Kyo -1 e-Pulse: -3 pts no-Tamer, no speed change."),
    ("Going first costs 0.4 turns", "Lv6 by end of T2: 22% first vs 60% second.", "Choose second on the roll, pending matchup models. No pilot states a preference."),
    ("Dead openings", "10% of opening hands hold 2+ Lv6s; the policy mulligans 31% of hands.", ""),
    ("Security as a resource", "Policy ends games at 4.2 security; every Barrier save costs one. Against 20-34% killer rates per check this is the binding constraint.", ""),
    ("No Barrier on Gekkomon / Chiropmon / Liollmon BT26 bases", "Those stacks die to the first big security card.", "Prefer Liollmon BT25 in the breeding line when the Lv6 will go on it."),
    ("Every opponent bursts on its T2", "Research puts the first Lv6 and first removal of all four meta decks on their own T2; our goldfish kill is T4. We must survive one burst turn, usually two.", "Matchup sims (next step) measure how often we do."),
]

# ------------------------------------------------------------------ playbooks
# sheet name -> matchup index, header facts, sections of (point, tag, source)
PLAYBOOKS = {
    "vs Jupitermon": {
        "matchup": 0,
        "facts": [
            ("Their burst turn", "J-T2: Lv5, Lv6 and Lv7 in one turn, 2 removals, 4 checks (n=1)"),
            ("Their fastest win", "J-T3 (n=1)"),
            ("Our Lv6", "Atratusmon; Habakirimon's Option side as the board wipe"),
            ("End our turn with", "them at 0 security; pass as little as possible (6 lost a game)"),
        ],
        "sections": [
            ("Their plan", [
                ("Wants Aegiomon and Inori early via Elecmon / Tapirmon searches; a no-Rookie hand bricks and can't interact.", "STATED + OBSERVED", "cardsrealm guide; KnTElixar 32K4To1jzKY"),
                ("Security is fuel: burns its own security to fire Inori (free Aegiochusmon digivolve) and Tsunomon; picks Holy (protection, -5000 x3), Blue (De-Digivolve, unsuspend, Blocker) or P-213 (Rush) by need.", "STATED", "cardsrealm guide"),
                ("Jupitermon costs its security count; Recover +2 needs 1 or fewer (2 -> 1 -> 3). Pilots want 1-3 security and never 0.", "STATED + COUNTED", "cardsrealm guide; Barcelona mZ4GiLpJzEs"),
                ("J-T2 seen: Aegiomon out, Blue free via Inori, Jupitermon for 3, Wrath Mode for 5, 2 removals, 4 checks, own security 3 -> 0 -> 3, passed 7.", "OBSERVED n=1", "DDOUGHY kv58ncMwTMU"),
                ("J-T3 seen: Blinding Ray, Wide Plasment, Arts Digivolve into Jupitermon, -13000 twice, Wrath -15000: about 5 removals, won.", "OBSERVED n=1", "kv58ncMwTMU"),
                ("Protection: Barrier inherits, Jupitermon 'doesn't leave' by trashing security, Holy shields 1 Digimon from -DP, stack trash and bounce until our turn ends.", "STATED + COUNTED", "cardsrealm guide; card text"),
            ]),
            ("How they beat Glowing Dawn", [
                ("DigiLab: Glowing Dawn 41.7% (105-147).", "OBSERVED", "digilab.cards"),
                ("No Digimon on board (denies Tomoro & Kyo's memory) and choke us to 1.", "OBSERVED", "V-Tamer DhHn8jxncWY"),
                ("'All we got to do is not put ourselves to zero and hit a Tamer': they avoid checking into our security Tamers.", "OBSERVED", "Barcelona mZ4GiLpJzEs (BT25)"),
                ("-13000 / -15000 last until our turn ends. Applied before Atratusmon turns immune, they stay: 'the one crack'.", "OBSERVED + COUNTED", "Barcelona commentary; card text"),
                ("Every check we make: Jupitermon trashes our top security, Holy gives 3 of ours -5000, Wrath gives 1 of ours -15000.", "COUNTED", "card text"),
                ("Options ignore immunity: Wide Plasment (deletes all our lowest DP), Crimson Blaze in security (wipes <= 6000), Blinding Ray.", "COUNTED", "Fish's list"),
            ]),
            ("Our plan", [
                ("Tamer on T1-T2. Kyo (the memory Tamer) is 'fundamental' here.", "STATED", "Romulo TR9dZjK9XH0"),
                ("Our T1-T2: evolve in the back and play around the -5000 (don't expose a 4000-5000 DP Digimon).", "STATED", "Peoria qjWEEf2UKxM; Hoang Zero"),
                ("Their T2: expect -13000 on our best Digimon and about 4 checks into us. Nothing we leave out survives; keep the stack in breeding.", "OBSERVED n=1", "kv58ncMwTMU"),
                ("Our kill turn: attack with Atratusmon first so it is immune before any check fires Holy or Wrath.", "INFERRED", "card timing; follows from 'the one crack'"),
                ("Vs a lone Jupitermon: use the non-DUAL Lv6's Option to force its protection (costs their security), then digivolve, become immune and kill it.", "STATED", "Romulo TR9dZjK9XH0"),
                ("Board wipe: Habakirimon's Option side (-8000 to one, then -5000 to all). Lingering -13000 kills Atratusmon, so the Option side is the safer play; won 2-1 this way, including Dianamon before it stripped fuel.", "OBSERVED", "V-Tamer DhHn8jxncWY"),
                ("End the turn with them at 0 security (not 1: Jupitermon recovers 2 at 1 or fewer).", "STATED + COUNTED", "Security Check WSfJyTi8zh4; card text"),
                ("Unresolved: Nima would chip Jupitermon to 2-4 and race; every other pilot says never chip. The matchup sim will test both.", "STATED", "Nima CoEe9A1S5mU vs Peoria qjWEEf2UKxM"),
                ("Going first or second: Jupitermon gave Glowing Dawn first in game 3 and Glowing Dawn won.", "OBSERVED n=1", "DhHn8jxncWY"),
            ]),
            ("Their misplays to punish", [
                ("Going to 0 security; skipping Elecmon's start-of-main pickup (costs the Jupitermon memory); burning security with no payoff; wasting Holy copies; suspending Homeros for the draw; no-Rookie brick; attacking into our security Tamers.", "STATED + OBSERVED", "cardsrealm; KnTElixar bewyBp4hr_c, 32K4To1jzKY; Barcelona"),
            ]),
            ("Corrections and unknowns", [
                ("Claim rejected: 'Inori's free Lv5 needs 3 or fewer memory'. Inori BT24-084's free digivolve has no memory condition; only its start-of-main +1 needs 4 or less.", "COUNTED", "Hi4g8MRm-x0 vs card text"),
                ("No data: their key turn against Glowing Dawn specifically, and what they target first.", "INFERRED", ""),
            ]),
        ],
    },
    "vs Homeros": {
        "matchup": 1,
        "facts": [
            ("Their burst turn", "T2: Minervamon plays Homeros, first removal (n=1); Mervamon T3"),
            ("Their fastest win", "slow; T5+ or a time draw"),
            ("Our Lv6", "Atratusmon (but Mervamon -DP and Wide Plasment get around it)"),
            ("End our turn with", "exactly 4 memory for them"),
        ],
        "sections": [
            ("Their plan", [
                ("Keeps any hand with a Lv3; 12 Lv3 searchers because 'those level sixes are expensive'.", "STATED", "DigiCarding JSnmWFvks5E"),
                ("Lands an ADAMAS Tamer early via Aegiomon and takes its own security early, because Wide Plasment costs 1 more per security card.", "STATED", "digimonmeta guide; DigiCarding"),
                ("T2 seen: Minervamon plays Homeros and removes the same turn.", "OBSERVED n=1", "-jFZg3bprFk"),
                ("Full combo: Mervamon plays Homeros + a searcher and gives -4000 per Iliad/TS card until our turn ends; Homeros replays it at their end of turn; the Tamer casts Wide Plasment, Arts Digivolves, plays Bacchusmon and Sirenmon.", "STATED", "digimonmeta guide"),
                ("Plan B: Ceresmon / Bacchusmon suspend board. Bacchusmon suspends whatever digivolves and deletes our lowest DP when something is played by effect.", "STATED + COUNTED", "DigiCarding; card text"),
                ("Grinds: Coronamon and Mervamon replay pieces from the trash; this is why it wins long games. Deck-out is a real risk for them.", "STATED", "DigiCarding"),
                ("Memory: passes about 7 early, chokes to about 3 later; Kanan lets them pass 3 and still cast an Option.", "STATED", "digimonmeta guide; DigiCarding"),
            ]),
            ("How they beat Glowing Dawn", [
                ("DigiLab: Glowing Dawn 16% (4-21-4); a BT26 retrospective says 37%.", "OBSERVED", "digilab.cards"),
                ("Every Iliad body has Blocker + Reboot on our turn: blockers are always up.", "COUNTED", "Minervamon / Mervamon card text"),
                ("Sirenmon's redirect and the leave-protections (back to security) undo a 5-check push.", "STATED", "digimonmeta guide"),
                ("Mervamon's -DP lasts through our turn and Wide Plasment is an Option: both get around Atratusmon's immunity.", "COUNTED", "card text"),
                ("GAO game: Bacchusmon suspended whatever digivolved; only the BT25 Cougarmon chain kept Kekkomon live; Sirenmon saved Bacchusmon from Eclipse Impact; Habakirimon's -5000 didn't kill Homeros-buffed rookies; TS passed rather than overextend into a Tamer-less Glowing Dawn.", "OBSERVED", "GAO LCQ u0z_9HckvRM"),
                ("Attacks only when safe; games go to time.", "STATED", "DigiCarding"),
            ]),
            ("Our plan", [
                ("Pass exactly 4 at the end of each turn: every Homeros gains 1, reaches 5 and suspends itself, losing the end-of-turn replay. They order Homeros first, so 3 can leave one Homeros live; 5+ gifts memory.", "COUNTED + STATED", "Homeros text; JSnmWFvks5E, Melbourne report 6FOJs_cdfwI"),
                ("Race Mervamon, which lands on their T3. Their T2 put 0 checks into us, so we can build undisturbed; but the goldfish kills by our T3 only about 13%, and going second our T3 comes after their T3. Expect to face Mervamon and plan the pass and blockers for it.", "INFERRED", "n=1 timeline; Goldfish sheet"),
                ("Suspend Minervamon instead of deleting it: its On Deletion replays an Iliad card and De-Digivolves, and the trash feeds Mervamon.", "OBSERVED + COUNTED", "KnTElixar 0iT08uRH52Q; card text"),
                ("Remove Sirenmon first: it dies in place of any other Iliad body leaving (Eclipse Impact included) and its inherit redirects our attacks.", "COUNTED + OBSERVED", "card text; GAO"),
                ("Armalizamon suspends a blocker (On Play / When Digivolving) and makes Final Judgment cost 0-1; Eclipse Impact bottom-decks the biggest suspended Digimon (beats Reboot).", "STATED + COUNTED", "Madrid vWJCKCJVDy0; Peoria; card text"),
                ("Count DP: 16000 into a 16000 Bacchusmon was a loss.", "OBSERVED", "GAO"),
                ("If the kill is gone, play fast: their pilots go to time, and a draw beats a loss.", "INFERRED", ""),
            ]),
            ("Their misplays to punish", [
                ("'Caveman mode' card spam; feeding Homeros into a 5-memory pass; slow play into time; over-searching into deck-out; Bacchusmon baited (its delete is mandatory); Wide Plasment while security is high; digging for Minervamon; building around Venusmon; passing extra memory into Minervamon.", "STATED + OBSERVED", "DigiCarding; KnTElixar 0iT08uRH52Q"),
            ]),
            ("Corrections and unknowns", [
                ("No TS pilot has explained this matchup; no Glowing Dawn-side data on the 4-memory pass yet.", "INFERRED", ""),
            ]),
        ],
    },
    "vs Toho": {
        "matchup": 2,
        "facts": [
            ("Their burst turn", "T2: Shishimamon, Execute, Lv6 (Kaguyamon / Amaterasumon / Ryugumon)"),
            ("Their fastest win", "T3 via Susanoomon (game T5 on the play, T6 on the draw)"),
            ("Our Lv6", "Atratusmon; Habakirimon second"),
            ("End our turn with", "as little memory as possible for them"),
        ],
        "sections": [
            ("Their plan", [
                ("T1 setup: Lv3 in breeding, Island for 3, or Analog Youth plus a set Sanmyojin Arrival; passes 2-3.", "OBSERVED", "Sao Paulo 7JFJMCXLEA0; Singapore Ky_clVcx92s"),
                ("T2 burst: Shishimamon (gives one of ours Security Attack -1 and -3000), Execute, a Lv6. Kaguyamon is the default (4 Retaliation blockers); Amaterasumon for removal; Ryugumon into Atratusmon.", "OBSERVED + STATED", "Brisbane H40YtjjjJbE; Rotherham MDqMIDDu1Jo"),
                ("T3: Susanoomon gives all of ours -3000 per color (-15000 to -18000) for their turn, places one of ours into their security, trashes ours and recovers.", "OBSERVED + COUNTED", "card text"),
                ("Arrival: when their Lv5+ would leave the battle area, they play a Sanmyojin Digimon from hand for free (bottom-deck counts as leaving).", "COUNTED", "Sanmyojin Arrival text"),
                ("Island in security plays a Lv5-or-lower from hand: a Shellmon (can't attack or block) froze our Habakirimon.", "STATED + OBSERVED", "Brisbane; Sao Paulo"),
                ("Karakurumon suspends a Tamer and keeps it down: their only way to touch Tamers.", "STATED", "Brisbane"),
                ("Memory: 'not good with memory', passes 2-3; Analog Youth regains memory after Execute deletions.", "STATED", "Brisbane; jumbojank 2026-07-15"),
            ]),
            ("How they beat Glowing Dawn", [
                ("DigiLab: Glowing Dawn 41.3% (62-88).", "OBSERVED", "digilab.cards"),
                ("Ryugumon: whenever they play or digivolve, one of ours can't suspend (attack) or use When Digivolving until our turn ends; Evade + Barrier. 'If you see Ryugu that matchup's pretty favored.'", "COUNTED + STATED", "card text; Brisbane"),
                ("Sao Paulo game 3: early Kaguyamon wall, Shellmon locked a Glowing Dawn Tamer; bottom-decking Kaguyamon just brought another via Arrival; removing Kaguyamon re-triggers Karakurumon and Kaguyamon, which 'basically guarantees you take lethal back'.", "OBSERVED", "7JFJMCXLEA0"),
                ("Chip damage feeds Susanoomon: every name in their trash counts.", "STATED", "Madrid vWJCKCJVDy0"),
                ("Romulo lost game 2 playing into Ryugumon's trigger.", "STATED", "Romulo TR9dZjK9XH0"),
            ]),
            ("Our plan", [
                ("Atratusmon is the Lv6: immunity blanks Amaterasumon's delete, Shishimamon's -3000, and Susanoomon's -DP and security placement. Won Sao Paulo game 1.", "OBSERVED + COUNTED", "7JFJMCXLEA0; card text"),
                ("Barrier answers Execute and Susanoomon swings (battle). Pump Atratusmon to 21000-24000 (Monarchlizamon ST23-08 +3000, Tomoro & Kyo) to survive -DP that lands before immunity.", "STATED + COUNTED", "Madrid vWJCKCJVDy0"),
                ("Bottom-deck Kaguyamon and Ryugumon with Eclipse Impact (Atratusmon's Option side): no Retaliation, no On Deletion, Evade can't save it. Expect Arrival to replace it.", "COUNTED + OBSERVED", "card text; olBMZIKhl5g"),
                ("Habakirimon second: trashes the top security of whoever has more and unsuspends; 'doesn't leave' stops Susanoomon's placement (costs our security).", "OBSERVED + COUNTED", "7JFJMCXLEA0; card text"),
                ("Take all 5 security in one turn, or steal the turn first: game 1 was won by dodging two checks and turning the extra memory into lethal.", "STATED + OBSERVED", "Madrid; 7JFJMCXLEA0"),
                ("Keep a second attacker for Ryugumon; ST23-04 Murasamemon's -5000 clears small blockers.", "COUNTED + STATED", "card text; Romulo"),
                ("Keep the Lv4 in breeding: Kokeshimon x4 and Musyamon delete Lv4-or-lower on sight.", "COUNTED", "Vaelthas's list"),
            ]),
            ("Their misplays to punish", [
                ("Shishimamon into a security Option; missing Ryugumon against Atratusmon; a trash too thin for Kaguyamon or Susanoomon; passing big memory; letting Glowing Dawn steal the turn while it has memory.", "STATED + OBSERVED", "Brisbane; Sao Paulo"),
            ]),
            ("Corrections and unknowns", [
                ("Correction: Ryugumon does not freeze Tamers (its lock hits a Digimon); Karakurumon is the Tamer stunner. Round 1 notes said otherwise.", "COUNTED", "card text"),
                ("Correction: the bottom-deck tool is Atratusmon's Eclipse Impact, not Habakirimon (Habakirimon trashes security and protects).", "COUNTED", "card text"),
                ("Unverified: a possible banlist 'hit on Analog' (Analog Youth) mentioned by Sao Paulo commentators.", "STATED", "7JFJMCXLEA0"),
                ("No data: whether Toho targets our Tamers or the breeding Lv4 first.", "INFERRED", ""),
            ]),
        ],
    },
    "vs DATS": {
        "matchup": 3,
        "facts": [
            ("Their burst turn", "T2 combo: 2-4 removals plus hand strip (n=2-3); T3 'more likely'"),
            ("Their fastest win", "T4-T5 (n=3, very low confidence)"),
            ("Our Lv6", "Atratusmon"),
            ("End our turn with", "as little memory as possible (their combo costs 8-11)"),
        ],
        "sections": [
            ("Their plan", [
                ("T1: one or two Tamers (dual Tamer via DNA Charge or GeoGreymon). The 'perfect' hand is a full Agumon/Falcomon line, DNA Charge and a Tamer.", "OBSERVED", "G-iNe0mpPC4; -_59naRfz6c"),
                ("T2 combo: Peckmon / Crowmon delete a Lv4-or-lower, Ravemon from the trash deletes our highest DP, hand strip, Ravemon face-up into security. 2-4 removals.", "OBSERVED n=2-3", "-_59naRfz6c, G-rvjwxTjIA"),
                ("About 9 memory rips 6 cards and puts 2 Ravemon into security.", "STATED", "Japanese guide (note.com, paywalled)"),
                ("Ravemon in security replays itself at the end of our turn.", "OBSERVED + COUNTED", "card text"),
                ("Plan B: Lilamon (free off 2 Tamer sources) into Rosemon into Rosemon Burst Mode; rebuilds from about 3 memory.", "STATED", "BenjiTCG G-iNe0mpPC4; East I__Sik4t_A0"),
                ("Closer: Rosemon Burst Mode bottom-decks a suspended Digimon to trash a security card, repeatably.", "OBSERVED", "-jFZg3bprFk"),
                ("Deliberately avoids gaining memory to pass less.", "OBSERVED", "OyZ9g4jRbe0"),
            ]),
            ("How they beat Glowing Dawn", [
                ("DigiLab: Glowing Dawn 45.8% (11-13-5).", "OBSERVED", "digilab.cards"),
                ("Not with hand rip: Glowing Dawn 'did not care' (e-Pulse refills, Tamers replay from the trash).", "OBSERVED", "KnTElixar qiM2Bz92Vd0"),
                ("With the Rosemon Tamer lock: double Rosemon plus Aguichant Levres won that game.", "OBSERVED + STATED", "qiM2Bz92Vd0; Romulo TR9dZjK9XH0"),
                ("Why the lock hurts: Tomoro's +2 fuel and Kyo's +1 fuel are paid by suspending the Tamer, so a suspended Tamer that can't unsuspend makes no triggered fuel. Tomoro & Kyo's start-of-main +1 fuel +1 memory and Kyo's hand tuck still work.", "COUNTED", "Tomoro BT25-090, Kyo BT26-089, Tomoro & Kyo ST23-13 text"),
                ("Rosemon's trigger: whenever our Digimon or Tamers suspend, they play a cost-3-or-lower DATA SQUAD card free (+1 per suspended card).", "COUNTED", "Rosemon BT26-049 text"),
            ]),
            ("Our plan", [
                ("Raise to Lv5 in breeding and move on T3, not T2: Peckmon x4 and Crowmon x4 delete a Lv4-or-lower on their T2.", "COUNTED + OBSERVED", "Rayquon's list"),
                ("Atratusmon: immunity stops Ravemon, Crowmon and Rosemon (all Digimon effects) once it has digivolved or attacked. Romulo: immunity + Blocker + Reboot is 'very complete'.", "COUNTED + STATED", "card text; Romulo"),
                ("Protect the Tamers: 2 Tamers before their T2-T3; dual Tamers are better against Tamer stun. Some pilots run fewer memory setters for this matchup.", "STATED", "Peoria; Romulo"),
                ("Ignore the hand rip; refill with e-Pulse / Makoto.", "OBSERVED", "qiM2Bz92Vd0"),
                ("Batch attacks: a 1-check poke gives a free Tamer 20% of the time, and a Ravemon in security replays when our turn ends.", "COUNTED", "Rayquon's list; card text"),
                ("If their security is all face-up Ravemon, it empties at the end of our turn: keep an attacker for an end-of-turn or next-turn kill.", "OBSERVED", "-_59naRfz6c (the DATS player's misplay)"),
            ]),
            ("Their misplays to punish", [
                ("Ravemon into security too early (its On Deletion stops resolving); security made only of Ravemon; no Lv5 (scoops); no interaction on their opponent's turn, so suspend / -DP on their turn beats them.", "OBSERVED", "G-iNe0mpPC4; -_59naRfz6c; bewyBp4hr_c"),
            ]),
            ("Corrections and unknowns", [
                ("No data: how DATS handles Atratusmon, its key turn vs Glowing Dawn, or when it picks the Rosemon lock over Ravemon removal.", "INFERRED", ""),
            ]),
        ],
    },
}

RESEARCH_SOURCES = [
    ("Research round 1: real-game turn timings", "research/round1-timings.md", "OBSERVED / STATED / INFERRED; unread video lists per deck"),
    ("Research round 2: how strong pilots play each deck", "research/round2-playbooks.md", "cached transcripts and guides under research/transcripts/"),
    ("Jupitermon Wrath Mode deck tech (cardsrealm, 2026-09-25)", "https://digimon.cardsrealm.com/en-us/articles/digimon-tcg-deck-tech-how-to-play-jupitermon-wrath-mode", ""),
    ("TS Mervamon guide (digimonmeta, OvermasterP, 2026-08-28)", "research/transcripts/guides/merva_megazoo.txt", "cached in full"),
]
VIDEOS = [
    ("kv58ncMwTMU", "DDOUGHY feature match, Jupitermon vs Toho (BT26)"),
    ("7JFJMCXLEA0", "Sao Paulo top 8, Yuri (Toho) vs Glowing Dawn, Portuguese"),
    ("olBMZIKhl5g", "Same match re-commentated"),
    ("TR9dZjK9XH0", "Romulo 'Alchemist', Sao Paulo 8th, Glowing Dawn interview"),
    ("qjWEEf2UKxM", "Peoria top 16 Glowing Dawn profile (Hoang Zero, BT25)"),
    ("H40YtjjjJbE", "Brisbane 2nd Toho profile (Caleb)"),
    ("JSnmWFvks5E", "DigiCarding TS Mervamon profile + goldfish"),
    ("0iT08uRH52Q", "KnTElixar Titans vs TS Mervamon"),
    ("u0z_9HckvRM", "GAO LCQ Thailand, Glowing Dawn vs TS Box"),
    ("G-iNe0mpPC4", "BenjiTCG + Tommy, DATA SQUAD Ravemon"),
    ("qiM2Bz92Vd0", "KnTElixar, Glowing Dawn vs DATS"),
    ("-jFZg3bprFk", "DDOUGHY casual, TS Mervamon vs DATS Rosemon"),
    ("-_59naRfz6c", "DDOUGHY, DATS game A"),
    ("mZ4GiLpJzEs", "Barcelona, East (Jupitermon) vs Glowing Dawn (BT25)"),
    ("DhHn8jxncWY", "V-Tamer, Glowing Dawn vs Jupitermon"),
    ("WSfJyTi8zh4", "Security Check, Jupitermon games"),
    ("vWJCKCJVDy0", "Madrid Glowing Dawn profile"),
    ("CoEe9A1S5mU", "Nima, Dusseldorf store regional (Gere Gaming)"),
    ("I__Sik4t_A0", "East, 'DATS TRAP'"),
]
