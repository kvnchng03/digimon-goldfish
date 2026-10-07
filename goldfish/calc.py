"""Exact odds for one attack turn into a real opponent's security.

The model follows the Comprehensive Rules for attacks (11-5, 13, 14, 16-7, 16-25):
- An attack that connects while they have 0 security wins. A check that removes their
  last card does not; the next unblocked attack does (1-2-3-1).
- Each check reveals one card. A security Digimon with DP >= the attacker's deletes it
  (ties delete both, 14-2-1-3); <Barrier> trashes your top security instead (16-25).
  Crimson Blaze deletes the attacker if it has 6000 DP or less (no Barrier). A deleted
  attacker stops checking (13-1-5); the revealed card is gone either way.
- A blocked attack battles the blocker and makes no checks, unless the attacker has
  <Piercing> and deletes the blocker (16-7). Sirenmon's redirect and Aegiochusmon: Blue's
  inherited unsuspend each stop one more attack, so they count as "stoppers".
- Their check triggers (Aegiochusmon: Holy's -5000, Wrath Mode's -15000) shrink every
  non-immune attacker from the first removed card on.

Approximations, stated in the workbook too: each check is an independent draw from their
50-card list; you always have security to pay for Barrier (the expected payment is
reported so you can compare); stoppers share one DP; the opponent blocks either the
first attacks ("early") or only the lethal ones ("lethal"), and the truth lies between.

The same transition rules drive the exact solver here and the live Excel formulas
(tools/build_workbook.py renders `transitions` symbolically), so the two cannot drift.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

S_MAX = 7  # their security cards
B_MAX = 3  # stoppers
MAX_ATTACKERS = 3
MAX_ATTACKS = 2  # the second one needs an unsuspend
MAX_CHECKS = 3

DEAD, IDLE, CHECKING = 0, 1, 2
WON = "won"
POLICIES = ("early", "lethal")


@dataclass(frozen=True)
class Attacker:
    dp: int
    checks: int = 1
    attacks: int = 1
    barrier: bool = False
    immune: bool = False  # to their Digimon effects (Atratusmon after digivolving / attacking)
    piercing: bool = False


@dataclass(frozen=True)
class Security:
    """Their 50-card list as security composition: Digimon by DP, plus non-Digimon cards."""

    digimon: tuple[tuple[int, int], ...]  # (dp, count)
    tamers: int
    crimson: int
    other: int

    @property
    def total(self) -> int:
        return sum(c for _, c in self.digimon) + self.tamers + self.crimson + self.other

    def p_at_least(self, dp: int) -> float:
        return sum(c for d, c in self.digimon if d >= dp) / self.total


@dataclass(frozen=True)
class Situation:
    security: Security
    their_security: int
    attackers: tuple[Attacker, ...]
    stoppers: int = 0
    stopper_dp: int = 0
    minus: int = 0  # -DP their check triggers give each non-immune attacker
    your_security: int = 5
    first_check_trash: int = 0  # your security they trash on your first check (Jupitermon)


# ------------------------------------------------------------------ per-attacker numbers
def check_dp(a: Attacker, sit: Situation) -> int:
    """Attacker DP in a security battle: a check always follows a removal, so triggers apply."""
    return a.dp - (0 if a.immune else sit.minus)


def p_battle_loss(a: Attacker, sit: Situation) -> float:
    x = check_dp(a, sit)
    return 0.0 if x <= 0 else sit.security.p_at_least(x)


def p_hard_kill(a: Attacker, sit: Situation) -> float:
    """Deletion that Barrier can't stop: DP pushed to 0, or Crimson Blaze."""
    x = check_dp(a, sit)
    if x <= 0:
        return 1.0
    return sit.security.crimson / sit.security.total if x <= 6000 else 0.0


def p_die(a: Attacker, sit: Situation) -> float:
    return min(1.0, p_hard_kill(a, sit) + (0.0 if a.barrier else p_battle_loss(a, sit)))


