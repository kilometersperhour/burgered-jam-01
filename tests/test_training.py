import unittest

from burgerJam.combat import BODY_WIDTH, Controls, Fighter, Match
from burgerJam.training import DUMMY_LEFT, DUMMY_RIGHT, TrainingSession


class TrainingTests(unittest.TestCase):
    def advance(self, session, seconds, controls=None):
        hits = []
        for _ in range(round(seconds * 120)):
            hits += session.update(1 / 120, controls or Controls())
        return hits

    def combo(self, session):
        for move, duration in (("lp", .1), ("mp", .14), ("hp", .20), ("special", .18)):
            session.update(1 / 120, Controls(attack=move))
            self.advance(session, duration)

    def test_dummy_stays_still_and_never_attacks(self):
        session = TrainingSession("Burger")
        self.advance(session, 2)
        player, dummy = session.match.fighters
        self.assertEqual((player.x, dummy.x), (480, 600))
        self.assertEqual((player.health, dummy.health), (100, 100))
        self.assertIsNone(dummy.attack)
        self.assertEqual(session.match.remaining, 60)

    def test_training_has_no_knockouts_or_timeout(self):
        session = TrainingSession("Burger")
        session.match.remaining = 0
        session.match.fighters[1].health = 1
        self.advance(session, .3, Controls(attack="lp"))
        self.assertEqual(session.match.fighters[1].health, 1)
        self.assertFalse(session.match.over)
        self.assertIsNone(session.match.winner)
        self.assertEqual(session.match.remaining, 0)

    def test_combo_records_persist_without_recentering_dummy(self):
        session = TrainingSession("Burger")
        self.combo(session)
        self.assertEqual(session.last_hits, 4)
        self.assertEqual(session.best_hits, 4)
        self.assertGreater(session.last_damage, 20)
        recorded = (session.last_hits, session.last_damage, session.best_hits, session.best_damage)
        self.advance(session, .5)
        positions = tuple(fighter.x for fighter in session.match.fighters)
        self.advance(session, 2)
        self.assertEqual(tuple(fighter.x for fighter in session.match.fighters), positions)
        self.assertGreater(positions[1], 600)
        self.assertEqual([fighter.health for fighter in session.match.fighters], [100, 100])
        self.assertEqual(session.match.fighters[0].combo_hits, 0)
        self.assertEqual(recorded, (session.last_hits, session.last_damage, session.best_hits, session.best_damage))

    def test_training_uses_same_combo_damage_and_timing_as_normal_combat(self):
        session = TrainingSession("Burger")
        match = Match([Fighter(480), Fighter(600, -1)])
        for move, duration in (("lp", .1), ("mp", .14), ("hp", .2)):
            controls = Controls(attack=move)
            session.update(1 / 120, controls)
            match.update(1 / 120, [controls, Controls()])
            for _ in range(round(duration * 120)):
                session.update(1 / 120, Controls())
                match.update(1 / 120, [Controls(), Controls()])
        self.assertEqual(session.last_hits, match.fighters[0].combo_hits)
        self.assertEqual(session.last_damage, match.fighters[0].combo_damage)
        self.assertEqual(session.total_damage, 100 - match.fighters[1].health)
        self.assertEqual(session.match.fighters[1].health, 100)

    def test_manual_reset_clears_combat_but_preserves_records(self):
        session = TrainingSession("Pickle")
        self.combo(session)
        best = (session.best_hits, session.best_damage)
        session.match.fighters[0].health = 50
        session.reset()
        self.assertEqual(session.match.fighters[0].character, "Pickle")
        self.assertEqual(session.match.fighters[0].health, 100)
        self.assertEqual(session.match.fighters[0].stun, 0)
        self.assertIsNone(session.match.fighters[0].attack)
        self.assertEqual((session.best_hits, session.best_damage), best)

    def test_dummy_and_player_stay_put_when_movement_stops(self):
        session = TrainingSession("Burger")
        session.update(.1, Controls(attack="lp"))
        self.advance(session, 2, Controls(move=-1))
        self.assertLess(session.match.fighters[0].x, 480)
        self.assertGreater(session.total_damage, 0)
        position = session.match.fighters[0].x
        self.advance(session, 2)
        self.assertEqual(session.match.fighters[0].x, position)

    def test_dummy_guard_modes_shield_low_and_overhead_attacks(self):
        session = TrainingSession("Burger")
        session.cycle_dummy()
        self.assertEqual(session.dummy_mode, "guard")
        hits = session.update(.1, Controls(attack="lp"))
        self.assertTrue(hits[0].blocked)
        session.cycle_dummy()
        self.assertEqual(session.dummy_mode, "crouch guard")
        session.update(.01, Controls())
        self.assertTrue(session.match.fighters[1].crouching)
        self.assertTrue(session.match.fighters[1].blocking)
        session.update(.1, Controls(crouch=True, attack="lk"))
        self.assertEqual(session.match.fighters[1].health, 100)
        session.reset()
        hits = session.update(.1, Controls(attack="hk"))
        hits += self.advance(session, .2)
        self.assertTrue(any(hit.blocked for hit in hits))
        session.cycle_dummy()
        self.assertEqual(session.dummy_mode, "stand")

    def test_dummy_shield_can_break_and_reset_restores_it_without_losing_damage(self):
        session = TrainingSession("Burger", "guard")
        dummy = session.match.fighters[1]
        dummy.shield = 5
        hits = session.update(.1, Controls(attack="lp"))
        self.assertTrue(hits[0].shield_broken)
        self.assertEqual(session.total_damage, 0)
        self.advance(session, .3)
        session.update(.1, Controls(attack="lp"))
        self.assertEqual(session.total_damage, 8)
        session.reset()
        self.assertEqual(session.match.fighters[1].shield, 100)
        self.assertEqual(session.match.fighters[1].shield_break, 0)
        self.assertEqual(session.total_damage, 8)

    def test_dummy_stops_knockback_at_both_travel_limits(self):
        for limit, sign in ((DUMMY_RIGHT, 1), (DUMMY_LEFT, -1)):
            session = TrainingSession("Burger")
            player, dummy = session.match.fighters
            dummy.x = limit - sign * 5
            player.x = dummy.x - sign * 100
            session.update(.1, Controls(attack="hp"))
            self.advance(session, .4)
            self.assertEqual(dummy.x, limit)
            self.advance(session, 3)
            self.assertEqual(dummy.x, limit)
            self.assertGreater(session.total_damage, 0)

    def test_walking_cannot_push_dummy_past_its_limits(self):
        for limit, direction in ((DUMMY_RIGHT, 1), (DUMMY_LEFT, -1)):
            session = TrainingSession("Burger")
            player, dummy = session.match.fighters
            dummy.x, player.x = limit, limit - direction * 40
            self.advance(session, .5, Controls(move=direction))
            self.assertEqual(dummy.x, limit)
            self.assertGreaterEqual(abs(player.x - dummy.x), BODY_WIDTH - 1e-8)

    def test_player_can_jump_behind_dummy_at_either_limit_and_hit_back(self):
        for limit, direction in ((DUMMY_RIGHT, 1), (DUMMY_LEFT, -1)):
            session = TrainingSession("Burger")
            player, dummy = session.match.fighters
            dummy.x, player.x = limit, limit - direction * 90
            session.update(1 / 120, Controls(move=direction, jump=True))
            self.advance(session, 1, Controls(move=direction))
            self.assertGreater((player.x - dummy.x) * direction, BODY_WIDTH)
            self.assertLessEqual(dummy.x, DUMMY_RIGHT)
            self.assertGreaterEqual(dummy.x, DUMMY_LEFT)
            # Landing can push the dummy through body collision; it then stays put.
            position = dummy.x
            self.advance(session, .5)
            self.assertEqual(dummy.x, position)
            while abs(player.x - dummy.x) > 100:
                session.update(1 / 120, Controls(move=-direction))
            before = session.total_damage
            session.update(.1, Controls(attack="lp"))
            self.advance(session, .1)
            self.assertGreater(session.total_damage, before)
            self.assertLess((dummy.x - position) * direction, 0)

    def test_guard_changes_do_not_recenter_dummy(self):
        session = TrainingSession("Burger")
        session.match.fighters[1].x = DUMMY_RIGHT
        session.cycle_dummy()
        self.advance(session, .1)
        self.assertEqual(session.match.fighters[1].x, DUMMY_RIGHT)

    def test_total_damage_keeps_growing_past_100_and_survives_manual_reset(self):
        session = TrainingSession("Burger")
        for _ in range(20):
            session.match.fighters[0].x = session.match.fighters[1].x - 100
            session.update(.1, Controls(attack="lp"))
            self.advance(session, .35)
        self.assertEqual(session.total_damage, 160)
        self.assertEqual(session.match.fighters[1].health, 100)
        session.reset()
        self.assertEqual(session.total_damage, 160)
        self.assertEqual(TrainingSession("Burger").total_damage, 0)


if __name__ == "__main__":
    unittest.main()
