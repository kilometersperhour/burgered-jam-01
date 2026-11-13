"""Headless Pygame input, menus, rendering and launch integration checks."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

import pygame

from burgerJam.combat import ATTACKS, DIVES, FLOOR, NORMALS, Controls, move_for
from burgerJam.game import DEFAULT_BINDINGS, NUMPAD_BINDINGS, KNOCKOUT_DURATION, Game
from burgerJam.progress import CHARACTERS, Progress

ROOT = Path(__file__).resolve().parents[1]


class GameTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "save.json"
        self.game = Game(save_path=self.path, mute=True, seed=42)
        self.addCleanup(pygame.quit)

    def key(self, key, mod=0, release=False):
        self.game.handle_event(pygame.event.Event(pygame.KEYUP if release else pygame.KEYDOWN, key=key, mod=mod))

    def start(self):
        self.game.start_match()
        self.game.countdown = 0

    def test_menu_selection_difficulty_and_cpu_start(self):
        self.key(pygame.K_RIGHT)
        self.assertEqual(self.game.selected[0], "Tomato")
        self.key(pygame.K_RIGHT, pygame.KMOD_SHIFT)
        self.assertEqual(self.game.selected[1], "Hot Dog")
        self.key(pygame.K_DOWN)
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN)
        self.assertEqual(self.game.progress.difficulty, "hard")
        self.key(pygame.K_UP)
        self.key(pygame.K_UP)
        self.key(pygame.K_RETURN)
        self.assertEqual(self.game.state, "fight")
        self.assertEqual(self.game.ai.difficulty, "hard")

    def test_local_versus_is_unavailable_through_ui_or_start(self):
        self.assertNotIn("versus", [action for _, _, action in self.game.buttons()])
        self.assertFalse(self.game.start_match("versus"))
        self.assertEqual(self.game.state, "menu")
        self.game.activate("versus")
        self.assertEqual(self.game.state, "menu")

    def test_new_roster_cards_are_selectable_and_old_unlocks_remain_locked(self):
        for index in range(5, 10):
            self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                                     pos=self.game.card_rect(index).center))
            self.assertEqual(self.game.selected[0], CHARACTERS[index])
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                                 pos=self.game.card_rect(4).center))
        self.assertEqual(self.game.selected[0], "Milk Shake")

    def test_all_six_letter_keys_trigger_corresponding_attacks(self):
        for name in NORMALS:
            with self.subTest(move=name):
                self.start()
                self.key(DEFAULT_BINDINGS[name])
                self.game.update(.01, held=set())
                self.assertEqual(self.game.match.fighters[0].attack, name)

    def test_movement_crouch_and_thumb_jump(self):
        self.start()
        fighter = self.game.match.fighters[0]
        self.game.update(.01, held={pygame.K_a})
        self.assertLess(fighter.x, 330)
        position = fighter.x
        self.game.update(.01, held={pygame.K_d, pygame.K_s})
        self.assertEqual(fighter.x, position)
        self.assertTrue(fighter.crouching)
        self.key(pygame.K_SPACE)
        self.game.update(.01, held=set())
        self.assertGreater(fighter.elevation, 0)
        self.assertFalse(fighter.crouching)

    def test_a_and_d_move_full_speed_without_automatic_shield(self):
        for key, direction in ((pygame.K_a, -1), (pygame.K_d, 1)):
            self.start()
            fighter = self.game.match.fighters[0]
            self.game.update(.1, held={key})
            self.assertAlmostEqual(fighter.x, 330 + direction * 29)
            self.assertFalse(fighter.blocking)
            self.assertEqual(fighter.shield, 100)

    def test_shift_shields_and_forward_shift_parries_then_attack_counters(self):
        self.start()
        player, enemy = self.game.match.fighters
        player.x, enemy.x = 400, 500
        with patch.object(self.game.ai, "update", return_value=Controls()):
            self.game.update(.01, held={pygame.K_LSHIFT})
            self.assertTrue(player.blocking)
            self.game.update(.01, held=set())
            enemy.facing = -1
            enemy.start_attack("lp")
            self.game.update(.1, held={pygame.K_d, pygame.K_LSHIFT})
            self.assertEqual(player.health, 100)
            self.assertGreater(player.counter_window, 0)
            self.key(pygame.K_j)
            self.game.update(.05, held={pygame.K_d, pygame.K_LSHIFT})
            self.assertEqual(player.attack, "counter")
            self.assertEqual(enemy.health, 82)

    def test_remapped_shield_works_for_forward_parry_facing_left(self):
        self.start()
        self.game.progress.bindings["block"] = pygame.K_f
        player, enemy = self.game.match.fighters
        player.x, enemy.x = 600, 500
        enemy.facing = 1
        enemy.start_attack("lp")
        with patch.object(self.game.ai, "update", return_value=Controls()):
            self.game.update(.1, held={pygame.K_a, pygame.K_f})
        self.assertGreater(player.counter_window, 0)
        self.assertEqual(player.health, 100)

    def test_e_starts_counter_stance_and_auto_retaliates(self):
        self.start()
        player, enemy = self.game.match.fighters
        player.x, enemy.x, enemy.facing = 400, 500, -1
        enemy.start_attack("lp")
        self.key(pygame.K_e)
        with patch.object(self.game.ai, "update", return_value=Controls()):
            self.game.update(.1, held=set())
            self.game.update(.1, held=set())
        self.assertEqual(player.health, 100)
        self.assertEqual(enemy.health, 82)

    def test_shield_states_and_defense_instructions_render(self):
        preview = os.environ.get("BURGERJAM_PREVIEW_DIR")
        self.start()
        fighter = self.game.match.fighters[0]
        for state in ("full", "weak", "broken", "parry", "counter"):
            fighter.announcement, fighter.announcement_time = "", 0
            fighter.shield, fighter.shield_break = (100 if state == "full" else 15), 0
            fighter.blocking = state in ("full", "weak")
            fighter.parry_time = .1 if state == "parry" else 0
            fighter.counter_time = .1 if state == "counter" else 0
            if state == "counter":
                fighter.announcement, fighter.announcement_time = "COUNTER STANCE", .1
            if state == "broken":
                fighter.break_shield()
            with patch.object(self.game.art, "text", wraps=self.game.art.text) as render:
                self.game.draw()
            words = [str(call.args[1]) for call in render.call_args_list]
            self.assertIn("SHIELD BROKEN" if state == "broken" else "SHIELD " + str(round(fighter.shield)), words)
            if preview:
                Path(preview).mkdir(parents=True, exist_ok=True)
                pygame.image.save(self.game.screen, str(Path(preview) / ("shield-" + state + ".png")))
        self.game.activate("moves")
        self.game.move_page = 0
        self.game.progress.bindings["block"] = pygame.K_f
        with patch.object(self.game.art, "text", wraps=self.game.art.text) as render:
            self.game.draw()
        words = [str(call.args[1]) for call in render.call_args_list]
        self.assertTrue(any("Shield: hold F" in word for word in words))
        self.assertTrue(any("Forward + Shield" in word for word in words))
        self.assertTrue(any("Counter stance: E" in word for word in words))
        self.assertFalse(any("hold Back or" in word for word in words))
        if preview:
            pygame.image.save(self.game.screen, str(Path(preview) / "shield-moves.png"))

    def test_same_frame_direction_events_produce_quarter_circle_special(self):
        self.start()
        self.key(pygame.K_s)
        self.key(pygame.K_d)
        self.key(pygame.K_s, release=True)
        self.key(pygame.K_u)
        self.game.update(.01, held={pygame.K_d})
        self.assertEqual(self.game.match.fighters[0].attack, "special")

    def test_numpad_preset_and_custom_binding_are_used_in_gameplay(self):
        self.game.activate("numpad")
        self.assertEqual(self.game.progress.bindings, NUMPAD_BINDINGS)
        self.start()
        self.key(pygame.K_u)
        self.assertIsNone(self.game.pending.attack)
        self.key(pygame.K_KP4)
        self.game.update(.01, held=set())
        self.assertEqual(self.game.match.fighters[0].attack, "lp")
        self.game.progress.bindings["lp"] = pygame.K_h
        self.start()
        self.key(pygame.K_h)
        self.game.update(.01, held=set())
        self.assertEqual(self.game.match.fighters[0].attack, "lp")

    def test_mouse_punches_finish_without_additional_clicks(self):
        self.start()
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
        self.game.update(.01, held=set())
        self.assertEqual(self.game.match.fighters[0].attack, "lp")
        for _ in range(40):
            self.game.update(1 / 60, held=set())
        self.assertIsNone(self.game.match.fighters[0].attack)

    def test_pause_focus_loss_and_move_list_freeze_time_and_clear_input(self):
        self.start()
        self.key(pygame.K_u)
        self.key(pygame.K_ESCAPE)
        self.game.update(.1, held={pygame.K_d})
        self.assertEqual(self.game.match.remaining, 60)
        self.assertIsNone(self.game.pending.attack)
        self.key(pygame.K_ESCAPE)
        self.key(pygame.K_F2)
        self.assertEqual(self.game.state, "moves")
        self.game.update(.1, held={pygame.K_d})
        self.assertEqual(self.game.match.remaining, 60)
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.game.state, "fight")
        self.game.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertEqual(self.game.state, "pause")

    def test_countdown_prevents_early_attacks(self):
        self.game.start_match()
        self.key(pygame.K_u)
        self.game.update(.1, held={pygame.K_d})
        self.assertEqual(self.game.match.remaining, 60)
        self.assertEqual(self.game.match.fighters[0].x, 330)
        self.assertIsNone(self.game.match.fighters[0].attack)

    def test_settings_reject_duplicates_and_reserved_keys_then_save(self):
        self.game.activate("settings")
        self.game.activate("bind:lp")
        self.key(pygame.K_j)
        self.assertEqual(self.game.capture, "lp")
        self.key(pygame.K_F2)
        self.assertEqual(self.game.capture, "lp")
        self.key(pygame.K_h)
        self.assertIsNone(self.game.capture)
        self.game.activate("louder")
        self.game.activate("mute")
        self.game.activate("back")
        restored = Progress.load(DEFAULT_BINDINGS, self.path)
        self.assertEqual(restored.bindings["lp"], pygame.K_h)
        self.assertEqual(restored.volume, .45)
        self.assertTrue(restored.muted)
        self.assertEqual(self.game.state, "menu")

    def test_win_awards_once_unlocks_and_rematch_resets(self):
        self.start()
        self.game.match.fighters[1].health = 0
        self.game.update(.01, held=set())
        self.assertEqual(self.game.state, "knockout")
        self.assertEqual(self.game.progress.wins, 1)
        self.assertEqual(self.game.unlocked, ["Italian Scallion"])
        self.game.finish_match()
        self.assertEqual(self.game.progress.wins, 1)
        for _ in range(16):
            self.game.update(.1, held=set())
        self.assertEqual(self.game.state, "result")
        self.assertEqual(self.game.progress.wins, 1)
        with patch.object(self.game, "draw_knockout_fighter", wraps=self.game.draw_knockout_fighter) as fallen:
            self.game.draw()
        self.assertEqual(fallen.call_count, 1)
        self.game.activate("rematch")
        self.assertEqual([f.health for f in self.game.match.fighters], [100, 100])
        self.assertEqual(self.game.match.fighters[0].combo_hits, 0)
        self.assertEqual(self.game.knockout_poses, {})
        self.assertEqual(self.game.knockout_elapsed, 0)

    def test_losses_do_not_award_wins(self):
        self.start()
        self.game.match.fighters[0].health = 0
        self.game.update(.01, held=set())
        self.assertEqual(self.game.progress.wins, 0)
        self.assertEqual(self.game.state, "knockout")

    def test_ordinary_final_punch_plays_knockout_before_results(self):
        self.start()
        player, enemy = self.game.match.fighters
        player.x, enemy.x, enemy.health = 400, 500, 8
        with patch.object(self.game.ai, "update", return_value=Controls()):
            self.key(pygame.K_u)
            self.game.update(.1, held=set())
        self.assertTrue(self.game.match.over)
        self.assertEqual(enemy.health, 0)
        self.assertEqual(self.game.state, "knockout")
        self.assertEqual(self.game.buttons(), [])

    def test_knockout_sequence_runs_for_every_normal_special_and_dive(self):
        for move in NORMALS + ("special", "technique", "counter") + DIVES:
            self.start()
            player, enemy = self.game.match.fighters
            player.x, enemy.x, enemy.health = 400, 500, 1
            if move in DIVES:
                player.x, player.elevation = 425, 150
            if move == "counter":
                player.counter_window = .6
            self.assertTrue(player.start_attack(move))
            with patch.object(self.game.ai, "update", return_value=Controls()):
                for _ in range(12):
                    self.game.update(1 / 60, held=set())
                    if self.game.state == "knockout":
                        break
                # Slower heavy/special attacks can take more than twelve frames.
                for _ in range(30):
                    if self.game.state != "fight":
                        break
                    self.game.update(1 / 60, held=set())
            self.assertEqual(self.game.state, "knockout", move)
            self.assertIn(1, self.game.knockout_poses)

    def test_knockout_duration_and_frozen_combat_at_every_frame_rate(self):
        for fps in (30, 60, 120):
            self.start()
            self.game.match.fighters[1].health = 0
            self.game.update(.01, held=set())
            snapshot = [(f.x, f.elevation, f.health, f.attack_time) for f in self.game.match.fighters]
            remaining = self.game.match.remaining
            with patch.object(self.game.ai, "update", side_effect=AssertionError("CPU must stop after KO")):
                for _ in range(round(KNOCKOUT_DURATION * fps) - 1):
                    self.game.update(1 / fps, held={pygame.K_d, pygame.K_LSHIFT})
                self.assertEqual(self.game.state, "knockout")
                self.game.update(1 / fps, held=set())
            self.assertEqual(self.game.state, "result")
            self.assertEqual(self.game.match.remaining, remaining)
            self.assertEqual(snapshot, [(f.x, f.elevation, f.health, f.attack_time) for f in self.game.match.fighters])

    def test_knockout_ignores_attack_menu_and_mouse_inputs(self):
        self.start()
        self.game.match.fighters[1].health = 0
        self.game.update(.01, held=set())
        for key in (pygame.K_u, pygame.K_e, pygame.K_F2, pygame.K_ESCAPE, pygame.K_RETURN):
            self.key(key)
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(600, 348)))
        self.assertEqual(self.game.state, "knockout")
        self.assertIsNone(self.game.pending.attack)
        self.assertFalse(self.game.pending.counter)
        self.assertEqual(self.game.knockout_elapsed, 0)

    def test_knockout_freezes_for_focus_loss_and_quit_confirmation(self):
        self.start()
        self.game.match.fighters[1].health = 0
        self.game.update(.01, held=set())
        self.game.update(.1, held=set())
        self.game.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.game.update(.1, held=set())
        self.assertEqual(self.game.knockout_elapsed, .1)
        self.game.handle_event(pygame.event.Event(pygame.WINDOWFOCUSGAINED))
        self.game.update(.1, held=set())
        self.assertEqual(self.game.knockout_elapsed, .2)
        self.game.handle_event(pygame.event.Event(pygame.QUIT))
        self.game.update(.1, held=set())
        self.assertEqual(self.game.knockout_elapsed, .2)
        self.game.draw()
        self.key(pygame.K_ESCAPE)
        self.assertFalse(self.game.quit_prompt)
        self.assertEqual(self.game.state, "knockout")
        self.game.update(.1, held=set())
        self.assertAlmostEqual(self.game.knockout_elapsed, .3)

    def test_double_knockout_animates_both_fighters_without_awarding_a_win(self):
        self.start()
        for fighter in self.game.match.fighters:
            fighter.health = 0
        self.game.update(.01, held=set())
        self.assertEqual(self.game.state, "knockout")
        self.assertEqual(set(self.game.knockout_poses), {0, 1})
        self.assertIsNone(self.game.match.winner)
        self.assertEqual(self.game.progress.wins, 0)
        self.game.update(.1, held=set())
        self.game.update(.1, held=set())
        with patch.object(self.game.art, "text", wraps=self.game.art.text) as render:
            self.game.draw()
        self.assertIn("DOUBLE K.O.", [str(call.args[1]) for call in render.call_args_list])

    def test_timeouts_use_results_without_a_false_knockout(self):
        self.start()
        self.game.match.remaining = .001
        self.game.update(.01, held=set())
        self.assertEqual(self.game.state, "result")
        self.assertEqual(self.game.match.reason, "TIME")
        self.assertEqual(self.game.knockout_poses, {})

    def test_knockout_poses_animate_all_characters_without_mutating_combat(self):
        preview = os.environ.get("BURGERJAM_PREVIEW_DIR")
        for character in CHARACTERS:
            for facing in (-1, 1):
                self.start()
                player, enemy = self.game.match.fighters
                enemy.character, enemy.facing, enemy.health, enemy.elevation = character, facing, 0, 70
                player.x, enemy.x = 600 + facing * 100, 600
                self.game.update(.01, held=set())
                snapshot = (enemy.x, enemy.elevation, enemy.facing)
                for elapsed in (0, .18, .5, 1.25):
                    self.game.knockout_elapsed = elapsed
                    self.game.draw()
                    self.assertEqual((enemy.x, enemy.elevation, enemy.facing), snapshot)
                    if preview and character in ("Burger", "Pickle"):
                        Path(preview).mkdir(parents=True, exist_ok=True)
                        file = f"knockout-{character.lower()}-{facing}-{elapsed}.png"
                        pygame.image.save(self.game.screen, str(Path(preview) / file))

    def test_move_list_shows_six_normals_specials_and_combos_for_entire_roster(self):
        self.game.activate("moves")
        for character in CHARACTERS:
            self.game.move_character = character
            self.game.move_page = 0
            rows = self.game.move_rows()
            self.assertEqual(len(rows), 6)
            self.assertEqual([int(row[2]) for row in rows], [move_for(character, name).damage for name in NORMALS])
            for page in range(4):
                self.game.move_page = page
                self.assertTrue(self.game.move_rows())
                self.game.draw()
            self.game.move_page = 1
            self.assertEqual(self.game.move_rows()[0][0], move_for(character, "special").label)
        self.game.progress.bindings["lp"] = pygame.K_h
        self.game.move_page = 3
        self.assertTrue(self.game.move_rows()[0][1].startswith("H"))
        self.game.activate("moves_back")
        self.assertEqual(self.game.state, "menu")

    def test_every_screen_and_all_ten_character_moves_render(self):
        preview = os.environ.get("BURGERJAM_PREVIEW_DIR")
        if preview:
            Path(preview).mkdir(parents=True, exist_ok=True)
        for state in ("menu", "settings", "moves", "fight", "pause", "result"):
            if state == "fight":
                self.start()
            self.game.state = state
            self.game.result = "YOU WIN!"
            self.game.draw()
            if preview:
                pygame.image.save(self.game.screen, str(Path(preview) / f"{state}.png"))
        self.game.state = "moves"
        for page in range(4):
            self.game.move_page = page
            self.game.draw()
            if preview:
                pygame.image.save(self.game.screen, str(Path(preview) / f"moves-{page}.png"))
        self.start()
        self.game.debug = True
        self.game.match.fighters[0].x = 480
        self.game.match.fighters[1].x = 680
        sprites = set()
        for character in CHARACTERS:
            fighter = self.game.match.fighters[0]
            fighter.character = character
            sprites.add(pygame.image.tobytes(self.game.art.portrait(character), "RGBA"))
            for attack in NORMALS + ("special", "technique"):
                fighter.attack, fighter.spec = None, None
                fighter.start_attack(attack)
                fighter.attack_time = fighter.current_move.windup + .01
                self.game.match.fighters[1].blocking = True
                self.game.draw()
            if preview:
                pygame.image.save(self.game.screen, str(Path(preview) / (character.lower().replace(" ", "-") + ".png")))
        self.assertEqual(len(sprites), 10)
        self.assertEqual(self.game.screen.get_size(), (1200, 700))

    def test_w_and_space_both_jump(self):
        for key in (pygame.K_w, pygame.K_SPACE):
            self.start()
            self.key(key)
            self.game.update(.01, held=set())
            self.assertGreater(self.game.match.fighters[0].elevation, 0)

    def test_down_plus_air_attacks_trigger_the_two_dives(self):
        for key, move in ((pygame.K_j, "dive_kick"), (pygame.K_u, "elbow_drop")):
            self.start()
            self.game.match.fighters[0].elevation = 130
            self.key(key)
            self.game.update(.01, held={pygame.K_s})
            self.assertEqual(self.game.match.fighters[0].attack, move)
            self.assertLess(self.game.match.fighters[0].velocity, -900)

    def test_character_arm_palettes_and_alpha_match_the_roster(self):
        art = self.game.art
        for pose, original in art.arms.items():
            self.assertEqual(pygame.image.tobytes(art.character_arms["Burger"][pose], "RGBA"),
                             pygame.image.tobytes(original, "RGBA"))
            self.assertEqual(pygame.mask.from_surface(art.character_arms["Pickle"][pose]).count(),
                             pygame.mask.from_surface(original).count())
        pickle = art.character_arms["Pickle"]["idle"]
        pixels = [pickle.get_at((x, y)) for x in range(pickle.get_width()) for y in range(pickle.get_height())]
        self.assertTrue(all(color.g > color.r and color.g > color.b for color in pixels if color.a))
        palettes = {pygame.image.tobytes(art.character_arms[name]["idle"], "RGBA") for name in CHARACTERS}
        self.assertEqual(len(palettes), 10)

    def test_training_dummy_shows_damage_instead_of_health(self):
        self.game.activate("training")
        self.game.training.total_damage = 250
        with patch.object(self.game.art, "text", wraps=self.game.art.text) as render:
            self.game.draw()
        words = [str(call.args[1]) for call in render.call_args_list]
        self.assertIn("TOTAL DAMAGE", words)
        self.assertIn("250", words)
        self.assertNotIn("FLOUR SACK", words)

    def test_air_move_list_and_dive_poses_render_for_every_character(self):
        preview = os.environ.get("BURGERJAM_PREVIEW_DIR")
        self.game.activate("moves")
        self.game.move_page = 2
        self.game.draw()
        rows = self.game.move_rows()
        self.assertEqual([row[0] for row in rows], ["Downward Kick", "Elbow Drop"])
        self.assertIn("SPACE/W", rows[0][2])
        if preview:
            Path(preview).mkdir(parents=True, exist_ok=True)
            pygame.image.save(self.game.screen, str(Path(preview) / "air-moves.png"))
        for name in CHARACTERS:
            self.game.selected[0] = name
            self.game.activate("training")
            for move in DIVES:
                fighter = self.game.match.fighters[0]
                fighter.attack, fighter.spec, fighter.stun = None, None, 0
                fighter.elevation = 130
                fighter.start_attack(move)
                fighter.attack_time = fighter.current_move.windup + .01
                self.game.draw()
                if preview:
                    file = name.lower().replace(" ", "-") + "-" + move + ".png"
                    pygame.image.save(self.game.screen, str(Path(preview) / file))

    def test_enemy_health_bar_tracks_health(self):
        self.start()
        self.game.draw()
        full = self.game.screen.get_at((1100, 100))
        self.game.match.fighters[1].health = 20
        self.game.draw()
        self.assertNotEqual(self.game.screen.get_at((1100, 100)), full)

    def test_both_arms_are_visible_facing_either_direction(self):
        fighter = self.game.match.fighters[0]
        fighter.x = 600
        for facing in (1, -1):
            fighter.facing = facing
            self.game.screen.fill((0, 0, 0))
            self.game.draw_fighter(fighter, 0)
            x = 690 if facing == 1 else 490
            for y, height in ((FLOOR - 106, 26), (FLOOR - 65, 45)):
                region = self.game.screen.subsurface((x, y, 20, height))
                black = pygame.mask.from_threshold(region, (0, 0, 0), (1, 1, 1, 255))
                self.assertGreater(region.get_width() * region.get_height() - black.count(), 8)

    def test_punches_use_separate_arms_and_kicks_have_visible_leg(self):
        fighter = self.game.match.fighters[0]
        fighter.x = 600
        for facing in (1, -1):
            fighter.facing = facing
            def regions(attack):
                fighter.attack, fighter.spec = None, None
                if attack:
                    fighter.start_attack(attack)
                    fighter.attack_time = fighter.current_move.windup + .01
                self.game.screen.fill((0, 0, 0))
                self.game.draw_fighter(fighter, 0)
                x = 680 if facing == 1 else 435
                return tuple(pygame.image.tobytes(self.game.screen.subsurface((x, y, 85, height)), "RGB")
                             for y, height in ((FLOOR - 108, 28), (FLOOR - 50, 30)))
            idle, lp, hp, kick = regions(None), regions("lp"), regions("hp"), regions("lk")
            self.assertTrue(lp[0] != idle[0] and lp[1] == idle[1], "LP should use the rear arm")
            self.assertTrue(hp[0] == idle[0] and hp[1] != idle[1], "HP should use the front arm")
            self.assertTrue(kick != idle, "Kicks should visibly extend a leg")

    def test_no_audio_device_still_allows_play(self):
        pygame.mixer.quit()
        with patch("pygame.mixer.get_init", return_value=None):
            from burgerJam.game import Audio
            audio = Audio(.5)
            audio.play("lp")
            audio.set_volume(.8)
            self.assertFalse(audio.available)

    def test_quit_button_prompts_and_escape_cancels(self):
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(1070, 599)))
        self.assertTrue(self.game.running)
        self.assertTrue(self.game.quit_prompt)
        self.game.draw()
        self.key(pygame.K_ESCAPE)
        self.assertTrue(self.game.running)
        self.assertFalse(self.game.quit_prompt)
        self.assertEqual(self.game.state, "menu")
        self.assertEqual(self.game.menu_focus, 5)

    def test_grill_menu_button_starts_training_without_using_cpu(self):
        rect = next(rect for rect, _, action in self.game.buttons() if action == "training")
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=rect.center))
        self.assertEqual(self.game.mode, "training")
        self.assertEqual(self.game.countdown, 0)
        self.assertTrue(self.game.match.training)
        with patch.object(self.game.ai, "update", side_effect=AssertionError("Training must not use the CPU")):
            self.game.update(.1, held=set())
        self.assertIsNone(self.game.match.fighters[1].attack)

    def test_training_uses_selected_character_and_f3_resets_attempt(self):
        self.game.selected[0] = "Hot Dog"
        self.game.activate("training")
        self.key(pygame.K_u)
        self.game.update(.1, held=set())
        self.assertGreater(self.game.training.last_damage, 0)
        best = self.game.training.best_damage
        self.key(pygame.K_F3)
        self.assertEqual(self.game.match.fighters[0].character, "Hot Dog")
        self.assertEqual([fighter.health for fighter in self.game.match.fighters], [100, 100])
        self.assertEqual(self.game.training.best_damage, best)
        self.assertEqual(self.game.match.fighters[0].combo_hits, 0)
        self.assertIsNone(self.game.pending.attack)

    def test_training_never_awards_wins_or_enters_result_screen(self):
        self.game.activate("training")
        self.game.match.fighters[1].health = 1
        self.game.match.remaining = 0
        self.key(pygame.K_o)
        for _ in range(40):
            self.game.update(1 / 60, held=set())
        self.game.finish_match()
        self.assertEqual(self.game.state, "fight")
        self.assertFalse(self.game.match.over)
        self.assertEqual(self.game.progress.wins, 0)
        self.assertFalse(self.path.exists())

    def test_training_guard_shortcut_and_pause_moves_settings_preserve_session(self):
        self.game.activate("training")
        session = self.game.training
        self.key(pygame.K_F4)
        self.game.update(.01, held=set())
        self.assertEqual(session.dummy_mode, "guard")
        self.assertTrue(self.game.match.fighters[1].blocking)
        self.key(pygame.K_F4)
        self.game.update(.01, held=set())
        self.assertTrue(self.game.match.fighters[1].crouching)
        self.key(pygame.K_F2)
        self.game.update(.1, held=set())
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.game.state, "fight")
        self.key(pygame.K_ESCAPE)
        self.game.activate("settings")
        self.game.activate("back")
        self.assertEqual(self.game.state, "pause")
        self.assertIs(self.game.training, session)
        self.game.activate("training_reset")
        self.assertEqual(self.game.state, "fight")
        self.game.activate("menu")
        self.game.start_match()
        self.assertEqual(self.game.mode, "cpu")
        self.assertFalse(self.game.match.training)
        self.assertIsNone(self.game.training)

    def test_training_art_hud_and_pause_render(self):
        self.game.activate("training")
        self.key(pygame.K_u)
        self.game.update(.1, held=set())
        self.game.draw()
        self.assertNotEqual(pygame.image.tobytes(self.game.art.kitchen, "RGB"),
                            pygame.image.tobytes(self.game.art.background, "RGB"))
        preview = os.environ.get("BURGERJAM_PREVIEW_DIR")
        if preview:
            Path(preview).mkdir(parents=True, exist_ok=True)
            pygame.image.save(self.game.screen, str(Path(preview) / "grill-training.png"))
        self.key(pygame.K_ESCAPE)
        self.game.draw()
        if preview:
            pygame.image.save(self.game.screen, str(Path(preview) / "grill-pause.png"))

    def test_training_shortcuts_cannot_be_rebound(self):
        self.game.activate("settings")
        self.game.activate("bind:lp")
        for key in (pygame.K_F3, pygame.K_F4):
            self.key(key)
            self.assertEqual(self.game.capture, "lp")

    def test_result_quit_can_cancel_or_confirm_with_mouse(self):
        self.game.state, self.game.result = "result", "YOU WIN!"
        self.game.activate("quit")
        self.game.draw()
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(490, 404)))
        self.assertFalse(self.game.quit_prompt)
        self.assertTrue(self.game.running)
        self.assertEqual(self.game.state, "result")
        self.game.activate("quit")
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(710, 404)))
        self.assertFalse(self.game.running)

    def test_window_close_prompts_and_freezes_until_answered(self):
        self.start()
        self.key(pygame.K_u)
        self.game.handle_event(pygame.event.Event(pygame.QUIT))
        self.game.update(.1, held={pygame.K_d})
        self.assertEqual(self.game.match.remaining, 60)
        self.assertIsNone(self.game.pending.attack)
        self.key(pygame.K_RETURN)
        self.assertTrue(self.game.running)
        self.assertFalse(self.game.quit_prompt)
        self.game.handle_event(pygame.event.Event(pygame.QUIT))
        self.key(pygame.K_RIGHT)
        self.key(pygame.K_RETURN)
        self.assertFalse(self.game.running)

    def test_run_drains_event_queue_and_saves_on_confirmed_quit(self):
        pygame.event.clear()
        for _ in range(200):
            pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(20, 20)))
        for event in (pygame.event.Event(pygame.QUIT),
                      pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT),
                      pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN)):
            pygame.event.post(event)
        with patch.object(self.game, "update", wraps=self.game.update) as update:
            self.game.run()
            self.assertEqual(update.call_count, 0)
        self.assertFalse(pygame.get_init())
        self.assertTrue(self.path.exists())

    def test_launcher_works_outside_repo_and_import_does_not_open_window(self):
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run([sys.executable, str(ROOT / "burgerJam" / "burgrerfight.py"), "--help"],
                                cwd=self.temporary.name, env=environment, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import pygame; "
                "import burgerJam.burgrerfight; assert not pygame.get_init(); "
                "from burgerJam.game import Game; "
                "game = Game(save_path='test.json', mute=True); game.draw(); pygame.quit()")
        result = subprocess.run([sys.executable, "-c", code, str(ROOT)], cwd=self.temporary.name,
                                env=environment, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
