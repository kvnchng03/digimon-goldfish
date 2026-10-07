import random
import unittest

from goldfish.calc import Attacker, Security, Situation, simulate, solve

HARMLESS = Security(digimon=((1000, 50),), tamers=0, crimson=0, other=0)
KILLERS = Security(digimon=((16000, 50),), tamers=0, crimson=0, other=0)
ATRATUSMON = Attacker(dp=12000, checks=2, attacks=2, immune=True)


class HandCheckedCases(unittest.TestCase):
    def test_two_checks_then_lethal(self):
        r = solve(Situation(HARMLESS, their_security=2, attackers=(ATRATUSMON,)), "early")
        self.assertAlmostEqual(r.p_win, 1.0)
        self.assertAlmostEqual(r.checks, 2.0)

    def test_removing_the_last_card_is_not_a_win(self):
        r = solve(Situation(HARMLESS, their_security=3, attackers=(ATRATUSMON,)), "early")
        self.assertAlmostEqual(r.p_win, 0.0)
        self.assertAlmostEqual(r.p_zero, 1.0)

    def test_killers_stop_the_attacker_after_one_check(self):
        r = solve(Situation(KILLERS, their_security=5, attackers=(ATRATUSMON,)), "early")
        self.assertAlmostEqual(r.checks, 1.0)
        self.assertAlmostEqual(r.attackers_lost, 1.0)
        self.assertAlmostEqual(r.security_left, 4.0)

    def test_barrier_pays_security_instead(self):
        a = Attacker(dp=12000, checks=2, attacks=2, barrier=True)
        r = solve(Situation(KILLERS, their_security=4, attackers=(a,), your_security=5), "early")
        self.assertAlmostEqual(r.p_zero, 1.0)
        self.assertAlmostEqual(r.barrier_paid, 4.0)
        self.assertAlmostEqual(r.your_security_after, 1.0)

    def test_independent_checks_multiply(self):
        sec = Security(digimon=((12000, 10), (1000, 40)), tamers=0, crimson=0, other=0)
        r = solve(Situation(sec, their_security=3, attackers=(ATRATUSMON,)), "early")
        self.assertAlmostEqual(r.p_zero, 0.8 ** 2)  # the 3rd card is removed even if it kills the attacker
        self.assertAlmostEqual(r.attackers_lost, 1 - 0.8 ** 3)

    def test_saved_blocker_stops_the_lethal_attack(self):
        second = Attacker(dp=7000, immune=True)
        sit = Situation(HARMLESS, their_security=2, attackers=(ATRATUSMON, second), stoppers=1, stopper_dp=16000)
        # "lethal": blocks Atratusmon's 2nd attack, the 7000 connects.
        # "early": blocks attack 1 (Atratusmon dies), the 7000 checks once.
        self.assertAlmostEqual(solve(sit, "lethal").p_win, 1.0)
        self.assertAlmostEqual(solve(sit, "early").p_win, 0.0)

    def test_piercing_checks_after_beating_the_blocker(self):
        a = Attacker(dp=12000, checks=1, attacks=1, piercing=True)
        sit = Situation(HARMLESS, their_security=1, attackers=(a,), stoppers=1, stopper_dp=5000)
        self.assertAlmostEqual(solve(sit, "early").p_zero, 1.0)
        no_pierce = Situation(HARMLESS, their_security=1, attackers=(Attacker(dp=12000),), stoppers=1, stopper_dp=5000)
        self.assertAlmostEqual(solve(no_pierce, "early").security_left, 1.0)

    def test_triggers_shrink_non_immune_attackers(self):
        sec = Security(digimon=((5000, 25), (1000, 25)), tamers=0, crimson=0, other=0)
        lv5 = Attacker(dp=7000, checks=1)
        hit = Situation(sec, their_security=5, attackers=(lv5,), minus=5000)
        self.assertAlmostEqual(solve(hit, "early").attackers_lost, 0.5)  # 2000 DP loses to the 5000s
        immune = Situation(sec, their_security=5, attackers=(Attacker(dp=7000, immune=True),), minus=5000)
        self.assertAlmostEqual(solve(immune, "early").attackers_lost, 0.0)

    def test_crimson_blaze_ignores_barrier(self):
        sec = Security(digimon=(), tamers=0, crimson=50, other=0)
        a = Attacker(dp=6000, checks=1, barrier=True)
        r = solve(Situation(sec, their_security=3, attackers=(a,)), "early")
        self.assertAlmostEqual(r.attackers_lost, 1.0)
        self.assertAlmostEqual(r.barrier_paid, 0.0)


FIELDS = ("p_win", "p_zero", "security_left", "checks", "free_tamers", "attackers_lost", "barrier_paid")


class ExactMatchesMonteCarlo(unittest.TestCase):
    def test_random_situations(self):
        rng = random.Random(7)
        sec = Security(digimon=((1000, 11), (5000, 8), (8000, 8), (13000, 10)), tamers=10, crimson=2, other=1)
        for _ in range(12):
            attackers = tuple(
                Attacker(dp=rng.choice([4000, 7000, 12000, 15000]), checks=rng.randint(1, 3), attacks=rng.randint(1, 2),
                         barrier=rng.random() < 0.5, immune=rng.random() < 0.5, piercing=rng.random() < 0.3)
                for _ in range(rng.randint(1, 3)))
            sit = Situation(sec, their_security=rng.randint(0, 6), attackers=attackers, stoppers=rng.randint(0, 2),
                            stopper_dp=rng.choice([5000, 12000, 16000]), minus=rng.choice([0, 5000]))
            for policy in ("early", "lethal"):
                exact, mc = solve(sit, policy), simulate(sit, policy, games=20000, seed=rng.randint(0, 10**6))
                for field in FIELDS:
                    self.assertAlmostEqual(getattr(exact, field), getattr(mc, field), delta=0.03,
                                           msg=f"{field} {policy} {sit}")


if __name__ == "__main__":
    unittest.main()
