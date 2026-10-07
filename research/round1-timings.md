# Round 1: real-game turn timings (research, 2026-10-06)

Five researchers mined tournament and feature-match footage (transcripts, chapter markers, commentary) and guides for turn timings.
Labels: OBSERVED = seen in a game; STATED = a guide or pilot says so; INFERRED = reconstructed.
Commentators rarely say turn numbers, so most turn counts are reconstructed from the order of plays.
"Own Tn" = that deck's n-th turn; "game Tn" = the n-th turn of the game.
Cached transcripts: `research/transcripts/{tx,txc,tb}/` (files named by YouTube video ID).
YouTube IP-blocked `youtube-transcript-api` partway through; many sources stayed unread (listed per deck).

## Glowing Dawn (our deck)

About 12 readable games (regionals July to August, feature matches September), plus guides.

| Metric | Real games | Goldfish sim |
|---|---|---|
| First attack | median own T2 (n=12, range T2-T4) | T2 |
| First Lv5 | median T2 (n=11) | 63% by end of T2 |
| First Lv6 | median T2-T3 (6x T2, 2x T3, 4x T4) | 79% by end of T3 |
| Tamers by T3 | median 2 (range 1-3) | 75% have 2+ |
| Winning turn | median T4 (range T3-T4, n=7) | mean 4.15, median 4 |

Conclusion: the goldfish engine and policy match real Glowing Dawn speed.

How it loses: raced on the opponent's T4 (4 of 4 clean losses), Tamer removal (Galacticmon), -5000 wipes, option removal, Rosemon lock starving fuel.

STATED by pilots (Peoria top-16 Hoang Zero qjWEEf2UKxM; TCGplayer guide 2026-06-15; Cygnus OTK guide 2026-06-13; Sao Paulo 8th Romulo "Alchemist" TR9dZjK9XH0; Madrid top 8):
- Tamers must land on T1-T2 or the deck never builds fuel.
- The OTK needs about 5 fuel plus 4 memory (4 fuel with BT25 Murasamemon).
- "You can't chip": a Tamer flipped from their security hands them the turn.
- Two lines: aggressive T2 (out of breeding, Lv5/Lv6 same turn), or build stack and fuel in breeding and OTK from 5 security on T4.
- Killing Tamers "breaks the deck".
- e-Pulse and Makoto refill the hand against discard.

DigiLab matchup win rates for Glowing Dawn: vs Jupitermon 41.7% (105-147); vs TS Mervamon 16% (4-21-4; BT26 retrospective 37%); vs Toho Braves 41.3% (62-88); vs DATA SQUAD Ravemon 45.8% (11-13).
Dusseldorf 2026-10-04: 11 Glowing Dawn pilots went 40% combined; the 4th place 6-0-2 was one strong pilot.
Sao Paulo 2026-09-19: 15 pilots, 36%.
Gen Con was BT25 format; the drop coincides with BT26 bringing TS Mervamon and boosting Jupitermon and Toho.

UNREAD: Sao Paulo Swiss RvoF0dhzVsY (partly), top-8 oUi5tmN60SQ, u0z_9HckvRM, Qun9XU_tECc, PvB8XLexkpA, m8xwETbJ7as, 6FOJs_cdfwI, CoEe9A1S5mU, MLlgdNbhFjc, 0rBL3BGsmGw, TIoulm-fDEE, DhHn8jxncWY, VJmNkVlg3Y0; German locals ZmUQbqZaweM, OAAnrGA3ANg, BEPRQa8BrIU, 9jN102oxwf8 (captions too garbled).

## Toho Braves (TB)

About 20 game narrations; best source is the Sao Paulo top 8 (winner Yuri Rei vs Glowing Dawn, 7JFJMCXLEA0, Portuguese) and the final (LtKXMou-Ju0).

- Own T1: setup only (Lv3 in breeding, Island search, set Sanmyojin Arrival or Analog Youth), passes about 2-3 memory. Medium-high confidence.
- Own T2: the burst. Shishimamon (Lv5) then Execute then a Lv6 in one turn, first attack, 1-2 removals. Game T3 on the play, T4 on the draw.
- Lv6 choice: Kaguyamon (4-5 blockers with Retaliation, used vs OTK decks), Amaterasumon (removal), Ryugumon (freezes Tamers). A second Lv6 often arrives on the opponent's turn via Arrival.
- Own T3: Susanoomon gives all opponent Digimon -15k to -18k, then lethal. Delayed if the trash lacks 8 names.
- Fast wins: own T3 (game T5 on the play, T6 on the draw). Losses T6-T9.
- Execute about once per attack turn from own T2.
- Memory: "not good with memory"; passes 2-3.

