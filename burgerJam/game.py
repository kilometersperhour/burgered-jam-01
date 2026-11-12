"""Pygame presentation, menus, input and audio for Street Burger."""

from dataclasses import dataclass
import math
from pathlib import Path
import random

import pygame

from .combat import ATTACKS, FLOOR, HEIGHT, WIDTH, Controls, Fighter, Match, OpponentAI
from .progress import CHARACTERS, UNLOCK_WINS, Progress

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
    "p1_left": pygame.K_a, "p1_right": pygame.K_d, "p1_jump": pygame.K_w,
    "p1_jab": pygame.K_f, "p1_cross": pygame.K_g, "p1_block": pygame.K_s,
    "p2_left": pygame.K_LEFT, "p2_right": pygame.K_RIGHT, "p2_jump": pygame.K_UP,
    "p2_jab": pygame.K_j, "p2_cross": pygame.K_k, "p2_block": pygame.K_DOWN,
}
RESERVED_KEYS = {pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_F1}
ACTIONS = ("left", "right", "jump", "jab", "cross", "block")


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
        self.fonts = {}

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
        else:
            pygame.draw.polygon(body, (234, 158, 58), [(4, 15), (96, 15), (50, 98)])
            pygame.draw.polygon(body, (255, 213, 91), [(12, 23), (87, 23), (50, 88)])
            pygame.draw.line(body, (183, 99, 47), (10, 14), (91, 14), 15)
            pygame.draw.line(body, (241, 183, 91), (10, 10), (91, 10), 8)
            for pos in ((30, 31), (69, 34), (48, 67)):
                pygame.draw.circle(body, (195, 59, 44), pos, 9)
                pygame.draw.circle(body, (231, 94, 58), (pos[0] - 2, pos[1] - 2), 4)
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

    def text(self, target, words, pos, size=24, color=CREAM, center=False):
        if size not in self.fonts:
            self.fonts[size] = pygame.font.Font(None, size)
        surface = self.fonts[size].render(str(words), True, color)
        rect = surface.get_rect(center=pos) if center else surface.get_rect(topleft=pos)
        target.blit(surface, rect)
        return rect

    def portrait(self, name, size=145, facing=1):
        body = self.bodies[name].copy()
        eye_y = 47 if name == "Italian Scallion" else 39 if name == "French Fries" else 32
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
        pygame.display.set_caption("Street Burger | Next Order")
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
        self.running = True
        self.quit_prompt = False
        self.quit_previous_focus = 0
        self.mode = "cpu"
        self.selected = ["Burger", "Tomato"]
        self.match = Match()
        self.ai = OpponentAI(seed)
        self.countdown = 0
        self.pending = [Controls(), Controls()]
        self.mouse_block = False
        self.debug = False
        self.menu_focus = 0
        self.capture = None
        self.notice = ""
        self.result = ""
        self.unlocked = []
        self.particles = []

    def start_match(self, mode):
        self.mode = mode
        self.match = Match([Fighter(330, 1, self.selected[0]), Fighter(870, -1, self.selected[1])])
        self.ai = OpponentAI(self.random.randrange(2 ** 32))
        self.state = "fight"
        self.countdown = 2.4
        self.clear_input()
        self.particles.clear()
        self.unlocked = []

    def clear_input(self):
        self.pending = [Controls(), Controls()]
        self.mouse_block = False

    def finish_match(self):
        if self.state != "fight":
            return
        winner = self.match.winner
        self.result = "DRAW!" if winner is None else ("YOU WIN!" if self.mode == "cpu" and winner == 0
                      else "THE HOUSE WINS" if self.mode == "cpu" else f"PLAYER {winner + 1} WINS!")
        if self.mode == "cpu" and winner == 0:
            before = {name for name in CHARACTERS if self.progress.unlocked(name)}
            self.progress.wins += 1
            self.unlocked = [name for name in CHARACTERS if self.progress.unlocked(name) and name not in before]
            self.progress.save()
        self.state = "result"
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
            return [(pygame.Rect(x, 516, w, 52), label, action) for x, w, label, action in (
                (60, 280, "FIGHT THE CPU", "cpu"), (356, 280, "LOCAL VERSUS", "versus"),
                (652, 242, "SETTINGS / KEYS", "settings"), (910, 230, "QUIT", "quit"))]
        if self.state == "settings":
            result = [(pygame.Rect(340, 156, 52, 42), "-", "quieter"),
                      (pygame.Rect(808, 156, 52, 42), "+", "louder"),
                      (pygame.Rect(900, 156, 160, 42), "UNMUTE" if self.muted else "MUTE", "mute")]
            for player in range(2):
                for row, action in enumerate(ACTIONS):
                    name = f"p{player + 1}_{action}"
                    key = pygame.key.name(self.progress.bindings[name]).upper()
                    result.append((pygame.Rect(150 + player * 470, 282 + row * 44, 430, 36),
                                   f"{action.upper():<7}   [ {key} ]", "bind:" + name))
            result += [(pygame.Rect(340, 587, 250, 48), "RESTORE KEYS", "reset"),
                       (pygame.Rect(610, 587, 250, 48), "BACK", "back")]
            return result
        if self.state in ("pause", "result"):
            first = ("RESUME", "resume") if self.state == "pause" else ("REMATCH", "rematch")
            middle = ("SETTINGS", "settings") if self.state == "pause" else ("CHARACTERS", "menu")
            last = ("MAIN MENU", "menu") if self.state == "pause" else ("QUIT", "quit")
            return [(pygame.Rect(410, 350 + i * 64, 380, 48), label, action)
                    for i, (label, action) in enumerate((first, middle, last))]
        return []

    def activate(self, action):
        if action in ("cpu", "versus"):
            self.start_match(action)
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
            self.state = "menu"
            self.menu_focus = 0
            self.clear_input()
        elif action == "settings":
            self.settings_return = self.state
            self.state = "settings"
            self.notice = ""
            self.menu_focus = 0
        elif action == "back":
            self.capture = None
            self.progress.save()
            self.state = self.settings_return
            self.menu_focus = 0
        elif action == "resume":
            self.state = "fight"
            self.clear_input()
        elif action == "rematch":
            self.start_match(self.mode)
        elif action in ("quieter", "louder", "mute"):
            if action == "mute":
                self.muted = not self.muted
            else:
                self.progress.volume = round(max(0, min(1, self.progress.volume
                                                     + (.1 if action == "louder" else -.1))), 2)
                self.muted = False
            self.progress.muted = self.muted
            self.audio.set_volume(0 if self.muted else self.progress.volume)
        elif action.startswith("bind:"):
            self.capture = action[5:]
            self.notice = "Press a key. Esc cancels. Enter and F1 are reserved."
        elif action == "reset":
            self.progress.bindings = dict(DEFAULT_BINDINGS)
            self.notice = "Default controls restored."

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.activate("quit")
            return
        if event.type == pygame.WINDOWFOCUSLOST:
            if self.state == "fight":
                self.state = "pause"
                self.menu_focus = 0
            self.clear_input()
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
        if event.type == pygame.MOUSEBUTTONUP and event.button == 2:
            self.mouse_block = False
        if self.capture and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.capture = None
                self.notice = "Key change cancelled."
            elif event.key in RESERVED_KEYS or not pygame.key.name(event.key):
                self.notice = "That key is reserved. Choose another, or Esc to cancel."
            elif event.key in self.progress.bindings.values() and self.progress.bindings[self.capture] != event.key:
                self.notice = "That key is already assigned. Choose a free key."
            else:
                self.progress.bindings[self.capture] = event.key
                self.capture = None
                self.notice = "Control updated."
            return
        if self.capture:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if self.state == "fight":
                    self.state = "pause"
                    self.menu_focus = 0
                    self.clear_input()
                elif self.state == "pause":
                    self.activate("resume")
                elif self.state == "settings":
                    self.activate("back")
                elif self.state == "result":
                    self.activate("menu")
                return
            if self.state == "fight":
                if event.key == pygame.K_F1:
                    self.debug = not self.debug
                if self.countdown <= 0:
                    for player in range(1 if self.mode == "cpu" else 2):
                        for action in ("jump", "jab", "cross"):
                            if event.key == self.progress.bindings[f"p{player + 1}_{action}"]:
                                if action == "jump":
                                    self.pending[player].jump = True
                                elif self.pending[player].attack is None:
                                    self.pending[player].attack = action
                return
            if self.state == "menu" and event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                self.cycle_character(1 if getattr(event, "mod", 0) & pygame.KMOD_SHIFT else 0,
                                     1 if event.key == pygame.K_RIGHT else -1)
                return
            buttons = self.buttons()
            if buttons and event.key in (pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
                direction = -1 if event.key == pygame.K_UP else 1
                self.menu_focus = (self.menu_focus + direction) % len(buttons)
            elif buttons and event.key == pygame.K_RETURN:
                self.activate(buttons[self.menu_focus % len(buttons)][2])
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if self.state == "fight" and self.countdown <= 0 and self.mode == "cpu":
                if event.button in (1, 3) and self.pending[0].attack is None:
                    self.pending[0].attack = "jab" if event.button == 1 else "cross"
                elif event.button == 2:
                    self.mouse_block = True
            elif self.state == "menu" and event.button in (1, 3):
                for i, name in enumerate(CHARACTERS):
                    if pygame.Rect(60 + i * 218, 264, 200, 204).collidepoint(event.pos):
                        if self.progress.unlocked(name):
                            self.selected[0 if event.button == 1 else 1] = name
                        return
                if event.button == 1:
                    self.click_button(event.pos)
            elif event.button == 1:
                self.click_button(event.pos)

    def click_button(self, position):
        for i, (rect, _, action) in enumerate(self.buttons()):
            if rect.collidepoint(position):
                self.menu_focus = i
                self.activate(action)
                return

    def update(self, dt, held=None):
        if self.quit_prompt or self.state != "fight":
            return
        if self.countdown > 0:
            self.countdown = max(0, self.countdown - dt)
            self.clear_input()
            return
        if held is None:
            keys = pygame.key.get_pressed()
            held = {key for key in self.progress.bindings.values() if keys[key]}
        controls = []
        for i in range(2):
            mapping = self.progress.bindings
            prefix = f"p{i + 1}_"
            controls.append(Controls(
                move=int(mapping[prefix + "right"] in held) - int(mapping[prefix + "left"] in held),
                block=mapping[prefix + "block"] in held or (i == 0 and self.mouse_block),
                jump=self.pending[i].jump, attack=self.pending[i].attack))
        if self.mode == "cpu":
            controls[1] = self.ai.update(self.match, dt)
        for fighter, control in zip(self.match.fighters, controls):
            if (control.attack and fighter.attack is None and fighter.stun <= 0
                    and not control.block):
                self.audio.play(control.attack)
        hits = self.match.update(dt, controls)
        self.pending = [Controls(), Controls()]
        for hit in hits:
            fighter = self.match.fighters[hit.target]
            if hit.blocked:
                self.audio.play("block")
            for _ in range(10):
                self.particles.append(Particle(fighter.x - fighter.facing * 35,
                    FLOOR - fighter.elevation - 70, self.random.uniform(-180, 180),
                    self.random.uniform(-200, 40), .3, BLUE if hit.blocked else YELLOW))
        for particle in self.particles:
            particle.x += particle.vx * dt
            particle.y += particle.vy * dt
            particle.vy += 500 * dt
            particle.life -= dt
        self.particles = [particle for particle in self.particles if particle.life > 0]
        if self.match.over:
            self.finish_match()

    def draw_background(self, dim=170):
        self.screen.blit(self.art.background, (0, 0))
        tint = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        tint.fill((*INK, dim))
        self.screen.blit(tint, (0, 0))

    def draw_buttons(self, modal=False):
        if self.quit_prompt and not modal:
            return
        mouse = pygame.mouse.get_pos()
        for i, (rect, label, action) in enumerate(self.buttons()):
            focused = rect.collidepoint(mouse) or i == self.menu_focus
            color = YELLOW if focused else PANEL
            pygame.draw.rect(self.screen, color, rect, border_radius=8)
            pygame.draw.rect(self.screen, YELLOW if focused else (66, 75, 81), rect, 1, border_radius=8)
            self.art.text(self.screen, label, rect.center, 25, INK if focused else CREAM, True)
            if action == "bind:" + str(self.capture):
                pygame.draw.rect(self.screen, BLUE, rect.inflate(4, 4), 2, border_radius=8)

    def draw_logo(self):
        self.art.text(self.screen, "Sean and Miles present", (600, 61), 22, YELLOW, True)
        for x, height in ((298, 25), (461, 15), (761, 22), (890, 32)):
            pygame.draw.rect(self.screen, RED, (x, 137, 7, height), border_radius=3)
        for offset, color in ((6, INK), (3, RED), (0, CREAM)):
            self.art.text(self.screen, "STREET BURGER", (600 + offset, 120 + offset), 92, color, True)
        self.art.text(self.screen, "burger jam", (600, 190), 26, YELLOW, True)

    def draw_menu(self):
        self.draw_background(226)
        self.draw_logo()
        self.art.text(self.screen, "CHOOSE YOUR FIGHTERS", (60, 232), 27)
        self.art.text(self.screen, f"CPU WINS: {self.progress.wins}", (982, 236), 23, YELLOW)
        for i, name in enumerate(CHARACTERS):
            rect = pygame.Rect(60 + i * 218, 264, 200, 204)
            unlocked = self.progress.unlocked(name)
            pygame.draw.rect(self.screen, PANEL, rect, border_radius=10)
            chosen = [p for p in range(2) if self.selected[p] == name]
            if chosen:
                pygame.draw.rect(self.screen, YELLOW if 0 in chosen else BLUE, rect, 2, border_radius=10)
                self.art.text(self.screen, " + ".join(f"P{p + 1}" for p in chosen),
                              (rect.centerx, rect.y + 20), 22, YELLOW if 0 in chosen else BLUE, True)
            portrait = self.art.portrait(name, 116)
            if not unlocked:
                portrait.set_alpha(65)
            self.screen.blit(portrait, (rect.centerx - 58, rect.y + 36))
            self.art.text(self.screen, name.upper(), (rect.centerx, rect.y + 164), 22,
                          CREAM if unlocked else MUTED, True)
            sub = "READY TO RUMBLE" if unlocked else f"WIN {UNLOCK_WINS[i]} CPU MATCH" + ("ES" if UNLOCK_WINS[i] != 1 else "")
            self.art.text(self.screen, sub, (rect.centerx, rect.y + 188), 17,
                          GREEN if unlocked else MUTED, True)
        self.art.text(self.screen, "Click: P1 | Right-click: P2 | Left/Right: P1 | Shift+Left/Right: P2",
                      (600, 490), 22, MUTED, True)
        self.draw_buttons()
        self.art.text(self.screen, "Jab fast. Cross hard. Hold your guard. Win a CPU match to unlock the next course.",
                      (600, 604), 24, CREAM, True)
        self.art.text(self.screen, "Up/Down: choose an option | Enter: select | Settings: controls and volume",
                      (600, 637), 22, MUTED, True)
        if self.progress.warning:
            self.art.text(self.screen, self.progress.warning, (600, 674), 21, YELLOW, True)

    def draw_settings(self):
        self.draw_background(235)
        self.art.text(self.screen, "MAKE IT YOURS", (600, 67), 60, CREAM, True)
        self.art.text(self.screen, "Volume and controls are saved with your progress.", (600, 115), 24, MUTED, True)
        self.art.text(self.screen, "VOLUME", (153, 166), 27, YELLOW)
        pygame.draw.rect(self.screen, PANEL, (420, 170, 360, 14), border_radius=7)
        pygame.draw.rect(self.screen, YELLOW, (420, 170, int(360 * self.progress.volume), 14), border_radius=7)
        self.art.text(self.screen, "MUTED" if self.muted else f"{round(self.progress.volume * 100)}%",
                      (600, 211), 22, MUTED, True)
        for i in range(2):
            self.art.text(self.screen, f"PLAYER {i + 1}", (365 + 470 * i, 251), 28,
                          YELLOW if i == 0 else BLUE, True)
        self.draw_buttons()
        self.art.text(self.screen, self.notice or "Select an action, then press its new key. Each action needs a unique key.",
                      (600, 563), 23, BLUE if self.capture else MUTED, True)
        self.art.text(self.screen, self.progress.warning or "Esc: back | Up/Down or Tab: navigate | Enter: select",
                      (600, 671), 21, YELLOW if self.progress.warning else MUTED, True)

    def draw_arm(self, fighter, floor, rear):
        hand = "idle"
        extension = 0
        if fighter.blocking:
            hand = "block"
        elif fighter.attack == ("jab" if rear else "cross"):
            spec = ATTACKS[fighter.attack]
            hand = "windup" if fighter.attack_time < spec.windup else "active"
            extension = 33 if fighter.attack_box else 9
        width = 86 if rear else 94
        height = 63 if hand == "block" else 47 if rear else 51
        arm = pygame.transform.scale(self.art.arms[hand], (width, height))
        if rear:
            arm.fill((195, 195, 195), special_flags=pygame.BLEND_RGB_MULT)
        if fighter.facing == -1:
            arm = pygame.transform.flip(arm, True, False)
        shoulder = 26 if rear else 32
        hand_x = fighter.x + fighter.facing * (shoulder + extension)
        hand_y = floor - (80 if rear else 48)
        rect = (arm.get_rect(midleft=(hand_x, hand_y)) if fighter.facing == 1
                else arm.get_rect(midright=(hand_x, hand_y)))
        self.screen.blit(arm, rect)

    def draw_fighter(self, fighter, player):
        floor = FLOOR - fighter.elevation
        shadow_width = max(35, 125 - fighter.elevation * .25)
        shadow = pygame.Surface((160, 30), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100), (80 - shadow_width / 2, 6, shadow_width, 18))
        self.screen.blit(shadow, (fighter.x - 80, FLOOR - 11))
        self.draw_arm(fighter, floor, rear=True)
        portrait = self.art.portrait(fighter.character, 145, fighter.facing)
        if fighter.flash > 0:
            portrait.fill((40, 65, 70) if fighter.guard_hit else (65, 30, 10), special_flags=pygame.BLEND_RGB_ADD)
        if fighter.recoil > 0:
            portrait = pygame.transform.rotate(portrait, -fighter.facing * fighter.recoil * 12)
        # Original sprites have transparent padding below their feet.
        padding = portrait.get_height() - portrait.get_bounding_rect().bottom
        self.screen.blit(portrait, portrait.get_rect(midbottom=(fighter.x, floor + padding)))
        self.draw_arm(fighter, floor, rear=False)
        if fighter.blocking:
            pygame.draw.arc(self.screen, BLUE, (fighter.x - 78, floor - 147, 156, 150),
                            -1.2 if fighter.facing == 1 else 1.9,
                            1.2 if fighter.facing == 1 else 4.3, 4)
        self.art.text(self.screen, f"P{player + 1}" if player == 0 or self.mode == "versus" else "CPU",
                      (fighter.x, floor - 164), 22, YELLOW if player == 0 else BLUE, True)
        if self.debug:
            box = fighter.body
            pygame.draw.rect(self.screen, GREEN, (box.x, box.y, box.width, box.height), 1)
            box = fighter.attack_box
            if box:
                pygame.draw.rect(self.screen, RED, (box.x, box.y, box.width, box.height), 2)

    def controls_label(self, player):
        prefix = f"p{player + 1}_"
        keys = [pygame.key.name(self.progress.bindings[prefix + action]).upper() for action in ACTIONS]
        return f"{'/'.join(keys[:2])} move  {keys[2]} jump  {keys[3]}/{keys[4]} punch  {keys[5]} guard"

    def draw_arena(self):
        self.draw_background(105)
        pygame.draw.rect(self.screen, INK, (0, FLOOR, WIDTH, HEIGHT - FLOOR))
        pygame.draw.line(self.screen, YELLOW, (0, FLOOR), (WIDTH, FLOOR), 3)
        for x in range(-100, WIDTH + 100, 100):
            pygame.draw.line(self.screen, (44, 49, 53), (600 + (x - 600) * .8, FLOOR + 3), (x, HEIGHT), 1)
        for y in (625, 660, 699):
            pygame.draw.line(self.screen, (44, 49, 53), (0, y), (WIDTH, y), 1)
        for i, fighter in enumerate(self.match.fighters):
            x = 48 if i == 0 else 704
            color = YELLOW if i == 0 else BLUE
            label = "PLAYER 1" if i == 0 else "PLAYER 2" if self.mode == "versus" else "THE HOUSE"
            pygame.draw.rect(self.screen, INK, (x - 12, 24, 472, 99), border_radius=10)
            self.art.text(self.screen, label, (x, 35), 22, color)
            self.art.text(self.screen, fighter.character.upper(), (x, 61), 26)
            pygame.draw.rect(self.screen, (94, 43, 43), (x, 94, 448, 13), border_radius=6)
            health_width = round(448 * fighter.health / 100)
            if health_width > 0:
                pygame.draw.rect(self.screen, color, (x, 94, health_width, 13), border_radius=6)
            self.art.text(self.screen, str(fighter.health), (x + 418, 62), 25, color)
        self.art.text(self.screen, math.ceil(self.match.remaining), (600, 68), 65, CREAM, True)
        self.art.text(self.screen, "SECONDS", (600, 105), 18, MUTED, True)
        self.art.text(self.screen, "BURGARENA / NEXT ORDER", (600, 173), 22, CREAM, True)
        for i, fighter in enumerate(self.match.fighters):
            self.draw_fighter(fighter, i)
        for particle in self.particles:
            pygame.draw.circle(self.screen, particle.color, (round(particle.x), round(particle.y)),
                               max(1, round(particle.life * 13)))
        self.art.text(self.screen, "P1: " + self.controls_label(0), (28, 641), 21, YELLOW)
        right = "P2: " + self.controls_label(1) if self.mode == "versus" else "Mouse: left/right punch | Hold middle: guard"
        self.art.text(self.screen, right, (650, 641), 21, BLUE)
        self.art.text(self.screen, "Esc: pause | F1: hitboxes", (600, 678), 21, MUTED, True)
        if self.countdown > 0:
            self.art.text(self.screen, "ORDER UP!", (600, 285), 74, YELLOW, True)
            self.art.text(self.screen, math.ceil(self.countdown), (600, 361), 76, CREAM, True)

    def draw(self):
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "settings":
            self.draw_settings()
        else:
            self.draw_arena()
            if self.state in ("pause", "result"):
                overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                overlay.fill((*INK, 200))
                self.screen.blit(overlay, (0, 0))
                pygame.draw.rect(self.screen, PANEL, (330, 189, 540, 390), border_radius=16)
                self.art.text(self.screen, "ON THE BACK BURNER" if self.state == "pause" else self.result,
                              (600, 247), 44, YELLOW, True)
                subtitle = "PAUSED" if self.state == "pause" else self.match.reason + " / NEXT ORDER?"
                self.art.text(self.screen, subtitle, (600, 293), 27, MUTED, True)
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
