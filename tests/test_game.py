"""Exercise the real Pygame surfaces and event handlers without a window."""

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

from burgerJam.combat import ATTACKS, FLOOR, Controls
from burgerJam.game import DEFAULT_BINDINGS, Game
from burgerJam.progress import CHARACTERS, Progress

ROOT = Path(__file__).resolve().parents[1]


class GameTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "save.json"
        self.game = Game(save_path=self.path, mute=True, seed=42)
        self.addCleanup(pygame.quit)

    def key(self, key, mod=0):
        self.game.handle_event(pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod))

    def start(self, mode="versus"):
        self.game.start_match(mode)
        self.game.countdown = 0

    def test_menu_keyboard_navigation_and_character_selection(self):
        self.key(pygame.K_RIGHT)
        self.assertEqual(self.game.selected[0], "Tomato")
        self.key(pygame.K_RIGHT, pygame.KMOD_SHIFT)
        self.assertEqual(self.game.selected[1], "Burger")
        self.key(pygame.K_DOWN)
        self.key(pygame.K_RETURN)
        self.assertEqual(self.game.mode, "versus")
        self.assertEqual(self.game.state, "fight")

    def test_locked_roster_card_cannot_be_selected(self):
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(580, 340)))
        self.assertEqual(self.game.selected[0], "Burger")

    def test_local_players_have_independent_input_and_damage(self):
        self.start()
        a, b = self.game.match.fighters
        a.x, b.x = 400, 500
        self.key(pygame.K_j)
        for _ in range(15):
            self.game.update(1 / 60, held=set())
        self.assertEqual(a.health, 92)
        self.assertEqual(b.health, 100)
        before = (a.x, b.x)
        self.game.update(1 / 60, held={pygame.K_a, pygame.K_RIGHT})
        self.assertLess(a.x, before[0])
        self.assertGreater(b.x, before[1])

    def test_mouse_attacks_are_solo_only_and_animate_without_extra_clicks(self):
        self.start("cpu")
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
        self.game.update(1 / 60, held=set())
        self.assertEqual(self.game.match.fighters[0].attack, "jab")
        for _ in range(40):
            self.game.update(1 / 60, held=set())
        self.assertIsNone(self.game.match.fighters[0].attack)
        self.start("versus")
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(0, 0)))
        self.assertIsNone(self.game.pending[0].attack)

    def test_pause_and_focus_loss_freeze_time_and_clear_inputs(self):
        self.start()
        self.key(pygame.K_f)
        self.key(pygame.K_ESCAPE)
        remaining = self.game.match.remaining
        self.game.update(.1, held={pygame.K_d})
        self.assertEqual(self.game.match.remaining, remaining)
        self.assertIsNone(self.game.pending[0].attack)
        self.key(pygame.K_ESCAPE)
        self.assertEqual(self.game.state, "fight")
        self.game.handle_event(pygame.event.Event(pygame.WINDOWFOCUSLOST))
        self.assertEqual(self.game.state, "pause")

    def test_countdown_prevents_early_attacks_and_timer_changes(self):
        self.game.start_match("versus")
        self.key(pygame.K_f)
        self.game.update(.1, held={pygame.K_d})
        self.assertEqual(self.game.match.remaining, 60)
        self.assertEqual(self.game.match.fighters[0].x, 330)
        self.assertIsNone(self.game.match.fighters[0].attack)

    def test_settings_remap_rejects_duplicates_and_reserved_keys(self):
        self.game.activate("settings")
        self.game.activate("bind:p1_jab")
        self.key(pygame.K_j)
        self.assertEqual(self.game.capture, "p1_jab")
        self.key(pygame.K_RETURN)
        self.assertEqual(self.game.capture, "p1_jab")
        self.key(pygame.K_h)
        self.assertIsNone(self.game.capture)
        self.assertEqual(self.game.progress.bindings["p1_jab"], pygame.K_h)
        self.game.activate("louder")
        self.game.activate("mute")
        self.game.activate("back")
        restored = Progress.load(DEFAULT_BINDINGS, self.path)
        self.assertEqual(restored.bindings["p1_jab"], pygame.K_h)
        self.assertEqual(restored.volume, .45)
        self.assertTrue(restored.muted)
        self.assertEqual(self.game.state, "menu")

    def test_custom_binding_is_used_in_gameplay(self):
        self.game.progress.bindings["p1_jab"] = pygame.K_h
        self.start()
        self.key(pygame.K_f)
        self.assertIsNone(self.game.pending[0].attack)
        self.key(pygame.K_h)
        self.game.update(.01, held=set())
        self.assertEqual(self.game.match.fighters[0].attack, "jab")

    def test_cpu_victory_awards_one_win_and_unlocks_character(self):
        self.start("cpu")
        self.game.match.fighters[1].health = 0
        self.game.update(.01, held=set())
        self.assertEqual(self.game.state, "result")
        self.assertEqual(self.game.progress.wins, 1)
        self.assertEqual(self.game.unlocked, ["Italian Scallion"])
        self.game.update(.1, held=set())
        self.game.finish_match()
        self.assertEqual(self.game.progress.wins, 1)
        self.assertEqual(Progress.load(DEFAULT_BINDINGS, self.path).wins, 1)
        self.game.activate("rematch")
        self.assertEqual(self.game.state, "fight")
        self.assertEqual([f.health for f in self.game.match.fighters], [100, 100])

    def test_local_matches_and_cpu_losses_do_not_award_unlocks(self):
        for mode, loser in (("versus", 1), ("cpu", 0)):
            self.start(mode)
            self.game.match.fighters[loser].health = 0
            self.game.update(.01, held=set())
            self.assertEqual(self.game.progress.wins, 0)

    def test_every_screen_and_character_renders(self):
        preview = os.environ.get("BURGERJAM_PREVIEW_DIR")
        if preview:
            Path(preview).mkdir(parents=True, exist_ok=True)
        for state in ("menu", "settings", "fight", "pause", "result"):
            if state == "fight":
                self.start("cpu")
            self.game.state = state
            self.game.result = "YOU WIN!"
            self.game.draw()
            if preview:
                pygame.image.save(self.game.screen, str(Path(preview) / f"{state}.png"))
        self.start()
        self.game.debug = True
        self.game.match.fighters[0].x = 480
        self.game.match.fighters[1].x = 600
        for name in CHARACTERS:
            self.game.match.fighters[0].character = name
            self.game.match.fighters[0].start_attack("jab")
            self.game.match.fighters[0].attack_time = .1
            self.game.match.fighters[1].blocking = True
            self.game.draw()
        if preview:
            pygame.image.save(self.game.screen, str(Path(preview) / "combat.png"))
        self.assertEqual(self.game.screen.get_size(), (1200, 700))

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
            with self.subTest(facing=facing):
                fighter.facing = facing
                self.game.screen.fill((0, 0, 0))
                self.game.draw_fighter(fighter, 0)
                x = 690 if facing == 1 else 490
                for y, height in ((FLOOR - 106, 26), (FLOOR - 65, 45)):
                    region = self.game.screen.subsurface((x, y, 20, height))
                    visible = pygame.mask.from_threshold(region, (0, 0, 0), (1, 1, 1, 255))
                    self.assertGreater(region.get_width() * region.get_height() - visible.count(), 8)

    def test_jab_and_cross_animate_different_arms(self):
        fighter = self.game.match.fighters[0]
        fighter.x = 600
        for facing in (1, -1):
            with self.subTest(facing=facing):
                fighter.facing = facing
                def arm_regions(attack):
                    fighter.attack = attack
                    fighter.attack_time = ATTACKS[attack].windup + .01 if attack else 0
                    self.game.screen.fill((0, 0, 0))
                    self.game.draw_fighter(fighter, 0)
                    x = 680 if facing == 1 else 435
                    return tuple(pygame.image.tobytes(self.game.screen.subsurface((x, y, 85, height)), "RGB")
                                 for y, height in ((FLOOR - 108, 28), (FLOOR - 50, 30)))
                idle = arm_regions(None)
                jab = arm_regions("jab")
                cross = arm_regions("cross")
                self.assertTrue(jab[0] != idle[0], "Jab should animate the rear arm")
                self.assertTrue(jab[1] == idle[1], "Jab should leave the front arm idle")
                self.assertTrue(cross[0] == idle[0], "Cross should leave the rear arm idle")
                self.assertTrue(cross[1] != idle[1], "Cross should animate the front arm")

    def test_no_audio_device_still_allows_play(self):
        pygame.mixer.quit()
        with patch("pygame.mixer.get_init", return_value=None):
            from burgerJam.game import Audio
            audio = Audio(.5)
            audio.play("jab")
            audio.set_volume(.8)
            self.assertFalse(audio.available)

    def test_run_drains_event_queue_and_quits_cleanly(self):
        pygame.event.clear()
        for _ in range(200):
            pygame.event.post(pygame.event.Event(pygame.MOUSEMOTION, pos=(20, 20)))
        pygame.event.post(pygame.event.Event(pygame.QUIT))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RIGHT))
        pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
        with patch.object(self.game, "update", wraps=self.game.update) as update:
            self.game.run()
            self.assertEqual(update.call_count, 0)
        self.assertFalse(self.game.running)
        self.assertFalse(pygame.get_init())
        self.assertTrue(self.path.exists())

    def test_quit_button_asks_first_and_escape_cancels(self):
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(1000, 540)))
        self.assertTrue(self.game.running)
        self.assertTrue(self.game.quit_prompt)
        self.game.draw()
        self.key(pygame.K_ESCAPE)
        self.assertTrue(self.game.running)
        self.assertFalse(self.game.quit_prompt)
        self.assertEqual(self.game.state, "menu")
        self.assertEqual(self.game.menu_focus, 3)

    def test_result_quit_can_be_cancelled_or_confirmed_with_mouse(self):
        self.game.state = "result"
        self.game.result = "YOU WIN!"
        self.game.activate("quit")
        self.game.draw()
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(490, 404)))
        self.assertFalse(self.game.quit_prompt)
        self.assertTrue(self.game.running)
        self.assertEqual(self.game.state, "result")
        self.game.activate("quit")
        self.game.handle_event(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(710, 404)))
        self.assertFalse(self.game.running)

    def test_window_close_prompts_and_freezes_match_until_answered(self):
        self.start()
        self.key(pygame.K_f)
        self.game.handle_event(pygame.event.Event(pygame.QUIT))
        self.assertTrue(self.game.running)
        self.assertTrue(self.game.quit_prompt)
        self.game.update(.1, held={pygame.K_d})
        self.assertEqual(self.game.match.remaining, 60)
        self.assertEqual(self.game.match.fighters[0].x, 330)
        self.assertIsNone(self.game.pending[0].attack)
        # Enter defaults to Cancel, so opening the prompt cannot immediately exit.
        self.key(pygame.K_RETURN)
        self.assertTrue(self.game.running)
        self.assertFalse(self.game.quit_prompt)
        self.game.handle_event(pygame.event.Event(pygame.QUIT))
        self.key(pygame.K_RIGHT)
        self.key(pygame.K_RETURN)
        self.assertFalse(self.game.running)

    def test_launcher_works_outside_repository_and_import_has_no_window(self):
        environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run([sys.executable, str(ROOT / "burgerJam" / "burgrerfight.py"), "--help"],
                                cwd=self.temporary.name, env=environment, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--save-file", result.stdout)
        code = ("import sys; sys.path.insert(0, sys.argv[1]); import pygame; "
                "import burgerJam.burgrerfight; assert not pygame.get_init(); "
                "from burgerJam.game import Game; "
                "game = Game(save_path='temporary-profile.json', mute=True); "
                "game.draw(); pygame.quit()")
        result = subprocess.run([sys.executable, "-c", code, str(ROOT)], cwd=self.temporary.name,
                                env=environment, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
