"""Pygame presentation, menus, input and audio for Street Burger."""

from dataclasses import dataclass, replace
import math
from pathlib import Path
import random

import pygame

from .combat import (ATTACKS, DIFFICULTIES, DIVES, NORMALS, FLOOR, HEIGHT, WIDTH,
                     LEFT, RIGHT, SHIELD_MAX, SHIELD_BREAK_TIME, PARRY_TIME, PARRY_INPUT_WINDOW, COUNTER_TIME,
                     COUNTER_RECOVERY, RIPOSTE_WINDOW, Controls, Fighter, Match, OpponentAI, move_for)
from .progress import CHARACTERS, UNLOCK_WINS, Progress
from .roster import PROFILES
from .kitchen import make_dummy, make_kitchen
from .training import TrainingSession

ASSETS = Path(__file__).resolve().parent
INK = (22, 27, 34)
PANEL = (32, 39, 48)
CREAM = (255, 242, 212)
MUTED = (167, 177, 181)
YELLOW = (255, 201, 80)
RED = (241, 88, 63)
BLUE = (91, 209, 211)
GREEN = (137, 207, 107)
DEFAULT_BINDINGS = {
    "left": pygame.K_a, "down": pygame.K_s, "right": pygame.K_d, "jump": pygame.K_SPACE, "jump_alt": pygame.K_w,
    "lp": pygame.K_u, "mp": pygame.K_i, "hp": pygame.K_o,
    "lk": pygame.K_j, "mk": pygame.K_k, "hk": pygame.K_l,
    "block": pygame.K_LSHIFT, "parry": pygame.K_q, "counter": pygame.K_e,
}
NUMPAD_BINDINGS = dict(DEFAULT_BINDINGS, lp=pygame.K_KP4, mp=pygame.K_KP5, hp=pygame.K_KP6,
                       lk=pygame.K_KP1, mk=pygame.K_KP2, hk=pygame.K_KP3)
RESERVED_KEYS = {pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_F1, pygame.K_F2, pygame.K_F3, pygame.K_F4}
ACTIONS = tuple(DEFAULT_BINDINGS)
ACTION_LABELS = dict(left="Left", down="Down / Crouch", right="Right", jump="Jump", jump_alt="Jump (alternate)", block="Shield",
                     parry="Parry", counter="Counter", **{name: ATTACKS[name].label for name in NORMALS})
KNOCKOUT_DURATION, KNOCKOUT_HITSTOP, KNOCKOUT_FALL = 1.6, .12, .85


class Audio:
    def __init__(self, volume):
        self.sounds = {}
        self.available = bool(pygame.mixer.get_init())
        if self.available:
            try:
                for name, file in (("jab", "low_punch.wav"), ("cross", "high_punch.wav"),
                                   ("block", "normal_punch.wav")):
                    self.sounds[name] = pygame.mixer.Sound(str(ASSETS / file))
                pygame.mixer.music.load(str(ASSETS / "burgarena.mp3"))
                pygame.mixer.music.set_volume(volume * .5)
                pygame.mixer.music.play(-1)
            except (pygame.error, OSError):
                self.available = False
        self.set_volume(volume)

    def set_volume(self, volume):
        if self.available:
            pygame.mixer.music.set_volume(volume * .5)
            for sound in self.sounds.values():
                sound.set_volume(volume)

    def play(self, name):
        if name not in self.sounds and name not in ("block", "jab", "cross"):
            name = "jab" if name in ("lp", "lk") else "cross"
        if self.available and name in self.sounds:
            self.sounds[name].play()