def p_pay(a: Attacker, sit: Situation) -> float:
    return p_battle_loss(a, sit) if a.barrier else 0.0


def block_outcome(a: Attacker, sit: Situation, triggered: bool) -> dict[str, int]:
    """A battle against a stopper; `triggered` = their -DP triggers have already fired."""
    x = a.dp - (sit.minus if triggered and not a.immune else 0)
    loses = x <= sit.stopper_dp
    dead = loses and not a.barrier
    pierce = a.piercing and x >= sit.stopper_dp and not dead
    return {"dead": int(dead), "pierce": int(pierce), "idle": int(not dead and not pierce),
            "pay": int(loses and a.barrier)}


# ------------------------------------------------------------------ the shared model
def states() -> list:
    return [(s, st, b) for s in range(S_MAX + 1) for st in (DEAD, IDLE, CHECKING) for b in range(B_MAX + 1)] + [WON]


def steps() -> list[tuple]:
    out = []
    for a in range(MAX_ATTACKERS):
        for j in range(1, MAX_ATTACKS + 1):
            out.append(("start", a, j))
            out.extend(("check", a, j, k) for k in range(1, MAX_CHECKS + 1))
    return out


def active(step: tuple, sit: Situation) -> bool:
    a = sit.attackers[step[1]] if step[1] < len(sit.attackers) else None
    if a is None or step[2] > a.attacks:
        return False
    return step[0] == "start" or step[3] <= a.checks


def transitions(step: tuple, state, policy: str):
    """Where one source state goes in an active step.

    Returns (targets, acc): targets = [(state, factors)], acc = {kind: factors}, where
    factors are tokens multiplied together (an empty tuple is probability 1). Tokens:
    ("die", a), ("live", a), ("pay", a) per check, and ("blk", field, a, s) for a battle
    against a stopper at their security s (the -DP triggers fired iff s < their start).
    """
    if state == WON:
        return [(WON, ())], {}
    s, st, b = state
    a = step[1]
    if step[0] == "start":
        alive = True if step[2] == 1 else st != DEAD  # a new attacker starts alive
        if not alive:
            return [(state, ())], {}
        if b > 0 and (s == 0 or policy == "early"):
            blk = lambda f: (("blk", f, a, s),)  # noqa: E731
            return ([((s, DEAD, b - 1), blk("dead")), ((s, CHECKING, b - 1), blk("pierce")),
                     ((s, IDLE, b - 1), blk("idle"))],
                    {"deaths": blk("dead"), "pays": blk("pay")})
        if s == 0:
            return [(WON, ())], {}
        return [((s, CHECKING, b), ())], {}
    if st == CHECKING and s > 0:
        return ([((s - 1, DEAD, b), (("die", a),)), ((s - 1, CHECKING, b), (("live", a),))],
                {"checks": (), "deaths": (("die", a),), "pays": (("pay", a),)})
    return [(state, ())], {}


def start_state(sit: Situation) -> tuple:
    return (min(sit.their_security, S_MAX), IDLE, min(sit.stoppers, B_MAX))


# ------------------------------------------------------------------ numeric solver
def _token(tok: tuple, sit: Situation) -> float:
    if tok[0] == "blk":
        _, field, a, s = tok
        return block_outcome(sit.attackers[a], sit, triggered=s < sit.their_security)[field]
    a = sit.attackers[tok[1]]
    return {"die": p_die, "live": lambda x, y: 1 - p_die(x, y), "pay": p_pay}[tok[0]](a, sit)


def _product(factors: tuple, sit: Situation) -> float:
    out = 1.0
    for tok in factors:
        out *= _token(tok, sit)
    return out


@dataclass
class Result:
    p_win: float
    p_zero: float  # they end at 0 security and you didn't win
    security_left: float
    checks: float
    free_tamers: float
    free_plays: float
    attackers_lost: float
    barrier_paid: float
    your_security_after: float


