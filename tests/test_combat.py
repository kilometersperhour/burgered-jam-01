import unittest

from burgerJam.combat import BODY_WIDTH, LEFT, RIGHT, Controls, Fighter, Match, OpponentAI


class CombatTests(unittest.TestCase):
    def close_match(self):
        return Match([Fighter(400), Fighter(500, -1)])

    def advance(self, match, seconds, defender=None, fps=60):
        hits = []
        for _ in range(round(seconds * fps)):
            hits.extend(match.update(1 / fps, [Controls(), defender or Controls()]))
        return hits

    def test_jab_has_startup_and_hits_only_once(self):
        match = self.close_match()
        match.update(.05, [Controls(attack="jab"), Controls()])
        self.assertEqual(match.fighters[1].health, 100)
        hits = self.advance(match, .3)
        self.assertEqual(match.fighters[1].health, 92)
        self.assertEqual(len(hits), 1)
        self.advance(match, .2)
        self.assertIsNone(match.fighters[0].attack)

    def test_cross_is_stronger_and_pushes_target(self):
        match = self.close_match()
        match.fighters[0].start_attack("cross")
        self.advance(match, .4)
        self.assertEqual(match.fighters[1].health, 86)
        self.assertGreater(match.fighters[1].x, 500)

    def test_attack_cannot_interrupt_its_own_recovery(self):
        fighter = Fighter(400)
        self.assertTrue(fighter.start_attack("jab"))
        self.assertFalse(fighter.start_attack("cross"))
        fighter.update(.4, Controls(), False)
        self.assertTrue(fighter.start_attack("cross"))

    def test_out_of_range_punch_misses(self):
        match = Match()
        match.fighters[0].start_attack("cross")
        self.assertEqual(self.advance(match, .7), [])
        self.assertEqual(match.fighters[1].health, 100)

    def test_guard_stops_jab_and_reduces_cross_to_chip(self):
        for name, health in (("jab", 100), ("cross", 98)):
            with self.subTest(name=name):
                match = self.close_match()
                match.fighters[0].start_attack(name)
                hits = self.advance(match, .4, Controls(block=True))
                self.assertEqual(match.fighters[1].health, health)
                self.assertTrue(hits[0].blocked)

    def test_releasing_guard_allows_immediate_attack(self):
        fighter = Fighter(400)
        fighter.update(.01, Controls(block=True), True)
        self.assertFalse(fighter.start_attack("jab"))
        fighter.update(.01, Controls(attack="jab"), True)
        self.assertEqual(fighter.attack, "jab")
        self.assertFalse(fighter.blocking)

    def test_airborne_character_cannot_guard(self):
        fighter = Fighter(400, elevation=100)
        fighter.update(.01, Controls(block=True), True)
        self.assertFalse(fighter.blocking)

    def test_attack_facing_is_locked_during_swing(self):
        match = self.close_match()
        match.fighters[0].facing = -1
        match.fighters[0].start_attack("jab")
        self.advance(match, .2)
        self.assertEqual(match.fighters[1].health, 100)
        self.assertEqual(match.fighters[0].facing, -1)

    def test_airborne_target_outside_hitbox_is_not_hit(self):
        match = self.close_match()
        match.fighters[1].elevation = 240
        match.fighters[0].start_attack("jab")
        self.advance(match, .2)
        self.assertEqual(match.fighters[1].health, 100)

    def test_jump_returns_to_floor_without_drift(self):
        fighter = Fighter(400)
        for _ in range(5):
            fighter.update(1 / 120, Controls(jump=True), True)
            self.assertGreater(fighter.elevation, 0)
            for _ in range(120):
                fighter.update(1 / 120, Controls(), False)
            self.assertEqual(fighter.elevation, 0)
            self.assertEqual(fighter.velocity, 0)

    def test_cannot_double_jump(self):
        fighter = Fighter(400)
        fighter.update(.1, Controls(jump=True), True)
        old_velocity = fighter.velocity
        fighter.update(.1, Controls(jump=True), True)
        self.assertLess(fighter.velocity, old_velocity)

    def test_wall_clamping_does_not_bounce(self):
        for position, direction in ((LEFT, -1), (RIGHT, 1)):
            fighter = Fighter(position)
            for _ in range(100):
                fighter.update(1 / 60, Controls(move=direction), False)
                self.assertEqual(fighter.x, position)

    def test_bodies_separate_at_center_and_walls(self):
        for x in (LEFT, 600, RIGHT):
            match = Match([Fighter(x), Fighter(x, -1)])
            match.update(.01, [Controls(), Controls()])
            a, b = match.fighters
            self.assertGreaterEqual(b.x - a.x, BODY_WIDTH - 1e-8)
            self.assertGreaterEqual(a.x, LEFT)
            self.assertLessEqual(b.x, RIGHT)

    def test_jumping_over_opponent_changes_facing(self):
        match = self.close_match()
        match.fighters[0].x = 540
        match.fighters[0].elevation = 200
        match.update(.01, [Controls(), Controls()])
        self.assertEqual(match.fighters[0].facing, -1)
        self.assertEqual(match.fighters[1].facing, 1)

    def test_simultaneous_attacks_trade_and_can_draw(self):
        match = self.close_match()
        for fighter in match.fighters:
            fighter.health = 8
            fighter.start_attack("jab")
        self.advance(match, .2)
        self.assertTrue(match.over)
        self.assertIsNone(match.winner)
        self.assertEqual([f.health for f in match.fighters], [0, 0])

    def test_ko_ends_match_and_freezes_simulation(self):
        match = self.close_match()
        match.fighters[1].health = 3
        match.fighters[0].start_attack("cross")
        self.advance(match, .4)
        self.assertTrue(match.over)
        self.assertEqual(match.winner, 0)
        self.assertEqual(match.reason, "KO")
        snapshot = (match.remaining, match.fighters[0].x)
        match.update(.1, [Controls(move=1), Controls()])
        self.assertEqual(snapshot, (match.remaining, match.fighters[0].x))

    def test_timeout_chooses_health_leader_or_draw(self):
        for health, winner in ((100, None), (70, 0)):
            match = Match(remaining=.01)
            match.fighters[1].health = health
            match.update(.02, [Controls(), Controls()])
            self.assertTrue(match.over)
            self.assertEqual(match.winner, winner)
            self.assertEqual(match.reason, "TIME")

    def test_movement_and_damage_are_consistent_across_frame_rates(self):
        results = []
        for fps in (30, 60, 120):
            match = self.close_match()
            match.fighters[0].start_attack("jab")
            self.advance(match, 1, fps=fps)
            walker = Fighter(300)
            for _ in range(fps):
                walker.update(1 / fps, Controls(move=1), False)
            results.append((match.fighters[1].health, walker.x))
        self.assertEqual([value[0] for value in results], [92, 92, 92])
        for _, position in results:
            self.assertAlmostEqual(position, 590)

    def test_cpu_can_approach_attack_and_finish_a_match(self):
        match = Match()
        ai = OpponentAI(42)
        for _ in range(60 * 61):
            match.update(1 / 60, [Controls(), ai.update(match, 1 / 60)])
            if match.over:
                break
        self.assertTrue(match.over)
        self.assertEqual(match.winner, 1)
        self.assertEqual(match.reason, "KO")

    def test_invalid_delta_does_not_corrupt_state(self):
        for dt in (0, -1, float("nan"), float("inf")):
            match = Match()
            self.assertEqual(match.update(dt, [Controls(), Controls()]), [])
            self.assertEqual(match.remaining, 60)


if __name__ == "__main__":
    unittest.main()