class Art:
    def __init__(self):
        self.background = pygame.transform.smoothscale(
            pygame.image.load(str(ASSETS / "bcg.png")).convert(), (WIDTH, HEIGHT))
        self.eyes = pygame.image.load(str(ASSETS / "eyes_right.png")).convert_alpha()
        self.arms = {name: pygame.image.load(str(ASSETS / file)).convert_alpha()
                     for name, file in (("idle", "arm_idle.png"), ("windup", "arm_punching.png"),
                                        ("active", "arm_punched.png"), ("block", "arm_block.png"))}
        self.bodies = {name: self.make_body(name) for name in CHARACTERS}
        self.character_arms = {name: {pose: self.color_arm(sprite, PROFILES[name].arm_color)
                                     for pose, sprite in self.arms.items()} for name in CHARACTERS}
        self.fonts = {}
        self.kitchen = make_kitchen()
        self.dummy = make_dummy()

    @staticmethod
    def color_arm(sprite, color):
        if color is None:
            return sprite
        # Keep the jam sprite's silhouette, alpha and shading while changing its palette.
        arm = pygame.transform.grayscale(sprite)
        arm.fill((38, 38, 38), special_flags=pygame.BLEND_RGB_ADD)
        arm.fill(color, special_flags=pygame.BLEND_RGB_MULT)
        return arm

    def make_body(self, name):
        body = pygame.Surface((100, 100), pygame.SRCALPHA)
        if name == "Burger":
            body.blit(pygame.image.load(str(ASSETS / "burgrer.png")).convert_alpha(), (0, 0))
        elif name == "Tomato":
            pygame.draw.ellipse(body, (232, 68, 49), (8, 19, 84, 77))
            pygame.draw.ellipse(body, (174, 39, 38), (17, 56, 71, 36))
            pygame.draw.ellipse(body, (255, 132, 95), (22, 27, 25, 13))
            pygame.draw.polygon(body, (87, 158, 63),
                                [(49, 29), (20, 13), (41, 15), (48, 3), (57, 17),
                                 (81, 9), (65, 30), (76, 37), (52, 30), (33, 39)])
        elif name == "Italian Scallion":
            for x, top, lean in ((26, 4, -17), (42, 0, -5), (60, 6, 13), (72, 13, 18)):
                pygame.draw.polygon(body, (74, 155, 76),
                                    [(x, 61), (x + lean - 5, top), (x + lean + 5, top), (x + 9, 63)])
                pygame.draw.line(body, (148, 208, 105), (x + 4, 53), (x + lean, top + 7), 3)
            pygame.draw.ellipse(body, (229, 233, 188), (22, 35, 58, 62))
            pygame.draw.ellipse(body, (255, 250, 214), (25, 37, 37, 50))
            for x in (39, 49, 59):
                pygame.draw.line(body, (192, 158, 103), (x, 91), (x - 4, 99), 2)
        elif name == "French Fries":
            for x, top in ((17, 10), (30, 2), (43, 9), (56, 0), (69, 7), (80, 17)):
                pygame.draw.rect(body, (238, 165, 45), (x, top, 10, 60), border_radius=2)
                pygame.draw.line(body, (255, 222, 112), (x + 2, top + 3), (x + 2, 50), 3)
            pygame.draw.polygon(body, (224, 69, 51), [(9, 39), (92, 39), (80, 96), (22, 96)])
            pygame.draw.polygon(body, (173, 45, 44), [(69, 40), (92, 39), (80, 96), (62, 96)])
            pygame.draw.line(body, CREAM, (20, 77), (77, 77), 5)
        elif name == "Pizza":
            pygame.draw.polygon(body, (234, 158, 58), [(4, 15), (96, 15), (50, 98)])
            pygame.draw.polygon(body, (255, 213, 91), [(12, 23), (87, 23), (50, 88)])
            pygame.draw.line(body, (183, 99, 47), (10, 14), (91, 14), 15)
            pygame.draw.line(body, (241, 183, 91), (10, 10), (91, 10), 8)
            for pos in ((30, 31), (69, 34), (48, 67)):
                pygame.draw.circle(body, (195, 59, 44), pos, 9)
                pygame.draw.circle(body, (231, 94, 58), (pos[0] - 2, pos[1] - 2), 4)
        elif name == "Hot Dog":
            pygame.draw.ellipse(body, (220, 153, 72), (9, 19, 82, 77))
            pygame.draw.ellipse(body, (255, 202, 112), (13, 22, 68, 67))
            pygame.draw.rect(body, (158, 59, 39), (33, 13, 37, 80), border_radius=18)
            pygame.draw.lines(body, (249, 201, 53), False,
                              [(43, 24), (60, 34), (43, 44), (60, 54), (43, 64), (60, 74), (45, 84)], 5)
        elif name == "Pickle":
            pygame.draw.rect(body, (73, 139, 48), (22, 6, 57, 91), border_radius=26)
            pygame.draw.ellipse(body, (128, 185, 67), (27, 12, 27, 70))
            for x, y in ((32, 24), (65, 23), (66, 58), (37, 73), (60, 86), (26, 50)):
                pygame.draw.circle(body, (47, 110, 43), (x, y), 4)
                pygame.draw.circle(body, (151, 195, 79), (x - 1, y - 1), 2)
        elif name in ("Ketchup", "Mustard"):
            sauce = (214, 56, 45) if name == "Ketchup" else (235, 180, 36)
            light = (247, 99, 73) if name == "Ketchup" else (255, 218, 79)
            pygame.draw.polygon(body, sauce, [(23, 96), (18, 40), (32, 25), (38, 22),
                                             (38, 10), (61, 10), (61, 22), (70, 26), (83, 41), (77, 96)])
            pygame.draw.rect(body, light, (25, 41, 14, 48), border_radius=6)
            pygame.draw.rect(body, (236, 224, 182), (31, 51, 40, 31), border_radius=5)
            pygame.draw.rect(body, sauce, (44, 1, 12, 15), border_radius=3)
            pygame.draw.circle(body, sauce, (51, 70), 8)
        elif name == "Milk Shake":
            pygame.draw.line(body, (229, 85, 104), (61, 48), (76, 2), 7)
            pygame.draw.line(body, CREAM, (64, 35), (68, 21), 3)
            pygame.draw.polygon(body, (229, 135, 164), [(18, 40), (83, 40), (72, 97), (30, 97)])
            pygame.draw.polygon(body, (255, 187, 203), [(23, 45), (43, 45), (47, 92), (33, 92)])
            for x, y, radius in ((30, 34, 17), (48, 27, 21), (69, 34, 16)):
                pygame.draw.circle(body, (255, 240, 213), (x, y), radius)
            pygame.draw.circle(body, (218, 62, 70), (49, 10), 9)
        # Multiplication preserves source alpha and shades the underside.
        shade = pygame.Surface((100, 100), pygame.SRCALPHA)
        shade.fill((255, 255, 255, 255))
        for y in range(100):
            value = 255 - int(max(0, y - 35) * .55)
            pygame.draw.line(shade, (value, value, value, 255), (0, y), (99, y))
        body.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        for x in range(100):
            value = 255 - int(max(0, x - 30) * .35)
            pygame.draw.line(shade, (value, value, value, 255), (x, 0), (x, 99))
        body.blit(shade, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return body

    def text(self, target, words, pos, size=24, color=CREAM, center=False, right=False):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(None, size)
        surface = self.fonts[size].render(str(words), True, color)
        rect = surface.get_rect(center=pos) if center else surface.get_rect(topleft=pos)
        if right:
            rect.topright = pos
        target.blit(surface, rect)
        return rect

    def portrait(self, name, size=145, facing=1):
        body = self.bodies[name].copy()
        eye_y = {"Italian Scallion": 47, "French Fries": 39, "Hot Dog": 39,
                 "Ketchup": 44, "Mustard": 44, "Milk Shake": 50}.get(name, 32)
        body.blit(self.eyes, (35, eye_y))
        if facing == -1:
            body = pygame.transform.flip(body, True, False)
        return pygame.transform.scale(body, (size, size))


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    color: tuple


class Game:
    def __init__(self, save_path=None, mute=False, seed=None):
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Street Burger | Six Button Food Fight")
        self.clock = pygame.time.Clock()
        self.art = Art()
        self.progress = Progress.load(DEFAULT_BINDINGS, save_path)
        if any(key in RESERVED_KEYS or not pygame.key.name(key) for key in self.progress.bindings.values()):
            self.progress.bindings = dict(DEFAULT_BINDINGS)
        self.muted = mute or self.progress.muted
        self.audio = Audio(0 if self.muted else self.progress.volume)
        self.random = random.Random(seed)
        self.state = "menu"
        self.settings_return = "menu"
        self.moves_return = "menu"
        self.move_character = "Burger"
        self.move_page = 0
        self.running = True
        self.quit_prompt = False
        self.quit_previous_focus = 0
        self.mode = "cpu"
        self.training = None
        self.selected = ["Burger", "Tomato"]
        self.match = Match()
        self.ai = OpponentAI(seed, self.progress.difficulty)
        self.countdown = 0
        self.pending = Controls()
        self.motion_samples = []
        self.event_keys = set()
        self.mouse_block = False
        self.debug = False
        self.menu_focus = 0
        self.capture = None
        self.notice = ""
        self.result = ""
        self.unlocked = []
        self.particles = []
        self.knockout_elapsed = 0
        self.knockout_paused = False
        self.knockout_poses = {}

    def key_label(self, action):
        return pygame.key.name(self.progress.bindings[action]).upper()

    def jump_label(self):
        return self.key_label("jump") + "/" + self.key_label("jump_alt")

    @staticmethod
    def card_rect(index):
        return pygame.Rect(60 + (index % 5) * 218, 188 + (index // 5) * 164, 200, 152)

    def start_match(self, mode="cpu"):
        if mode in ("cpu", "training"):
            self.knockout_elapsed = 0
            self.knockout_paused = False
            self.knockout_poses.clear()
        if mode == "training":
            self.training = TrainingSession(self.selected[0])
            self.match = self.training.match
            self.mode, self.state, self.countdown = "training", "fight", 0
            self.clear_input()
            self.particles.clear()
            self.unlocked = []
            return True
        if mode != "cpu":
            self.notice = "Local versus is unavailable with the six-button keyboard layout."
            return False
        self.mode = "cpu"
        self.training = None
        self.match = Match([Fighter(330, 1, self.selected[0]), Fighter(870, -1, self.selected[1])])
        self.ai = OpponentAI(self.random.randrange(2 ** 32), self.progress.difficulty)
        self.state = "fight"
        self.countdown = 2.4
        self.clear_input()
        self.particles.clear()
        self.unlocked = []
        return True

    def reset_training(self):
        if self.training is not None:
            self.training.reset()
            self.clear_input()
            self.particles.clear()

    def clear_input(self):
        self.pending = Controls()
        self.motion_samples = []
        self.event_keys.clear()
        self.mouse_block = False
        for fighter in self.match.fighters:
            fighter.motion.samples.clear()
            fighter.buffered = None

    def finish_match(self):
        if self.state != "fight" or self.mode == "training":
            return
        winner = self.match.winner
        self.result = "DRAW!" if winner is None else "YOU WIN!" if winner == 0 else "THE HOUSE WINS"
        if winner == 0:
            before = {name for name in CHARACTERS if self.progress.unlocked(name)}
            self.progress.wins += 1
            self.unlocked = [name for name in CHARACTERS if self.progress.unlocked(name) and name not in before]
            self.progress.save()
        self.state = "knockout" if self.match.reason == "KO" else "result"
        if self.state == "knockout":
            self.knockout_elapsed = 0
            self.knockout_paused = False
            self.knockout_poses = {index: self.make_knockout_pose(fighter)
                                   for index, fighter in enumerate(self.match.fighters) if fighter.health == 0}
            self.audio.play("cross")
        self.menu_focus = 0
        self.clear_input()

    def cycle_character(self, player, direction):
        index = CHARACTERS.index(self.selected[player])
        for offset in range(1, len(CHARACTERS) + 1):
            candidate = CHARACTERS[(index + offset * direction) % len(CHARACTERS)]
            if self.progress.unlocked(candidate):
                self.selected[player] = candidate
                return

    def buttons(self):
        if self.quit_prompt:
            return [(pygame.Rect(390, 380, 200, 48), "CANCEL", "cancel_quit"),
                    (pygame.Rect(610, 380, 200, 48), "YES, QUIT", "confirm_quit")]
        if self.state == "menu":
            return [(pygame.Rect(x, 575, width, 48), label, action) for x, width, label, action in (
                (60, 200, "FIGHT THE CPU", "cpu"),
                (270, 212, "GO TO THE GRILL", "training"),
                (492, 174, "CPU: " + self.progress.difficulty.upper(), "difficulty"),
                (676, 140, "MOVE LIST", "moves"),
                (826, 190, "SETTINGS / KEYS", "settings"), (1026, 114, "QUIT", "quit"))]
        if self.state == "settings":
            buttons = [(pygame.Rect(340, 134, 52, 40), "-", "quieter"),
                       (pygame.Rect(808, 134, 52, 40), "+", "louder"),
                       (pygame.Rect(900, 134, 160, 40), "UNMUTE" if self.muted else "MUTE", "mute"),
                       (pygame.Rect(215, 203, 340, 38), "U I O / J K L PRESET", "letters"),
                       (pygame.Rect(645, 203, 340, 38), "NUMPAD 4 5 6 / 1 2 3", "numpad")]
            columns = (("left", "down", "right", "jump", "jump_alt", "block", "parry", "counter"), NORMALS)
            for column, actions in enumerate(columns):
                for row, action in enumerate(actions):
                    buttons.append((pygame.Rect(110 + column * 510, 285 + row * 35, 470, 30),
                                    f"{ACTION_LABELS[action]}   [ {self.key_label(action)} ]", "bind:" + action))
            buttons += [(pygame.Rect(340, 610, 250, 44), "RESTORE KEYS", "reset"),
                        (pygame.Rect(610, 610, 250, 44), "BACK", "back")]
            return buttons
        if self.state == "moves":
            buttons = [(pygame.Rect(60 + index * 273, 161, 261, 40), label, "page:" + str(index))
                       for index, label in enumerate(("BASICS / DEFENSE", "CHARACTER SPECIALS", "AIR / DIVES", "COMBOS"))]
            buttons += [(pygame.Rect(60, 632, 170, 42), "< FIGHTER", "previous_fighter"),
                        (pygame.Rect(250, 632, 170, 42), "FIGHTER >", "next_fighter"),
                        (pygame.Rect(930, 632, 210, 42), "BACK", "moves_back")]
            return buttons
        if self.state == "pause":
            if self.mode == "training":
                options = (("RESUME", "resume"), ("RESET PRACTICE", "training_reset"),
                           ("DUMMY: " + self.training.dummy_mode.upper(), "training_dummy"),
                           ("MOVE LIST", "moves"), ("SETTINGS", "settings"), ("MAIN MENU", "menu"))
                return [(pygame.Rect(350 + (index % 2) * 260, 326 + (index // 2) * 56, 240, 44), label, action)
                        for index, (label, action) in enumerate(options)]
            options = (("RESUME", "resume"), ("MOVE LIST", "moves"), ("SETTINGS", "settings"), ("MAIN MENU", "menu"))
        elif self.state == "result":
            options = (("REMATCH", "rematch"), ("CHARACTERS", "menu"), ("MOVE LIST", "moves"), ("QUIT", "quit"))
        else:
            return []
        return [(pygame.Rect(410, 326 + index * 56, 380, 44), label, action)
                for index, (label, action) in enumerate(options)]

    def activate(self, action):
        if action == "cpu":
            self.start_match()
        elif action == "training":
            self.start_match("training")
        elif action == "training_reset" and self.training is not None:
            self.reset_training()
            self.state = "fight"
        elif action == "training_dummy" and self.training is not None:
            self.training.cycle_dummy()
            self.clear_input()
            self.particles.clear()
        elif action == "versus":
            self.notice = "Local versus is currently unavailable."
        elif action == "difficulty":
            index = DIFFICULTIES.index(self.progress.difficulty)
            self.progress.difficulty = DIFFICULTIES[(index + 1) % len(DIFFICULTIES)]
        elif action == "quit":
            if not self.quit_prompt:
                self.quit_prompt = True
                self.quit_previous_focus = self.menu_focus
                self.menu_focus = 0
                self.capture = None
                self.clear_input()
        elif action == "confirm_quit" and self.quit_prompt:
            self.running = False
        elif action == "cancel_quit" and self.quit_prompt:
            self.quit_prompt = False
            self.menu_focus = self.quit_previous_focus
            self.clear_input()
        elif action == "menu":
            self.state, self.menu_focus = "menu", 0
            self.clear_input()
        elif action == "settings":
            self.settings_return = self.state
            self.state, self.menu_focus, self.notice = "settings", 0, ""
            self.clear_input()
        elif action == "moves":
            self.moves_return = self.state
            self.move_character = self.match.fighters[0].character if self.state in ("fight", "pause", "result") else self.selected[0]
            self.state, self.menu_focus, self.move_page = "moves", 0, 0
            self.clear_input()
        elif action.startswith("page:"):
            self.move_page = int(action[-1])
        elif action in ("previous_fighter", "next_fighter"):
            index = CHARACTERS.index(self.move_character)
            self.move_character = CHARACTERS[(index + (1 if action == "next_fighter" else -1)) % len(CHARACTERS)]
        elif action == "moves_back":
            self.state, self.menu_focus = self.moves_return, 0
            self.clear_input()
        elif action == "back":
            self.capture = None
            self.progress.save()
            self.state, self.menu_focus = self.settings_return, 0
            self.clear_input()
        elif action == "resume":
            self.state = "fight"
            self.clear_input()
        elif action == "rematch":
            self.start_match()
        elif action in ("quieter", "louder", "mute"):
            if action == "mute":
                self.muted = not self.muted
            else:
                self.progress.volume = round(max(0, min(1, self.progress.volume + (.1 if action == "louder" else -.1))), 2)
                self.muted = False
            self.progress.muted = self.muted
            self.audio.set_volume(0 if self.muted else self.progress.volume)
        elif action.startswith("bind:"):
            self.capture = action[5:]
            self.notice = "Press a key. Esc cancels. Enter and F1-F4 are reserved."
        elif action in ("reset", "letters", "numpad"):
            self.progress.bindings = dict(NUMPAD_BINDINGS if action == "numpad" else DEFAULT_BINDINGS)
            self.notice = "Numpad preset applied." if action == "numpad" else "Letter preset applied."

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.activate("quit")
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            if self.state == "fight":
                self.state, self.menu_focus = "pause", 0
            elif self.state == "knockout":
                self.knockout_paused = True
            self.clear_input()
            return
        if event.type == pygame.WINDOWFOCUSGAINED:
            self.knockout_paused = False
            return
        if self.quit_prompt:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.activate("cancel_quit")
                elif event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
                    self.menu_focus = (self.menu_focus + 1) % 2
                elif event.key == pygame.K_RETURN:
                    self.activate(self.buttons()[self.menu_focus][2])
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.click_button(event.pos)
            return
        if self.state == "knockout":
            return
        if self.capture:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.capture, self.notice = None, "Key change cancelled."
                elif event.key in RESERVED_KEYS or not pygame.key.name(event.key):
                    self.notice = "That key is reserved. Choose another, or Esc to cancel."
                elif event.key in self.progress.bindings.values() and self.progress.bindings[self.capture] != event.key:
                    self.notice = "That key is already assigned. Choose a free key."
                else:
                    self.progress.bindings[self.capture] = event.key
                    self.capture, self.notice = None, "Control updated."
            return
        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            self.mouse_block = False
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.state == "fight":
                self.state, self.menu_focus = "pause", 0
                self.clear_input()
            elif self.state == "pause":
                self.activate("resume")
            elif self.state == "settings":
                self.activate("back")
            elif self.state == "moves":
                self.activate("moves_back")
            elif self.state == "result":
                self.activate("menu")
            return
        if self.state == "fight":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                self.debug = not self.debug
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F2:
                self.activate("moves")
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F3 and self.mode == "training":
                self.reset_training()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_F4 and self.mode == "training":
                self.activate("training_dummy")
            elif self.countdown <= 0 and event.type in (pygame.KEYDOWN, pygame.KEYUP):
                if event.type == pygame.KEYDOWN:
                    self.event_keys.add(event.key)
                else:
                    self.event_keys.discard(event.key)
                mapping = self.progress.bindings
                if event.key in (mapping["left"], mapping["right"], mapping["down"]):
                    move = int(mapping["right"] in self.event_keys) - int(mapping["left"] in self.event_keys)
                    self.motion_samples.append((move, mapping["down"] in self.event_keys))
                if event.type == pygame.KEYDOWN:
                    for action in ("jump", "jump_alt", "parry", "counter") + NORMALS:
                        if event.key == mapping[action]:
                            if action in NORMALS:
                                if self.pending.attack is None:
                                    self.pending.attack = action
                            elif action == "jump_alt":
                                self.pending.jump = True
                            else:
                                setattr(self.pending, action, True)
            elif self.countdown <= 0 and event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (1, 3) and self.pending.attack is None:
                    self.pending.attack = "lp" if event.button == 1 else "hp"
                elif event.button == 2:
                    self.mouse_block = True
            return
        if event.type == pygame.KEYDOWN:
            if self.state == "menu" and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.cycle_character(1 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 0,
                                     1 if event.key == pygame.K_RIGHT else -1)
                return
            if self.state == "moves" and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.activate("next_fighter" if event.key == pygame.K_RIGHT else "previous_fighter")
                return
            buttons = self.buttons()
            if buttons and event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
                self.menu_focus = (self.menu_focus + (-1 if event.key == pygame.K_UP else 1)) % len(buttons)
            elif buttons and event.key == pygame.K_RETURN:
                self.activate(buttons[self.menu_focus % len(buttons)][2])
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.state == "menu" and event.button in (1, 3):
                for index, name in enumerate(CHARACTERS):
                    if self.card_rect(index).collidepoint(event.pos):
                        if self.progress.unlocked(name):
                            self.selected[0 if event.button == 1 else 1] = name
                        return
            if event.button == 1:
                self.click_button(event.pos)

    def click_button(self, position):
        for index, (rect, _, action) in enumerate(self.buttons()):
            if rect.collidepoint(position):
                self.menu_focus = index
                self.activate(action)
                return

    def update(self, dt, held=None):
        if self.quit_prompt:
            return
        if self.state == "knockout":
            if self.knockout_paused or not math.isfinite(dt) or dt <= 0:
                return
            self.knockout_elapsed = min(KNOCKOUT_DURATION, self.knockout_elapsed + min(dt, .1))
            self.update_particles(min(dt, .1) * .3)
            if self.knockout_elapsed >= KNOCKOUT_DURATION - 1e-9:
                self.state, self.menu_focus = "result", 0
                self.clear_input()
            return
        if self.state != "fight":
            return
        if self.countdown > 0:
            self.countdown = max(0, self.countdown - dt)
            self.clear_input()
            return
        if held is None:
            keys = pygame.key.get_pressed()
            held = {key for key in self.progress.bindings.values() if keys[key]}
        mapping = self.progress.bindings
        player = Controls(move=int(mapping["right"] in held) - int(mapping["left"] in held),
            crouch=mapping["down"] in held, block=mapping["block"] in held or self.mouse_block,
            jump=self.pending.jump, attack=self.pending.attack, parry=self.pending.parry,
            counter=self.pending.counter, motions=tuple(self.motion_samples))
        before = [(fighter.attack, fighter.attack_time) for fighter in self.match.fighters]
        if self.mode == "training":
            hits = self.training.update(dt, player)
        else:
            hits = self.match.update(dt, [player, self.ai.update(self.match, dt)])
        for fighter, previous in zip(self.match.fighters, before):
            if fighter.attack and (fighter.attack != previous[0] or fighter.attack_time < previous[1]):
                self.audio.play(fighter.attack)
        self.pending, self.motion_samples = Controls(), []
        for hit in hits:
            fighter = self.match.fighters[hit.target]
            if hit.blocked or hit.parried or hit.countered:
                self.audio.play("block")
            color = RED if hit.shield_broken else BLUE if hit.parried or hit.blocked else YELLOW
            for _ in range(10):
                self.particles.append(Particle(fighter.x - fighter.facing * 35, FLOOR - fighter.elevation - 70,
                    self.random.uniform(-180, 180), self.random.uniform(-200, 40), .3, color))
        self.update_particles(dt)
        if self.match.over:
            self.finish_match()

    def update_particles(self, dt):
        for particle in self.particles:
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vy += 500 * dt
            particle.life -= dt
        self.particles = [particle for particle in self.particles if particle.life > 0]

    def draw_background(self, dim=170):
        self.screen.blit(self.art.background, (0, 0))
        tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        tint.fill((*INK, dim))
        self.screen.blit(tint, (0, 0))

    def draw_buttons(self, modal=False):
        if self.quit_prompt and not modal:
            return
        mouse = pygame.mouse.get_pos()
        for index, (rect, label, action) in enumerate(self.buttons()):
            selected_page = action == "page:" + str(self.move_page) if self.state == "moves" else False
            focused = rect.collidepoint(mouse) or index == self.menu_focus or selected_page
            color = YELLOW if focused else PANEL
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, YELLOW if focused else (66, 75, 81), rect, 1, border_radius=8)
            self.art.text(self.screen, label, rect.center, 23, INK if focused else CREAM, True)
            if action == "bind:" + str(self.capture):
                pygame.draw.rect(self.screen, BLUE, rect.inflate(4, 4), 2, border_radius=8)

    def draw_logo(self):
        self.art.text(self.screen, "Sean and Miles present", (600, 27), 21, YELLOW, True)
        for x, height in ((365, 15), (501, 13), (789, 17)):
            pygame.draw.rect(self.screen, RED, (x, 90, 6, height), border_radius=3)
        for offset, color in ((5, INK), (2, RED), (0, CREAM)):
            self.art.text(self.screen, "STREET BURGER", (600 + offset, 78 + offset), 71, color, True)
        self.art.text(self.screen, "burger jam", (600, 127), 23, YELLOW, True)

    def draw_menu(self):
        self.draw_background(230)
        self.draw_logo()
        self.art.text(self.screen, "CHOOSE YOUR FIGHTER + CPU", (60, 157), 24)
        self.art.text(self.screen, f"CPU WINS: {self.progress.wins}", (977, 158), 22, YELLOW)
        for index, name in enumerate(CHARACTERS):
            rect = self.card_rect(index)
            unlocked = self.progress.unlocked(name)
            pygame.draw.rect(self.screen, PANEL, rect, border_radius=10)
            chosen = [player for player in range(2) if self.selected[player] == name]
            if chosen:
                pygame.draw.rect(self.screen, YELLOW if 0 in chosen else BLUE, rect, 2, border_radius=10)
                self.art.text(self.screen, " + ".join("YOU" if player == 0 else "CPU" for player in chosen),
                              (rect.centerx, rect.y + 12), 17, YELLOW if 0 in chosen else BLUE, True)
            portrait = self.art.portrait(name, 86)
            if not unlocked:
                portrait.set_alpha(65)
            self.screen.blit(portrait, (rect.centerx - 43, rect.y + 23))
            self.art.text(self.screen, name.upper(), (rect.centerx, rect.y + 116), 21,
                          CREAM if unlocked else MUTED, True)
            text = "READY" if unlocked else f"WIN {UNLOCK_WINS[index]} CPU MATCH" + ("ES" if UNLOCK_WINS[index] != 1 else "")
            self.art.text(self.screen, text, (rect.centerx, rect.y + 137), 16, GREEN if unlocked else MUTED, True)
        self.art.text(self.screen, "Click: you | Right-click: CPU | Left/Right: you | Shift+Left/Right: CPU",
                      (600, 533), 22, MUTED, True)
        self.art.text(self.screen, PROFILES[self.selected[0]].style, (600, 558), 22, YELLOW, True)
        self.draw_buttons()
        self.art.text(self.screen, "LOCAL VERSUS UNAVAILABLE - expanded controls use the keyboard.",
                      (600, 648), 22, MUTED, True)
        difficulty_help = {"easy": "Easy: simple attacks only.", "medium": "Medium: all moves, no combos.",
                           "hard": "Hard: all moves and combos."}[self.progress.difficulty]
        self.art.text(self.screen, self.progress.warning or self.notice or difficulty_help,
                      (600, 678), 21, YELLOW, True)

    def draw_settings(self):
        self.draw_background(235)
        self.art.text(self.screen, "MAKE IT YOURS", (600, 53), 53, CREAM, True)
        self.art.text(self.screen, "Six-button controls | Presets replace bindings | Changes save with your profile.",
                      (600, 99), 23, MUTED, True)
        self.art.text(self.screen, "VOLUME", (135, 144), 26, YELLOW)
        pygame.draw.rect(self.screen, PANEL, (420, 149, 360, 13), border_radius=6)
        pygame.draw.rect(self.screen, YELLOW, (420, 149, int(360 * self.progress.volume), 13), border_radius=6)
        self.art.text(self.screen, "MUTED" if self.muted else f"{round(self.progress.volume * 100)}%",
                      (600, 184), 20, MUTED, True)
        self.art.text(self.screen, "MOVEMENT / DEFENSE", (345, 264), 23, YELLOW, True)
        self.art.text(self.screen, "PUNCHES / KICKS", (855, 264), 23, BLUE, True)
        self.draw_buttons()
        self.art.text(self.screen, self.notice or "Click any action to rebind it. Each action needs a unique key.",
                      (600, 583), 21, BLUE if self.capture else MUTED, True)
        self.art.text(self.screen, self.progress.warning or "Esc: back | Up/Down or Tab: navigate | Enter: select",
                      (600, 678), 20, YELLOW if self.progress.warning else MUTED, True)

    def move_rows(self):
        """Rows used by the move menu, generated from the same specs as combat."""
        character = self.move_character
        if self.move_page == 0:
            return [(move_for(character, name).label, self.key_label(name),
                     str(move_for(character, name).damage), f"{round(move_for(character, name).windup * 1000)} ms",
                     move_for(character, name).level.upper()) for name in NORMALS]
        if self.move_page == 1:
            return [(PROFILES[character].special, "Down > Down+Forward > Forward + Punch",
                     f"Facing right: {self.key_label('down')} > {self.key_label('down')}+{self.key_label('right')} > {self.key_label('right')} + Punch",
                     "special"),
                    (PROFILES[character].technique, "Down > Down+Back > Back + Kick",
                     f"Facing right: {self.key_label('down')} > {self.key_label('down')}+{self.key_label('left')} > {self.key_label('left')} + Kick",
                     "technique")]
        if self.move_page == 2:
            return [(move_for(character, "dive_kick").label, "While airborne: hold Down + any Kick",
                     f"Jump: {self.jump_label()} | {self.key_label('down')} + " + "/".join(self.key_label(name) for name in NORMALS[3:]),
                     "dive_kick"),
                    (move_for(character, "elbow_drop").label, "While airborne: hold Down + any Punch",
                     f"Jump: {self.jump_label()} | {self.key_label('down')} + " + "/".join(self.key_label(name) for name in NORMALS[:3]),
                     "elbow_drop")]
        return [
            ("Punch chain", " > ".join(self.key_label(name) for name in ("lp", "mp", "hp")), "Light Punch > Medium Punch > Heavy Punch"),
            ("Kick chain", " > ".join(self.key_label(name) for name in ("lk", "mk", "hk")), "Light Kick > Medium Kick > Heavy Kick"),
            ("Mixed chain", " > ".join(self.key_label(name) for name in ("lp", "mk", "hp")), "Light Punch > Medium Kick > Heavy Punch"),
            ("Special finish", "Light > Medium > Heavy > quarter-circle special", PROFILES[character].special + " or " + PROFILES[character].technique),
        ]

    def draw_moves(self):
        self.draw_background(240)
        self.art.text(self.screen, "MOVE LIST", (600, 43), 49, CREAM, True)
        self.art.text(self.screen, self.move_character.upper() + " / " + PROFILES[self.move_character].style,
                      (600, 91), 30, YELLOW, True)
        self.art.text(self.screen, "Forward/back follow your opponent. Motions mirror when facing left.",
                      (600, 128), 22, MUTED, True)
        self.draw_buttons()
        if self.move_page == 0:
            columns = (70, 420, 650, 800, 1000)
            for x, label in zip(columns, ("MOVE", "KEY", "DAMAGE", "STARTUP", "HIT")):
                self.art.text(self.screen, label, (x, 218), 21, BLUE)
            for index, row in enumerate(self.move_rows()):
                y = 252 + index * 37
                for x, value in zip(columns, row):
                    self.art.text(self.screen, value, (x, y), 24)
            lines = [
                f"{self.key_label('left')}/{self.key_label('right')}: full-speed move | {self.key_label('down')}: crouch | {self.jump_label()}: jump",
                f"Shield: hold {self.key_label('block')}. Stops all frontal hits. Back only moves; shielding stops movement.",
                f"Shield wears down; release to recover. At zero it breaks, leaving you stunned for {SHIELD_BREAK_TIME:g}s.",
                f"Parry: Forward + Shield within {round(PARRY_INPUT_WINDOW * 1000)} ms of each other (or {self.key_label('parry')}); catch impact within {round(PARRY_TIME * 1000)} ms.",
                f"After parry: any attack or {self.key_label('counter')} within {round(RIPOSTE_WINDOW * 1000)} ms gives a fast {move_for(self.move_character, 'counter').damage}-damage reply.",
                f"Counter stance: {self.key_label('counter')} catches hits for {round(COUNTER_TIME * 1000)} ms and strikes back. Miss: {COUNTER_RECOVERY:g}s total recovery.",
            ]
            for index, line in enumerate(lines):
                self.art.text(self.screen, line, (70, 484 + index * 23), 21, YELLOW if index >= 3 else MUTED)
        elif self.move_page in (1, 2):
            descriptions = {"rush": "Rush forward with an extended punch.", "rising": "A rising strike launches the opponent.",
                            "long": "Long reach to punish opponents at a distance.", "overhead": "A heavy strike with overhead reach.",
                            "sweep": "A long low sweep.", "slide": "Slide forward with a low kick.",
                            "dive_kick": "Drop fast with your leg pointed straight down. Recovers on landing.",
                            "elbow_drop": "Lean into a fast elbow-first drop. Recovers on landing."}
            profile = PROFILES[self.move_character]
            for index, (label, motion, example, name) in enumerate(self.move_rows()):
                y = 224 + index * 170
                spec = move_for(self.move_character, name)
                kind = name if name in DIVES else profile.special_kind if name == "special" else profile.technique_kind
                pygame.draw.rect(self.screen, PANEL, (60, y, 1080, 154), border_radius=9)
                self.art.text(self.screen, label, (80, y + 13), 32, YELLOW)
                self.art.text(self.screen, motion, (80, y + 48), 25)
                self.art.text(self.screen, example, (80, y + 79), 22, BLUE)
                self.art.text(self.screen, descriptions[kind], (80, y + 109), 22, MUTED)
                self.art.text(self.screen, f"{spec.damage} DMG / {spec.level.upper()}", (906, y + 17), 22, CREAM)
            instruction = ("Both dives hit overhead once. Shield, parry or a timed counter can stop them." if self.move_page == 2 else
                           "Finish the motion within 450 ms, then press any punch/kick. Specials require the ground.")
            self.art.text(self.screen, instruction,
                          (60, 583), 22, MUTED)
        else:
            for index, (name, keys, description) in enumerate(self.move_rows()):
                y = 222 + index * 75
                self.art.text(self.screen, name, (70, y), 27, YELLOW)
                self.art.text(self.screen, keys, (340, y), 26)
                self.art.text(self.screen, description, (340, y + 30), 21, MUTED)
            self.art.text(self.screen, "Connect a hit, then press a stronger attack promptly. Misses and blocks cannot cancel.",
                          (70, 536), 22, CREAM)
            self.art.text(self.screen, "Press just before or after impact; a 140 ms input buffer helps. Keep close / hold Forward.",
                          (70, 564), 22, MUTED)
            self.art.text(self.screen, "Hits must connect before the opponent recovers. Combo damage scales down after each hit.",
                          (70, 591), 22, MUTED)

    def draw_arm(self, fighter, floor, rear, surface=None):
        if not rear and fighter.attack == "elbow_drop" and not fighter.dive_landed:
            self.draw_elbow(fighter, floor)
            return
        hand, extension = "idle", 0
        spec = fighter.current_move
        limb = "rear" if rear else "front"
        if fighter.blocking or fighter.parry_time > 0:
            hand = "block"
        elif spec and spec.limb == limb:
            hand = "windup" if fighter.attack_time < spec.windup else "active"
            extension = min(65, max(18, spec.reach - 35)) if fighter.attack_box else 9
        width = 86 if rear else 94
        height = 63 if hand == "block" else 47 if rear else 51
        arm = pygame.transform.scale(self.art.character_arms[fighter.character][hand], (width, height))
        if rear:
            arm.fill((195, 195, 195), special_flags=pygame.BLEND_RGB_MULT)
        if fighter.facing == -1:
            arm = pygame.transform.flip(arm, True, False)
        hand_x = fighter.x + fighter.facing * ((26 if rear else 32) + extension)
        hand_y = floor - (80 if rear else 48) + (35 if fighter.crouching else 0)
        rect = arm.get_rect(midleft=(hand_x, hand_y)) if fighter.facing == 1 else arm.get_rect(midright=(hand_x, hand_y))
        (self.screen if surface is None else surface).blit(arm, rect)

    def make_knockout_pose(self, fighter):
        """Keep both arms attached while rotating the defeated fighter as one sprite."""
        pose = replace(fighter, x=180, attack=None, spec=None, blocking=False, parry_time=0)
        canvas = pygame.Surface((360, 260), pygame.SRCALPHA)
        self.draw_arm(pose, 210, rear=True, surface=canvas)
        body = self.art.portrait(pose.character, 145, pose.facing)
        if pose.crouching:
            body = pygame.transform.scale(body, (156, 90))
        padding = body.get_height() - body.get_bounding_rect().bottom
        canvas.blit(body, body.get_rect(midbottom=(180, 210 + padding)))
        self.draw_arm(pose, 210, rear=False, surface=canvas)
        bounds = canvas.get_bounding_rect()
        return canvas.subsurface(bounds).copy(), bounds.centerx - pose.x

    def draw_knockout_fighter(self, fighter, player):
        progress = min(1, max(0, (self.knockout_elapsed - KNOCKOUT_HITSTOP) / KNOCKOUT_FALL))
        ease = 1 - (1 - progress) ** 3
        direction = -fighter.facing
        angle = -direction * 88 * ease
        sprite, center_offset = self.knockout_poses[player]
        rotated = pygame.transform.rotate(sprite, angle)
        rotated = rotated.subsurface(rotated.get_bounding_rect())
        x = max(LEFT, min(RIGHT, fighter.x + direction * 55 * ease))
        floor = FLOOR - fighter.elevation * (1 - ease) - math.sin(progress * math.pi) * 32
        shadow = pygame.Surface((160, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), (15, 6, 130, 18))
        self.screen.blit(shadow, (x - 80, FLOOR - 11))
        self.screen.blit(rotated, rotated.get_rect(midbottom=(x + center_offset * math.cos(math.radians(angle)), floor)))

    def draw_knockout(self):
        elapsed = self.knockout_elapsed
        if elapsed < .3:
            shake = round(5 * math.sin(elapsed * 110) * (1 - elapsed / .3))
            frame = self.screen.copy()
            self.screen.fill(INK)
            self.screen.blit(frame, (shake, 0))
        if elapsed < KNOCKOUT_HITSTOP:
            flash = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            flash.fill((*CREAM, round(75 * (1 - elapsed / KNOCKOUT_HITSTOP))))
            self.screen.blit(flash, (0, 0))
        else:
            pygame.draw.rect(self.screen, INK, (0, 0, WIDTH, 12))
            pygame.draw.rect(self.screen, INK, (0, HEIGHT - 12, WIDTH, 12))
            title = "DOUBLE K.O." if self.match.winner is None else "K.O."
            caption = "BOTH FIGHTERS ARE DOWN" if self.match.winner is None else (
                self.match.fighters[self.match.winner].character.upper() + " TAKES THE ROUND")
            self.art.text(self.screen, title, (604, 278), 116, INK, True)
            self.art.text(self.screen, title, (600, 272), 116, YELLOW, True)
            self.art.text(self.screen, caption, (600, 344), 27, CREAM, True)
        if self.knockout_paused:
            self.art.text(self.screen, "Return to the game to continue", (600, 400), 27, CREAM, True)

    @staticmethod
    def limb_colors(fighter):
        color = PROFILES[fighter.character].arm_color or (247, 162, 102)
        return tuple(round(value * .57) for value in color), color

    def draw_elbow(self, fighter, floor):
        outline, color = self.limb_colors(fighter)
        shoulder = (fighter.x + fighter.facing * 20, floor - 70)
        elbow = (fighter.x + fighter.facing * 33, floor + 20)
        fist = (fighter.x + fighter.facing * 62, floor - 40)
        pygame.draw.lines(self.screen, outline, False, (shoulder, elbow, fist), 20)
        pygame.draw.lines(self.screen, color, False, (shoulder, elbow, fist), 12)
        pygame.draw.circle(self.screen, color, (round(elbow[0]), round(elbow[1])), 9)

    def draw_kick(self, fighter, floor):
        spec = fighter.current_move
        if not spec or spec.limb != "kick":
            return
        outline, color = self.limb_colors(fighter)
        if fighter.attack == "dive_kick" and not fighter.dive_landed:
            points = ((fighter.x + fighter.facing * 10, floor - 28),
                      (fighter.x + fighter.facing * 16, floor + 22),
                      (fighter.x + fighter.facing * 18, floor + 70))
            pygame.draw.lines(self.screen, outline, False, points, 19)
            pygame.draw.lines(self.screen, color, False, points, 12)
            pygame.draw.rect(self.screen, color, (points[-1][0] - 10, points[-1][1] - 3, 20, 9), border_radius=3)
            return
        amount = 1 if fighter.attack_box else .35
        height = 20 if spec.level == "low" else 88 if spec.level == "overhead" else 61
        start = (fighter.x + fighter.facing * 17, floor - 23)
        knee = (fighter.x + fighter.facing * (45 + 25 * amount), floor - height * .6)
        toe = (fighter.x + fighter.facing * (32 + spec.reach * amount), floor - height)
        pygame.draw.lines(self.screen, outline, False, (start, knee, toe), 19)
        pygame.draw.lines(self.screen, color, False, (start, knee, toe), 12)
        pygame.draw.circle(self.screen, CREAM, (round(toe[0]), round(toe[1])), 8)

    def draw_fighter(self, fighter, player):
        if (self.state in ("knockout", "result") and self.knockout_poses
                and self.knockout_elapsed > KNOCKOUT_HITSTOP):
            if player in self.knockout_poses:
                self.draw_knockout_fighter(fighter, player)
                return
            # Let the winner finish the swing and settle from an airborne final hit.
            elapsed = self.knockout_elapsed - KNOCKOUT_HITSTOP
            fighter = replace(fighter, elevation=fighter.elevation * max(0, 1 - elapsed / .5),
                              flash=max(0, fighter.flash - elapsed), recoil=max(0, fighter.recoil - elapsed * 5),
                              announcement_time=max(0, fighter.announcement_time - elapsed))
            if fighter.current_move:
                fighter.attack_time += elapsed * .7
                if fighter.attack_time >= fighter.current_move.duration:
                    fighter.attack, fighter.spec = None, None
        dummy = self.mode == "training" and player == 1
        floor = FLOOR - fighter.elevation
        shadow_width = max(35, 125 - fighter.elevation * .25)
        shadow = pygame.Surface((160, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), (80 - shadow_width / 2, 6, shadow_width, 18))
        self.screen.blit(shadow, (fighter.x - 80, FLOOR - 11))
        if not dummy:
            self.draw_arm(fighter, floor, rear=True)
        if dummy:
            portrait = pygame.transform.scale(self.art.dummy, (145, 145))
            if fighter.facing == -1:
                portrait = pygame.transform.flip(portrait, True, False)
        else:
            portrait = self.art.portrait(fighter.character, 145, fighter.facing)
        if fighter.crouching:
            portrait = pygame.transform.scale(portrait, (156, 90))
        if fighter.flash > 0:
            portrait.fill((40, 65, 70) if fighter.guard_hit else (65, 30, 10), special_flags=pygame.BLEND_RGB_ADD)
        rotation = -fighter.facing * fighter.recoil * 12
        if fighter.attack == "elbow_drop" and not fighter.dive_landed:
            rotation -= fighter.facing * 22
        if rotation:
            portrait = pygame.transform.rotate(portrait, rotation)
        padding = portrait.get_height() - portrait.get_bounding_rect().bottom
        self.screen.blit(portrait, portrait.get_rect(midbottom=(fighter.x, floor + padding)))
        self.draw_kick(fighter, floor)
        if not dummy:
            self.draw_arm(fighter, floor, rear=False)
        if fighter.blocking:
            fraction = fighter.shield / SHIELD_MAX
            color = RED if fraction < .3 else BLUE
            radius = round(57 + fraction * 28)
            bubble = pygame.Surface((180, 190), pygame.SRCALPHA)
            pygame.draw.circle(bubble, (*color, 35), (90, 95), radius)
            pygame.draw.circle(bubble, (*color, 210), (90, 95), radius, 4)
            self.screen.blit(bubble, (fighter.x - 90, floor - 170))
        if fighter.parry_time > 0:
            pygame.draw.circle(self.screen, CREAM, (round(fighter.x), round(floor - 72)), 87, 5)
        if fighter.counter_time > 0:
            pygame.draw.circle(self.screen, YELLOW, (round(fighter.x), round(floor - 72)), 87, 5)
        if fighter.shield_break > 0:
            for offset in range(3):
                angle = fighter.clock * 4 + offset * math.tau / 3
                pygame.draw.circle(self.screen, YELLOW,
                    (round(fighter.x + math.cos(angle) * 35), round(floor - 155 + math.sin(angle) * 10)), 6)
        self.art.text(self.screen, "YOU" if player == 0 else "DUMMY" if dummy else "CPU", (fighter.x, floor - 164),
                      22, YELLOW if player == 0 else BLUE, True)
        if fighter.announcement_time > 0:
            self.art.text(self.screen, fighter.announcement, (fighter.x, floor - 198), 24, BLUE, True)
        if fighter.counter_window > 0:
            self.art.text(self.screen, "COUNTER READY" if player else "ATTACK TO COUNTER",
                          (fighter.x, floor - 225), 22, YELLOW, True)
        if self.debug:
            for box, color in ((fighter.body, GREEN), (fighter.attack_box, RED)):
                if box:
                    pygame.draw.rect(self.screen, color, (box.x, box.y, box.width, box.height), 2)

    def draw_arena(self):
        if self.mode == "training":
            self.screen.blit(self.art.kitchen, (0, 0))
        else:
            self.draw_background(105)
            pygame.draw.rect(self.screen, INK, (0, FLOOR, WIDTH, HEIGHT - FLOOR))
            for x in range(-100, WIDTH + 100, 100):
                pygame.draw.line(self.screen, (44, 49, 53), (600 + (x - 600) * .8, FLOOR + 3), (x, HEIGHT), 1)
            for y in (625, 660, 699):
                pygame.draw.line(self.screen, (44, 49, 53), (0, y), (WIDTH, y), 1)
        pygame.draw.line(self.screen, YELLOW, (0, FLOOR), (WIDTH, FLOOR), 3)
        for index, fighter in enumerate(self.match.fighters):
            x = 48 if index == 0 else 704
            color = YELLOW if index == 0 else BLUE
            pygame.draw.rect(self.screen, INK, (x - 12, 24, 472, 113), border_radius=10)
            label = "YOU" if index == 0 else "PRACTICE DUMMY" if self.mode == "training" else "CPU / " + self.ai.difficulty.upper()
            damage_meter = index == 1 and self.mode == "training"
            name = "TOTAL DAMAGE" if damage_meter else fighter.character.upper()
            self.art.text(self.screen, label, (x, 35), 22, color)
            self.art.text(self.screen, name, (x, 61), 26)
            if damage_meter:
                total = self.training.total_damage
                capacity = max(100, math.ceil(total / 100) * 100)
                value, fraction = total, total / capacity
                background = (44, 61, 66)
            else:
                value, fraction, background = fighter.health, fighter.health / 100, (94, 43, 43)
            pygame.draw.rect(self.screen, background, (x, 94, 448, 13), border_radius=6)
            if fraction:
                pygame.draw.rect(self.screen, color, (x, 94, round(448 * fraction), 13), border_radius=6)
            self.art.text(self.screen, value, (x + 448, 62), 25, color, right=True)
            shield_color = RED if fighter.shield_break > 0 or fighter.shield < 30 else BLUE
            shield_text = "SHIELD BROKEN" if fighter.shield_break > 0 else f"SHIELD {math.ceil(fighter.shield)}"
            self.art.text(self.screen, shield_text, (x, 113), 17, shield_color)
            pygame.draw.rect(self.screen, (44, 61, 66), (x + 138, 119, 310, 7), border_radius=3)
            if fighter.shield > 0:
                pygame.draw.rect(self.screen, shield_color, (x + 138, 119, round(310 * fighter.shield / SHIELD_MAX), 7), border_radius=3)
            if fighter.combo_hits >= 2 and self.mode != "training":
                self.art.text(self.screen, f"{fighter.combo_hits} HIT COMBO / {fighter.combo_damage} DAMAGE",
                              (x, 150), 26, color)
        if self.mode == "training":
            self.art.text(self.screen, "GRILL", (600, 68), 44, CREAM, True)
            self.art.text(self.screen, "TRAINING", (600, 105), 18, YELLOW, True)
            self.draw_training_hud()
        else:
            self.art.text(self.screen, math.ceil(self.match.remaining), (600, 68), 65, CREAM, True)
            self.art.text(self.screen, "SECONDS", (600, 105), 18, MUTED, True)
        for index, fighter in enumerate(self.match.fighters):
            self.draw_fighter(fighter, index)
        for particle in self.particles:
            pygame.draw.circle(self.screen, particle.color, (round(particle.x), round(particle.y)),
                               max(1, round(particle.life * 13)))
        self.art.text(self.screen, f"{self.key_label('left')}/{self.key_label('right')} move | {self.key_label('down')} crouch | {self.jump_label()} jump",
                      (28, 637), 21, YELLOW)
        self.art.text(self.screen, "P: " + "/".join(self.key_label(key) for key in NORMALS[:3]) +
                      " | K: " + "/".join(self.key_label(key) for key in NORMALS[3:]), (460, 637), 21, CREAM)
        self.art.text(self.screen, f"{self.key_label('block')} shield | {self.key_label('parry')} parry | {self.key_label('counter')} counter",
                      (835, 637), 21, BLUE)
        hint = "Esc: pause | F1: hitboxes | F2: moves and combos"
        if self.mode == "training":
            hint += " | F3: reset | F4: dummy guard"
        if self.state == "knockout":
            hint = "KNOCKOUT / ROUND COMPLETE"
        self.art.text(self.screen, hint, (600, 678), 21, MUTED, True)
        if self.countdown > 0:
            self.art.text(self.screen, "ORDER UP!", (600, 285), 74, YELLOW, True)
            self.art.text(self.screen, math.ceil(self.countdown), (600, 361), 76, CREAM, True)

    def draw_training_hud(self):
        session = self.training
        pygame.draw.rect(self.screen, PANEL, (48, 144, 1104, 76), border_radius=9)
        last_unit = "HIT" if session.last_hits == 1 else "HITS"
        best_unit = "HIT" if session.best_hits == 1 else "HITS"
        self.art.text(self.screen, f"LAST: {session.last_hits} {last_unit} / {session.last_damage} DAMAGE", (66, 158), 26, YELLOW)
        self.art.text(self.screen, f"LAST HIT: {session.last_hit_damage} DAMAGE", (66, 190), 21, MUTED)
        self.art.text(self.screen, "GO TO THE GRILL", (600, 168), 27, CREAM, True)
        self.art.text(self.screen, "F3: RESET POSITIONS / NO TIME LIMIT", (600, 198), 18, MUTED, True)
        self.art.text(self.screen, f"BEST: {session.best_hits} {best_unit} / {session.best_damage} DAMAGE", (794, 158), 25, BLUE)
        self.art.text(self.screen, "DUMMY: " + session.dummy_mode.upper(), (794, 190), 21, MUTED)

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "settings":
            self.draw_settings()
        elif self.state == "moves":
            self.draw_moves()
        else:
            self.draw_arena()
            if self.state == "knockout":
                self.draw_knockout()
            if self.state in ("pause", "result"):
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((*INK, 200))
                self.screen.blit(overlay, (0, 0))
                pygame.draw.rect(self.screen, PANEL, (330, 189, 540, 390), border_radius=16)
                self.art.text(self.screen, "ON THE BACK BURNER" if self.state == "pause" else self.result,
                              (600, 247), 44, YELLOW, True)
                self.art.text(self.screen, "PAUSED" if self.state == "pause" else self.match.reason + " / NEXT ORDER?",
                              (600, 293), 27, MUTED, True)
                self.draw_buttons()
                if self.unlocked and self.state == "result":
                    self.art.text(self.screen, "NEW FIGHTER: " + ", ".join(self.unlocked).upper(),
                                  (600, 607), 30, YELLOW, True)
                if self.progress.warning:
                    self.art.text(self.screen, self.progress.warning, (600, 650), 22, YELLOW, True)
        if self.quit_prompt:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((*INK, 210))
            self.screen.blit(overlay, (0, 0))
            pygame.draw.rect(self.screen, PANEL, (350, 235, 500, 235), border_radius=16)
            self.art.text(self.screen, "Are you sure?", (600, 286), 48, YELLOW, True)
            self.art.text(self.screen, "Quit Street Burger?", (600, 334), 27, CREAM, True)
            self.draw_buttons(modal=True)
            self.art.text(self.screen, "Esc: cancel | Arrows: choose | Enter: select",
                          (600, 449), 21, MUTED, True)

    def run(self):
        try:
            while self.running:
                dt = min(self.clock.tick(60) / 1000, .1)
                for event in pygame.event.get():
                    self.handle_event(event)
                if not self.running:
                    break
                self.update(dt)
                self.draw()
                pygame.display.flip()
        finally:
            self.progress.save()
            pygame.quit()
