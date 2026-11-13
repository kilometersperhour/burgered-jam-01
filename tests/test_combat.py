import unittest

from burgerJam.combat import (ATTACKS, DIVES, NORMALS, BODY_WIDTH, LEFT, RIGHT, SHIELD_MAX,
                             SHIELD_BREAK_TIME, Controls, Fighter, Match, MotionBuffer, OpponentAI, move_for)
from burgerJam.roster import CHARACTERS


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

    def test_shield_takes_damage_instead_of_health(self):
        for name in ("jab", "cross"):
            with self.subTest(name=name):
                match = self.close_match()
                match.fighters[0].start_attack(name)
                hits = self.advance(match, .4, Controls(block=True))
                self.assertEqual(match.fighters[1].health, 100)
                self.assertLess(match.fighters[1].shield, SHIELD_MAX - 10)
                self.assertTrue(hits[0].blocked)

    def test_releasing_guard_allows_immediate_attack(self):
        fighter = Fighter(400)
        fighter.update(.01, Controls(block=True), True)
        self.assertFalse(fighter.start_attack("jab"))
        fighter.update(.01, Controls(attack="jab"), True)
        self.assertEqual(fighter.attack, "lp")
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

    def test_all_six_normals_have_distinct_strengths_and_kick_geometry(self):
        for name in NORMALS:
            with self.subTest(move=name):
                match = self.close_match()
                self.assertTrue(match.fighters[0].start_attack(name))
                hits = self.advance(match, .5)
                self.assertEqual(len(hits), 1)
                self.assertEqual(hits[0].damage, ATTACKS[name].damage)
                self.assertEqual(ATTACKS[name].limb == "kick", name.endswith("k"))

    def test_crouch_shortens_body_stops_walking_and_changes_kicks_to_low(self):
        fighter = Fighter(400)
        original_height = fighter.body.height
        fighter.update(.01, Controls(move=1, crouch=True, attack="lk"), True)
        self.assertTrue(fighter.crouching)
        self.assertLess(fighter.body.height, original_height)
        self.assertEqual(fighter.x, 400)
        self.assertEqual(fighter.current_move.level, "low")

    def test_shield_covers_low_mid_and_overhead_hits_at_both_heights(self):
        for move, attack_down, defend_down, blocked in (
                ("lk", True, False, True), ("lk", True, True, True),
                ("hk", False, True, True), ("hk", False, False, True)):
            with self.subTest(move=move, crouch=defend_down):
                match = self.close_match()
                controls = [Controls(crouch=attack_down, attack=move), Controls(block=True, crouch=defend_down)]
                hits = match.update(.05, controls)
                hits += self.advance(match, .4, Controls(block=True, crouch=defend_down))
                self.assertEqual(len(hits), 1)
                self.assertEqual(hits[0].blocked, blocked)

    def test_back_is_full_speed_movement_in_both_facing_directions(self):
        for facing in (-1, 1):
            fighter = Fighter(600, facing)
            fighter.update(.1, Controls(move=-facing), True)
            self.assertFalse(fighter.blocking)
            self.assertAlmostEqual(fighter.x, 600 - facing * 29)

    def test_walking_backward_does_not_block_incoming_attacks(self):
        match = self.close_match()
        hits = match.update(.1, [Controls(attack="lp"), Controls(move=1)])
        self.assertEqual(len(hits), 1)
        self.assertFalse(hits[0].blocked)
        self.assertEqual(match.fighters[1].health, 92)

    def test_air_normals_are_overheads_and_specials_require_ground(self):
        fighter = Fighter(400, elevation=120)
        fighter.start_attack("lp")
        self.assertEqual(fighter.current_move.level, "overhead")
        fighter.attack, fighter.spec = None, None
        self.assertFalse(fighter.start_attack("special"))

    def test_down_and_any_air_normal_starts_the_matching_fast_dive(self):
        for normal in NORMALS:
            fighter = Fighter(400, elevation=130, velocity=300)
            fighter.update(1 / 120, Controls(crouch=True, attack=normal), True)
            self.assertEqual(fighter.attack, "dive_kick" if normal.endswith("k") else "elbow_drop")
            self.assertLess(fighter.velocity, -900)
            self.assertLess(fighter.elevation, 130)
            self.assertEqual(fighter.current_move.level, "overhead")

    def test_dives_require_air_and_grounded_crouch_attacks_remain_normal(self):
        for move in DIVES:
            self.assertFalse(Fighter(400).start_attack(move))
        for normal in NORMALS:
            fighter = Fighter(400)
            fighter.update(.01, Controls(crouch=True, attack=normal), True)
            self.assertEqual(fighter.attack, normal)

    def test_dives_land_then_recover_including_immediate_jump_input(self):
        for elevation in (0, 130, 1500):
            for move in DIVES:
                fighter = Fighter(400, elevation=elevation)
                if elevation == 0:
                    fighter.update(1 / 120, Controls(jump=True, crouch=True,
                                   attack="lk" if move == "dive_kick" else "lp"), True)
                else:
                    fighter.start_attack(move)
                for _ in range(240):
                    fighter.update(1 / 120, Controls(), False)
                    if fighter.grounded:
                        break
                self.assertTrue(fighter.dive_landed)
                self.assertEqual(fighter.attack, move)
                self.assertIsNone(fighter.attack_box)
                for _ in range(60):
                    fighter.update(1 / 120, Controls(), False)
                self.assertIsNone(fighter.attack)

    def test_dives_hit_once_from_either_side_at_every_frame_rate(self):
        for move in DIVES:
            for facing in (-1, 1):
                for fps in (30, 60, 120):
                    with self.subTest(move=move, facing=facing, fps=fps):
                        match = Match([Fighter(500, facing, elevation=150), Fighter(500 + facing * 75, -facing)])
                        match.fighters[0].start_attack(move)
                        hits = self.advance(match, 1, fps=fps)
                        self.assertEqual(len(hits), 1)
                        self.assertEqual(hits[0].damage, ATTACKS[move].damage)
                        self.assertEqual(match.fighters[1].health, 100 - ATTACKS[move].damage)

    def test_dives_can_be_shielded_at_either_height_or_parried(self):
        for move in DIVES:
            for crouch in (False, True):
                match = Match([Fighter(500, elevation=150), Fighter(575, -1)])
                match.fighters[0].start_attack(move)
                hits = self.advance(match, .5, Controls(block=True, crouch=crouch))
                self.assertEqual(len(hits), 1)
                self.assertTrue(hits[0].blocked)
            match = Match([Fighter(500, elevation=150), Fighter(575, -1)])
            match.fighters[0].start_attack(move)
            hits = match.update(.1, [Controls(), Controls(parry=True)])
            self.assertEqual(len(hits), 1)
            self.assertTrue(hits[0].parried)

    def test_successful_parry_prevents_damage_and_unlocks_counter(self):
        match = self.close_match()
        hits = match.update(.1, [Controls(attack="lp"), Controls(parry=True)])
        self.assertTrue(hits[0].parried)
        self.assertEqual(match.fighters[1].health, 100)
        self.assertGreater(match.fighters[1].counter_window, 0)
        self.assertIsNone(match.fighters[0].attack)
        match.update(.05, [Controls(), Controls(counter=True)])
        self.assertEqual(match.fighters[0].health, 82)
        self.assertEqual(match.fighters[1].counter_window, 0)

    def test_counter_strike_requires_a_parry_but_e_also_offers_a_stance(self):
        fighter = Fighter(400)
        self.assertFalse(fighter.start_attack("counter"))
        fighter.counter_window = .01
        fighter.update(.02, Controls(counter=True), True)
        self.assertIsNone(fighter.attack)
        self.assertGreater(fighter.counter_time, 0)
        self.assertGreater(fighter.counter_recovery, 0)

    def test_forward_and_shield_gesture_parries_in_both_directions(self):
        for facing in (-1, 1):
            for fps in (30, 60, 120):
                match = Match([Fighter(600 - facing * 100, facing), Fighter(600, -facing)])
                match.fighters[0].start_attack("lp")
                hits = self.advance(match, .1, Controls(move=-facing, block=True), fps=fps)
                self.assertEqual(len(hits), 1)
                self.assertTrue(hits[0].parried)
                self.assertEqual(match.fighters[1].health, 100)
                self.assertGreater(match.fighters[1].shield, 99)
                self.assertGreater(match.fighters[1].counter_window, 0)

    def test_parry_gesture_allows_either_input_order_with_small_timing_gap(self):
        for first in (Controls(move=1), Controls(block=True)):
            fighter = Fighter(400)
            fighter.update(.06, first, True)
            fighter.update(.01, Controls(move=1, block=True), True)
            self.assertGreater(fighter.parry_time, 0)

    def test_held_shield_or_held_gesture_cannot_repeat_parries(self):
        fighter = Fighter(400)
        fighter.update(.2, Controls(block=True), True)
        fighter.update(.01, Controls(move=1, block=True), True)
        self.assertEqual(fighter.parry_time, 0)
        fighter.update(.01, Controls(), True)
        fighter.update(.01, Controls(move=1, block=True), True)
        self.assertGreater(fighter.parry_time, 0)
        for _ in range(120):
            fighter.update(1 / 120, Controls(move=1, block=True), True)
        self.assertEqual(fighter.parry_time, 0)
        self.assertTrue(fighter.blocking)

    def test_early_gesture_only_shields_and_late_gesture_cannot_escape_hit_stun(self):
        match = self.close_match()
        guard = Controls(move=-1, block=True)
        self.advance(match, .25, guard)
        match.fighters[0].start_attack("lp")
        hits = self.advance(match, .1, guard)
        self.assertTrue(hits[0].blocked)
        self.assertFalse(hits[0].parried)
        match = self.close_match()
        match.fighters[0].start_attack("lp")
        self.advance(match, .1)
        match.update(.01, [Controls(), guard])
        self.assertEqual(match.fighters[1].parry_time, 0)
        self.assertEqual(match.fighters[1].health, 92)

    def test_any_attack_after_parry_is_fast_even_with_shield_still_held(self):
        for attack in NORMALS:
            match = self.close_match()
            match.update(.1, [Controls(attack="lp"), Controls(move=-1, block=True)])
            hits = match.update(.05, [Controls(attack="hp"), Controls(move=-1, block=True, attack=attack)])
            self.assertEqual(match.fighters[1].attack, "counter")
            self.assertEqual(match.fighters[1].counter_window, 0)
            self.assertEqual(match.fighters[0].health, 82)
            self.assertEqual(match.fighters[1].health, 100)
            self.assertTrue(any(hit.target == 0 and hit.damage == 18 for hit in hits))

    def test_counter_stance_catches_attack_and_automatically_strikes_back(self):
        for facing in (-1, 1):
            match = Match([Fighter(600 - facing * 100, facing), Fighter(600, -facing)])
            hits = match.update(.1, [Controls(attack="lp"), Controls(counter=True)])
            hits += self.advance(match, .15)
            self.assertTrue(any(hit.countered for hit in hits))
            self.assertEqual(match.fighters[1].health, 100)
            self.assertEqual(match.fighters[0].health, 82)
            self.assertEqual(match.fighters[1].counter_time, 0)

    def test_counter_stance_scales_reply_to_strong_incoming_hits(self):
        match = Match([Fighter(400, character="Milk Shake"), Fighter(500, -1)])
        hits = match.update(.1, [Controls(attack="hp"), Controls(counter=True)])
        hits += self.advance(match, .25)
        self.assertTrue(any(hit.countered for hit in hits))
        self.assertEqual(match.fighters[0].health, 81)
        self.assertEqual(match.fighters[1].health, 100)

    def test_missed_counter_has_recovery_and_can_be_punished(self):
        match = self.close_match()
        match.update(.1, [Controls(), Controls(counter=True)])
        self.advance(match, .15)
        defender = match.fighters[1]
        self.assertEqual(defender.counter_time, 0)
        self.assertGreater(defender.counter_recovery, 0)
        position = defender.x
        match.update(.01, [Controls(), Controls(move=1, block=True, jump=True, attack="hp", counter=True)])
        self.assertEqual(defender.x, position)
        self.assertEqual(defender.elevation, 0)
        self.assertFalse(defender.blocking)
        self.assertIsNone(defender.attack)
        match.fighters[0].start_attack("lp")
        hits = self.advance(match, .1, Controls(block=True))
        self.assertFalse(hits[0].blocked or hits[0].countered)
        self.assertEqual(defender.health, 92)

    def test_shield_break_disables_defense_and_movement_then_recovers(self):
        for fps in (30, 60, 120):
            match = self.close_match()
            defender = match.fighters[1]
            defender.shield = 10
            match.fighters[0].start_attack("lp")
            hits = self.advance(match, .1, Controls(block=True), fps=fps)
            self.assertTrue(hits[0].shield_broken)
            self.assertEqual(defender.shield, 0)
            self.assertFalse(defender.blocking)
            self.assertEqual(defender.health, 100)
            position = defender.x
            match.update(.1, [Controls(), Controls(move=1, block=True, parry=True, counter=True, attack="lp", jump=True)])
            self.assertEqual(defender.x, position)
            self.assertEqual(defender.elevation, 0)
            self.assertFalse(defender.blocking)
            self.assertIsNone(defender.attack)
            self.assertEqual(defender.parry_time, 0)
            self.assertEqual(defender.counter_time, 0)
            self.advance(match, .2)
            match.fighters[0].start_attack("hp")
            self.advance(match, .3, Controls(block=True))
            self.assertEqual(defender.health, 86)
            self.assertGreater(defender.shield_break, 0)
            self.advance(match, SHIELD_BREAK_TIME)
            self.assertEqual(defender.shield_break, 0)
            self.assertGreaterEqual(defender.shield, 35)
            match.update(.01, [Controls(), Controls(block=True)])
            self.assertTrue(defender.blocking)

    def test_repeated_hits_break_a_full_shield(self):
        match = self.close_match()
        for _ in range(4):
            match.fighters[0].x = match.fighters[1].x - 100
            match.fighters[0].start_attack("hp")
            self.advance(match, .65, Controls(block=True))
        self.assertGreater(match.fighters[1].shield_break, 0)
        self.assertEqual(match.fighters[1].health, 100)

    def test_shield_drains_while_held_and_regenerates_only_after_release_delay(self):
        for fps in (30, 60, 120):
            match = self.close_match()
            self.advance(match, 1, Controls(block=True, move=1), fps=fps)
            defender = match.fighters[1]
            self.assertAlmostEqual(defender.shield, 95)
            self.assertEqual(defender.x, 500)
            self.advance(match, .5, fps=fps)
            self.assertAlmostEqual(defender.shield, 95)
            self.advance(match, 1, fps=fps)
            self.assertEqual(defender.shield, SHIELD_MAX)

    def test_shield_and_counter_are_unavailable_in_air(self):
        fighter = Fighter(400, elevation=150)
        fighter.update(.01, Controls(block=True, counter=True), True)
        self.assertFalse(fighter.blocking)
        self.assertEqual(fighter.counter_time, 0)

    def test_defense_cannot_protect_a_hit_from_behind(self):
        for defense in (Controls(block=True), Controls(parry=True), Controls(counter=True)):
            match = self.close_match()
            # Lock the defender facing away as the attack becomes active.
            match.update(.01, [Controls(attack="lp"), defense])
            match.fighters[1].facing = 1
            match.fighters[0].attack_time = ATTACKS["lp"].windup
            # Match normally faces an idle fighter toward its opponent; use the box contact
            # after a cross-up by keeping the defender's existing attack facing locked.
            match.fighters[1].attack, match.fighters[1].spec = "lp", ATTACKS["lp"]
            match.fighters[1].attack_time = .2
            hits = match.update(.01, [Controls(), defense])
            self.assertTrue(any(hit.target == 1 and hit.damage == 8 for hit in hits))

    def test_missed_parry_has_recovery_and_cannot_be_spammed(self):
        fighter = Fighter(400)
        fighter.update(.01, Controls(parry=True), True)
        self.assertGreater(fighter.parry_time, 0)
        fighter.update(.17, Controls(), False)
        self.assertEqual(fighter.parry_time, 0)
        self.assertFalse(fighter.start_attack("hp"))
        cooldown = fighter.parry_cooldown
        fighter.update(.01, Controls(parry=True), True)
        self.assertLess(fighter.parry_cooldown, cooldown)
        self.assertEqual(fighter.parry_time, 0)

    def test_hit_confirm_chain_into_special_counts_and_scales_four_hits(self):
        match = self.close_match()
        for name, duration in (("lp", .1), ("mp", .14), ("hp", .20), ("special", .18)):
            match.update(1 / 120, [Controls(attack=name), Controls()])
            self.advance(match, duration)
        attacker = match.fighters[0]
        self.assertEqual(attacker.combo_hits, 4)
        self.assertLess(attacker.combo_damage, sum(move_for("Burger", name).damage for name in ("lp", "mp", "hp", "special")))
        self.assertEqual(match.fighters[1].health, 100 - attacker.combo_damage)

    def test_cancel_is_unavailable_after_miss_or_block(self):
        for blocked in (False, True):
            match = self.close_match() if blocked else Match()
            match.fighters[0].start_attack("lp")
            self.advance(match, .1, Controls(block=blocked))
            self.assertFalse(match.fighters[0].start_attack("hp"))

    def test_same_or_lower_strength_cannot_cancel(self):
        match = self.close_match()
        match.fighters[0].start_attack("mp")
        self.advance(match, .14)
        self.assertFalse(match.fighters[0].start_attack("lp"))
        self.assertFalse(match.fighters[0].start_attack("mp"))

    def test_combo_input_just_before_impact_is_buffered(self):
        match = self.close_match()
        match.update(.04, [Controls(attack="lp"), Controls()])
        match.update(.04, [Controls(attack="mp"), Controls()])
        self.advance(match, .17)
        self.assertEqual(match.fighters[0].combo_hits, 2)

    def test_combo_requires_a_cancel_and_medium_cpu_cannot_request_it(self):
        match = self.close_match()
        match.fighters[0].start_attack("lp")
        self.advance(match, .1)
        match.update(.01, [Controls(attack="mp", allow_cancel=False), Controls()])
        self.assertEqual(match.fighters[0].attack, "lp")
        self.assertIsNone(match.fighters[0].buffered)

    def test_quarter_circle_motions_mirror_with_facing(self):
        for facing in (1, -1):
            for attack, sign, expected in (("lp", 1, "special"), ("lk", -1, "technique")):
                with self.subTest(facing=facing, move=expected):
                    fighter = Fighter(600, facing)
                    for move, down in ((0, True), (sign * facing, True), (sign * facing, False)):
                        fighter.update(.03, Controls(move=move, crouch=down), False)
                    fighter.update(.01, Controls(move=sign * facing, attack=attack), True)
                    self.assertEqual(fighter.attack, expected)

    def test_motion_expires_and_cannot_be_reused(self):
        buffer = MotionBuffer()
        for moment, move, down in ((0, 0, True), (.05, 1, True), (.1, 1, False)):
            buffer.record(move, down, 1, moment)
        self.assertEqual(buffer.consume("lp", .12), "special")
        self.assertEqual(buffer.consume("lp", .13), "lp")
        for moment, move, down in ((0, 0, True), (.05, 1, True), (.1, 1, False)):
            buffer.record(move, down, 1, moment)
        self.assertEqual(buffer.consume("lp", .7), "lp")

    def test_motion_events_within_single_frame_are_preserved(self):
        match = Match()
        match.update(.01, [Controls(move=1, attack="lp", motions=((0, True), (1, True), (1, False))), Controls()])
        self.assertEqual(match.fighters[0].attack, "special")

    def test_roster_has_ten_different_character_move_profiles(self):
        self.assertEqual(len(CHARACTERS), 10)
        signatures = set()
        for name in CHARACTERS:
            primary, secondary = move_for(name, "special"), move_for(name, "technique")
            signatures.add((primary.label, secondary.label))
            for move in NORMALS + ("special", "technique"):
                self.assertTrue(Fighter(400, character=name).start_attack(move))
        self.assertEqual(len(signatures), 10)
        self.assertGreater(move_for("Italian Scallion", "lp").reach, move_for("Burger", "lp").reach)
        self.assertGreater(move_for("Milk Shake", "hp").damage, move_for("Burger", "hp").damage)

    def test_rising_special_launches_and_rush_moves_forward(self):
        match = Match([Fighter(400, character="Tomato"), Fighter(500, -1)])
        match.fighters[0].start_attack("special")
        self.advance(match, .15)
        self.assertGreater(match.fighters[1].elevation, 0)
        fighter = Fighter(400)
        fighter.start_attack("special")
        fighter.update(.1, Controls(), False)
        self.assertGreater(fighter.x, 400)

    def test_cpu_difficulties_enforce_move_permissions(self):
        for difficulty in ("easy", "medium", "hard"):
            match = self.close_match()
            ai = OpponentAI(42, difficulty)
            attacks = set()
            for _ in range(1600):
                controls = ai.update(match, .1)
                if controls.attack:
                    attacks.add(controls.attack)
                self.assertEqual(controls.allow_cancel, difficulty == "hard")
                if difficulty == "easy":
                    self.assertFalse(controls.parry or controls.counter)
            if difficulty == "easy":
                self.assertEqual(attacks, set(NORMALS))
            else:
                self.assertIn("special", attacks)
                self.assertIn("technique", attacks)

    def test_hard_cpu_follows_confirmed_hits_with_combo_cancels(self):
        match = self.close_match()
        match.fighters[0].x, match.fighters[1].x = 500, 400
        match.fighters[1].facing = 1
        ai = OpponentAI(2, "hard")
        match.update(.1, [Controls(), Controls(attack="lp")])
        self.assertEqual(ai.update(match, .01).attack, "mp")
        for _ in range(60):
            match.update(1 / 120, [Controls(), ai.update(match, 1 / 120)])
        self.assertGreaterEqual(match.fighters[1].combo_hits, 3)

    def test_each_cpu_level_finishes_matches_and_only_hard_chains_hits(self):
        for difficulty in ("easy", "medium", "hard"):
            match = Match()
            ai = OpponentAI(7, difficulty)
            largest_combo = 0
            for _ in range(61 * 60):
                match.update(1 / 60, [Controls(), ai.update(match, 1 / 60)])
                largest_combo = max(largest_combo, match.fighters[1].combo_hits)
                if match.over:
                    break
            self.assertTrue(match.over, difficulty)
            self.assertLess(match.fighters[0].health, 100)
            if difficulty != "hard":
                self.assertLessEqual(largest_combo, 1, difficulty)
            else:
                self.assertGreaterEqual(largest_combo, 2)

    def test_simultaneous_jump_and_attack_uses_air_move(self):
        fighter = Fighter(400)
        fighter.update(.01, Controls(jump=True, attack="lp"), True)
        self.assertGreater(fighter.elevation, 0)
        self.assertEqual(fighter.current_move.level, "overhead")


if __name__ == "__main__":
    unittest.main()