Vs Glowing Dawn (Sao Paulo top 8, TB won 2-1): Atratusmon immunity blanked Amaterasumon's delete and blocked Shishimamon; Habakirimon cleared TB's board and trashed its security; TB uses Ryugumon/Kokeshimon to freeze Tomoro and Kyo; Kaguyamon survives Habakirimon's effect.
A guide (OYsWwDy3kI8) calls Atratusmon "brutal" for TB.
Correction to earlier advice: Atratusmon matters vs Toho as much as Habakirimon, because Susanoomon's -DP and "place as security" are Digimon effects.

Other matchups: vs Jupitermon mixed (DigiLab TB 59.6% over 57); vs TS Mervamon Bacchusmon/Ceresmon builds handle TB better; vs DATS hand-strip fills TB's trash so Susanoomon comes early.

UNREAD: oUi5tmN60SQ, 6FOJs_cdfwI, UE0Jfv1zouI, FhLOKoBlII8, Dy6gSvzgjIw, 7C5qrzenH9w, zEK-iZhctXk, TSpNn3BdChE, YbpsTkw8ioE, 68olTea5198, uU4M2qljIXw.

## DATA SQUAD Ravemon (Rose Rave)

Three games with countable turns (A -_59naRfz6c, B G-rvjwxTjIA, C -jFZg3bprFk pre-release), about 8 more with results only.

- Own T1: one or two Tamers (dual Tamer via DNA Charge or GeoGreymon).
- Own T2: the combo turn. Peckmon/Crowmon delete a Lv4-or-lower, Ravemon from trash deletes highest DP, hand strip, Ravemon face-up into security. 2-4 removals that turn (n=2-3).
- Own T2-T3: Rosemon lock; Burst Mode T2-T4 (low confidence).
- Game ends around game T7-T9 either way (n=3, very low confidence).
- Ravemon recurs from security at the end of the opponent's turn.
- STATED (G-iNe0mpPC4): full hand-rip combo "as early as turn two", "turn three is probably more likely"; costs about 8-11 memory.

DigiLab: overall 55.2% (373 entries); vs Jupitermon 37.5% (worst); vs TS Mervamon 61.5%; vs Glowing Dawn 54.2% (13-11-5); vs Toho Braves 45.5%.
Dusseldorf: 15 pilots at 33%.
Glowing Dawn note (qiM2Bz92Vd0 commentary): GD shrugs off hand rip by refilling with e-Pulse/Makoto.
Implication: their Lv4-killing chain lands on their T2, so vs DATS raise to Lv5 in breeding instead of moving the Lv3/Lv4 out on T2.

UNREAD: I__Sik4t_A0, OPUB0FWIGE0, nHrD1pG3Oco, RbmndxXy2v4, wftpyisvZy4, p36GiXoRIkc, EVEIHArzo1o, p9VQslQDCK4, kHfyGcNZxEk, i2sqtzHyYB8, 5TcfewG_-8o, N4ownaDRJOo, w-J77CzZByE, eSoehmXJC8w; no captions 7C5qrzenH9w, A3mEygGpuA4, SG8yjk2gLEU, p-fAeWiqDi8.

## TS Mervamon (Homeros control)

One game with countable turns (-jFZg3bprFk, casual, August); others give sequences only.

- Own T1: Tamer (Dan & Kanan), Central Town, Lv3.
- Own T2: Minervamon (first Lv6) plays Homeros; first removal the same turn.
- Own T3: Mervamon big -DP, then Alliance swings.
- Afterwards 2+ removal effects per turn (qualitative).
- Drags games out; wins by attacking once it controls the board; time draws common (Sao Paulo R5 0-0); sometimes near deck-out.
- STATED (JSnmWFvks5E): goes to time constantly; attack only when safe; hold a Homeros; board of Homeros, 2 Jupitermon, Mervamon, Sirenmon by about T4.
- STATED (digimonmeta OvermasterP guide 2026-08-28): common pass is around 7 memory early, chokes opponents to about 3 later.
- STATED (JSnmWFvks5E and Melbourne report 6FOJs_cdfwI): opponents pass exactly 4-5 memory so Homeros (gain 1, then at 5+ suspends to draw) suspends itself and cannot use its end-of-turn re-trigger. Tactical rule for us: vs Homeros, end the turn handing over 4.

