"""Fetch Digimon Card Game card text by card number from the Digimon Card Game wiki.

    python3 tools/fetch_card_text.py BT24-101 BT26-103 ...
    python3 tools/fetch_card_text.py --json data/cardtext.json BT24-101 ...

Prints one compact block per card (stats, effect, inherited effect, security
effect) with the wiki's templates rendered into the game's own notation, and
optionally merges the raw fields into a JSON cache. Community-transcribed text:
check anything surprising against the physical card.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://digimoncardgame.fandom.com/api.php?action=parse&prop=wikitext&format=json&redirects=1&page={}"
FIELDS = ("cardtype", "name", "name2", "colour", "colour2", "level", "dp", "playcost", "evocost", "evocol",
          "evolvl", "evocost2", "evocol2", "evolvl2", "evocon", "type", "type2", "type3", "type4", "form",
          "attribute", "dual", "rule", "ace", "effect", "inheriteff", "seceff", "digixros", "dna", "assembly",
          "applink", "applinkdp", "boteff", "artsdigivolve")

SIMPLE = {
    "OnPlay": "[On Play]", "WhenDigivolving": "[When Digivolving]", "WhenAttacking": "[When Attacking]",
    "WhenMoving": "[When Moving]", "OnDeletion": "[On Deletion]", "EndOfAttack": "[End of Attack]",
    "YourTurn": "[Your Turn]", "OpponentsTurn": "[Opponent's Turn]", "AllTurns": "[All Turns]",
    "OncePerTurn": "[Once Per Turn]", "TwicePerTurn": "[Twice Per Turn]", "StartYourMain": "[Start of Your Main Phase]",
    "StartYourTurn": "[Start of Your Turn]", "EndYourTurn": "[End of Your Turn]", "EndAllTurns": "[End of All Turns]",
    "StartOpponentsTurn": "[Start of Opponent's Turn]", "EndOpponentsTurn": "[End of Opponent's Turn]",
    "MainTiming": "[Main]", "CounterTiming": "[Counter]", "Delay": "[Delay]", "Hand": "[Hand]",
    "Blocker": "<Blocker>", "Rush": "<Rush>", "Piercing": "<Piercing>", "Jamming": "<Jamming>",
    "Reboot": "<Reboot>", "Retaliation": "<Retaliation>", "Barrier": "<Barrier>", "Evade": "<Evade>",
    "Alliance": "<Alliance>", "Blitz": "<Blitz>", "Raid": "<Raid>", "Decoy": "<Decoy>", "Fortitude": "<Fortitude>",
    "ArmorPurge": "<Armor Purge>", "Collision": "<Collision>", "Vortex": "<Vortex>", "Overclock": "<Overclock>",
    "Partition": "<Partition>", "Blast Digivolve": "<Blast Digivolve>", "BlastDigivolve": "<Blast Digivolve>",
    "BlastDNA": "<Blast DNA Digivolve>", "ArtsDigivolve": "[Arts Digivolve]", "Overflow": "<Overflow>",
    "Ace": "ACE", "Iceclad": "<Iceclad>", "Material Save": "<Material Save>", "MaterialSave": "<Material Save>",
    "Link": "<Link>", "Progress": "<Progress>", "Mind Link": "<Mind Link>", "MindLink": "<Mind Link>",
    "Burst Digivolve": "<Burst Digivolve>", "BurstDigivolve": "<Burst Digivolve>",
}


def render(text: str) -> str:
    """Turn wiki markup into the card game's plain notation."""
    def tpl(m: re.Match) -> str:
        body = m.group(1)
        parts = [p.strip() for p in body.split("|")]
        name, args = parts[0], parts[1:]
        key = name.replace(" ", "")
        if name in SIMPLE or key in SIMPLE:
            return SIMPLE.get(name, SIMPLE.get(key, name))
        if name == "EffectLinkTraits":
            return f"[{args[0]}]" if args else "[trait]"
        if name in ("EffectLink", "CardName"):
            return f"[{args[0]}]" if args else name
        if name == "Digivolve":
            return f"[Digivolve: {args[0]} from {args[1]}]" if len(args) >= 2 else "[Digivolve]"
        if name == "DigivolveFromTraits":
            return f"[Digivolve: {args[0]} from Lv.{args[1]} w/ [{args[2]}] trait]" if len(args) >= 3 else "[Digivolve (trait)]"
        if name == "Draw":
            return f"<Draw {args[0] if args else 1}>"
        if name == "Recovery":
            return f"<Recovery +{args[0] if args else 1} (Deck)>"
        if name in ("SecurityA+", "SecurityAttackPlus"):
            return f"<Security A. +{args[0] if args else 1}>"
        if name == "SecurityA-":
            return f"<Security A. -{args[0] if args else 1}>"
        if name == "DeDigivolve":
            return f"<De-Digivolve {args[0] if args else 1}>" + (f" {args[1]}" if len(args) > 1 and args[1] else "")
        if name == "Security":
            kind = args[0].lower() if args else ""
            return "[Security] " + {"play": "Play this card without paying the cost.",
                                    "main": "Activate this card's [Main] effect.",
                                    "add": "Add this card to the hand.",
                                    "place": "Place this card in the battle area.",
                                    "battle": "At the end of the battle, play this card without paying the cost.",
                                    "battlewithout": "Play this card without battling and without paying the cost."}.get(kind, "")
        if name == "UseReq":
            return f"Use Req. [{args[0]}] {args[1] if len(args) > 1 else ''}".strip()
        if name == "Colour":
            return args[0] if args else ""
        if name == "DigiXros":
            return "DigiXros " + " ".join(args)
        if name == "Timing":
            return f"[{args[0]}]" if args else ""
        if name == "Keyword":
            return f"<{args[0]}>" if args else ""
        if name == "Nihongo":
            return args[0] if args else ""
        return "[" + " ".join([name] + [a for a in args if "=" not in a]) + "]"

    # HTML first, so the <Keyword> notation produced below survives.
    out = re.sub(r"<small>.*?</small>", "", text, flags=re.S)
    out = re.sub(r"<br\s*/?>", " / ", out)
    out = re.sub(r"</?(?:nowiki|span|font|b|i|u|sup|sub|div|p)\b[^>]*>", "", out)
    for _ in range(6):   # nested templates
        new = re.sub(r"\{\{([^{}]*)\}\}", tpl, out)
        if new == out:
            break
        out = new
    out = re.sub(r"\[\[([^\]|]*)\|([^\]]*)\]\]", r"\2", out)
    out = re.sub(r"\[\[([^\]]*)\]\]", r"\1", out)
    out = re.sub(r"'{2,}", "", out)
    return re.sub(r"\s+", " ", out).strip()