def solve(sit: Situation, policy: str) -> Result:
    dist = {start_state(sit): 1.0}
    acc = {"checks": 0.0, "deaths": 0.0, "pays": 0.0}
    for step in steps():
        if not active(step, sit):
            continue
        new: dict = {}
        for state, p in dist.items():
            targets, contrib = transitions(step, state, policy)
            for target, factors in targets:
                q = p * _product(factors, sit)
                if q:
                    new[target] = new.get(target, 0.0) + q
            for kind, factors in contrib.items():
                acc[kind] += p * _product(factors, sit)
        dist = new
    s0 = start_state(sit)[0]
    p_win = dist.get(WON, 0.0)
    p_untouched = sum(p for st, p in dist.items() if st != WON and st[0] == s0)
    p_any_check = (1 - p_untouched) if s0 > 0 else 0.0
    sec = sit.security
    return Result(
        p_win=p_win,
        p_zero=sum(p for st, p in dist.items() if st != WON and st[0] == 0),
        security_left=sum(p * st[0] for st, p in dist.items() if st != WON),
        checks=acc["checks"],
        free_tamers=acc["checks"] * sec.tamers / sec.total,
        free_plays=acc["checks"] * sec.other / sec.total,
        attackers_lost=acc["deaths"],
        barrier_paid=acc["pays"],
        your_security_after=sit.your_security - acc["pays"] - sit.first_check_trash * p_any_check,
    )


# ------------------------------------------------------------------ Monte Carlo (for tests)
def simulate(sit: Situation, policy: str, games: int, seed: int = 1) -> Result:
    """Plays the same turn card by card; used to check the exact solver."""
    rng = random.Random(seed)
    sec = sit.security
    deck = [("digimon", d) for d, c in sec.digimon for _ in range(c)]
    deck += [("tamer", 0)] * sec.tamers + [("crimson", 0)] * sec.crimson + [("other", 0)] * sec.other
    tot = {k: 0.0 for k in ("win", "zero", "left", "checks", "tamers", "other", "lost", "paid")}
    s0 = min(sit.their_security, S_MAX)
    for _ in range(games):
        s, b, won = s0, min(sit.stoppers, B_MAX), False
        for a in sit.attackers:
            alive = True
            for _j in range(a.attacks):
                if not alive or won:
                    break
                checks = 0
                if b > 0 and (s == 0 or policy == "early"):
                    b -= 1
                    out = block_outcome(a, sit, triggered=s < s0)
                    tot["paid"] += out["pay"]
                    if out["dead"]:
                        alive = False
                        tot["lost"] += 1
                    elif out["pierce"]:
                        checks = a.checks
                elif s == 0:
                    won = True
                else:
                    checks = a.checks
                for _k in range(checks):
                    if s == 0:
                        break
                    s -= 1
                    tot["checks"] += 1
                    kind, dp = rng.choice(deck)
                    x = check_dp(a, sit)
                    tot["tamers"] += kind == "tamer"
                    tot["other"] += kind == "other"
                    if x <= 0 or (kind == "crimson" and x <= 6000):
                        alive = False
                    elif kind == "digimon" and dp >= x:
                        if a.barrier:
                            tot["paid"] += 1
                        else:
                            alive = False
                    if not alive:
                        tot["lost"] += 1
                        break
            if won:
                break
        tot["win"] += won
        tot["zero"] += (not won) and s == 0
        tot["left"] += 0 if won else s
    n = games
    return Result(p_win=tot["win"] / n, p_zero=tot["zero"] / n, security_left=tot["left"] / n,
                  checks=tot["checks"] / n, free_tamers=tot["tamers"] / n, free_plays=tot["other"] / n,
                  attackers_lost=tot["lost"] / n, barrier_paid=tot["paid"] / n, your_security_after=float("nan"))