DigiLab: TS Mervamon vs Glowing Dawn 84% (21-4) - our worst matchup; vs Jupitermon 68.2%; vs DATS 38.5%.
Dusseldorf: 5th UnkindledOne 6-1-1; 8 of the top 32.

UNREAD: __H3jtqnvhI, oUi5tmN60SQ, YtT8RaxN-oA, os55FEonMAM, azEKy04F5Q8, i-VhnSPPVkM; German KH7DatX7X1c, knVCCGhdfW0, DNIbWFKes8w.

## Jupitermon

Only 4 videos read before YouTube returned HTTP 429; only one (casual) has exact turn numbers, so no medians.
"J-Tn" = the Jupitermon player's n-th turn; [Tn] = game turn.

- kv58ncMwTMU (DDOUGHY feature match 2026-08-27, vs Toho Braves, J second), all OBSERVED:
  - J-T1 [T2]: Tsunomon, Elecmon, Aegiomon (Lv4) in breeding, Inori. No attack.
  - J-T2 [T4]: Aegiomon out, Homeros free, Aegiochusmon: Blue free via Inori, Jupitermon BT24 for 3, second Aegiomon, Dan & Kanan free (3 Tamers). First attack (2 checks). Wrath Mode for 5 the same turn, Venusmon; 2 removal effects; Wrath swings again (4 checks total). Own security 3 -> 0 -> back to 3 via Recovery +2. Passed opponent 7. One blocker (Wrath Mode).
  - Opponent [T5]: Susanoomon -18000 wipe after 2 stack protections.
  - J-T3 [T6]: Blinding Ray, Wide Plasment deletes Kaguyamon, Arts Digivolve into Jupitermon, -13000 twice, second Wrath Mode -15000 (about 5 removals). Won [T6].
- _m1ACKCJMwo (GAO LCQ Thailand top 8, BT26, vs Toho Braves), order only: no-rookie opening; early Aegiochusmon: Holy to punish TB's Lv4; Wide Plasment deletes Shishimamon; Dianamon; dropped to 1 security then Jupitermon Recovery +2 and Wrath Mode stabilised; Susanoomon wipe plus Crimson Blaze; lost a long game near deck-out. STATED: at 0 security Jupitermon cannot trash security to trigger Inori.
- Hi4g8MRm-x0 (Rotherham Regional BT26 R6, vs Beelstarmon), order only: Aegiomon then Inori; "At three security we can just do whatever we want"; Inori's free Lv5 needs 3 or fewer memory; 0- to 2-cost Jupitermon at low security; won 2-0.
- F7IqztqBxvE (casual, vs Toho Braves), INFERRED: Holy then BT26 Jupitermon within its first 2-3 turns; Wrath Mode only after TB's first Susanoomon; lost a long game near deck-out.

Typical values (n=1, low confidence): first Lv4 J-T1; first attack, Lv5, Lv6 and even Lv7 on J-T2; first removal J-T2, about 5 removals on J-T3; win J-T3 going second.
Lean on Tamer memory (3 Tamers, +3 per turn) and free plays.

DigiLab: Jupitermon vs Glowing Dawn 58.3% (147-105); vs Toho Braves 41.1% (65-93); vs TS Mervamon 31.8% (14-30); vs Beelstarmon 46.6%.
No Dusseldorf VOD exists (DigiLab has 6% match data, no stream links).

UNREAD (HTTP 429), highest value first: b6TqeUYk28A (Sao Paulo Regional R3, Jupitermon vs Dantemon), 6FOJs_cdfwI (Melbourne R4 vs Jupitermon, chapter 30:01), 8ZYi4jsqiMQ, AvSd8INowKA; KnTElixar bewyBp4hr_c, 32K4To1jzKY, ESank8yJui0, XBD4Bd0NLNI, yRp1ODsJu9c, 1DSkRr_rpMU, f3KG5Kv647w, 3Q_FfnhJaJE, lrqq1lOOggc, tCOIA5Hd4Zs, r1uXKmGcSU0, PM1enIklTCg; du0ijCPLj5A, WSfJyTi8zh4; vs Glowing Dawn _tpn6Brnkzc, inSKwaafaEU, TIhjuapxPdM; qOtRavPZ6YA (no captions); guides NMxAQyrQFO8, qWx8z0nhNmQ, ArcJqEohp4w, 97DD_-Aju_o, OqlYB0rqUNw; older mZ4GiLpJzEs, zHumxqlmcdw, z0qGxDwGbvs.