def fetch(card_id: str) -> dict[str, str] | None:
    req = urllib.request.Request(API.format(urllib.parse.quote(card_id)), headers={"User-Agent": "Mozilla/5.0 (deck-research)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    if "error" in data:
        return None
    wt = data["parse"]["wikitext"]["*"]
    fields: dict[str, str] = {"id": card_id}
    for line in wt.splitlines():
        m = re.match(r"^\|\s*([a-zA-Z0-9_]+)\s*=\s*(.*)$", line)
        if m and m.group(1) in FIELDS and m.group(2).strip():
            fields[m.group(1)] = m.group(2).strip()
    return fields


def describe(f: dict[str, str]) -> str:
    name = f.get("name", "?") + (f" // {f['name2']}" if f.get("name2") else "")
    colour = f.get("colour", "") + (f"/{f['colour2']}" if f.get("colour2") else "")
    stats = f"{f.get('cardtype', '?')} {colour} Lv{f.get('level', '-')} DP {f.get('dp', '-')}"
    costs = f"play {f.get('playcost', '-')} evo {f.get('evocost', '-')}"
    if f.get("evocon"):
        costs += " " + render(f["evocon"])
    if f.get("evocost2"):
        costs += f" (alt evo {f['evocost2']} from {f.get('evocol2', '')} Lv{f.get('evolvl2', '')})"
    traits = "/".join(f[k] for k in ("type", "type2", "type3", "type4") if f.get(k))
    lines = [f"== {f['id']} {name} | {stats} | {costs} | {traits}"]
    for key, label in (("rule", "RULE"), ("dna", "DNA"), ("digixros", "XROS"), ("assembly", "ASSEMBLY"), ("ace", "ACE"),
                       ("effect", "EFFECT"), ("inheriteff", "INH"), ("seceff", "SEC"), ("applink", "APPLINK")):
        if f.get(key):
            lines.append(f"   {label}: {render(f[key])}")
    return "\n".join(lines)


def fetch_template(name: str) -> str | None:
    """The rule text behind a wiki keyword template, e.g. 'Engage' or 'Assembly'."""
    page = name if name.startswith("Template:") else f"Template:{name}"
    req = urllib.request.Request(API.format(urllib.parse.quote(page)), headers={"User-Agent": "Mozilla/5.0 (deck-research)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8", "replace"))
    if "error" in data:
        return None
    wt = data["parse"]["wikitext"]["*"]
    wt = re.sub(r"<noinclude>.*?</noinclude>", "", wt, flags=re.S)
    wt = re.sub(r"<includeonly>.*?</includeonly>", "", wt, flags=re.S)
    return re.sub(r"\s+", " ", wt).strip()


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("ids", nargs="*", help="card numbers, e.g. BT24-101 (alt-art suffixes are stripped)")
    ap.add_argument("--json", type=Path, help="merge raw fields into this JSON cache")
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--template", nargs="*", default=[], help="print the raw wikitext of these keyword templates")
    args = ap.parse_args(argv)
    for name in args.template:
        try:
            body = fetch_template(name)
        except Exception as e:
            body = f"FETCH FAILED {e}"
        print(f"## Template:{name}\n{body}\n")
        time.sleep(args.sleep)
    cache: dict[str, dict[str, str]] = {}
    if args.json and args.json.exists():
        cache = json.loads(args.json.read_text())
    seen: set[str] = set()
    for raw in args.ids:
        cid = re.sub(r"_P\d+$", "", raw.strip())
        if cid in seen:
            continue
        seen.add(cid)
        f = cache.get(cid)
        if f is None:
            try:
                f = fetch(cid)
            except Exception as e:  # network trouble: say so and move on
                print(f"== {cid}: FETCH FAILED {e}")
                continue
            if f is None:
                print(f"== {cid}: no wiki page")
                continue
            cache[cid] = f
            time.sleep(args.sleep)
        print(describe(f))
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(cache, indent=1, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
