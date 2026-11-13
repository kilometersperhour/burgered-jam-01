"""Deterministic fighting rules, independent of the display and sound devices."""

from dataclasses import dataclass, field
import math
import random

WIDTH = 1200
HEIGHT = 700
FLOOR = 604
LEFT = 80
RIGHT = WIDTH - LEFT
BODY_WIDTH = 72
BODY_HEIGHT = 104
SPEED = 290
GRAVITY = 1900
JUMP_SPEED = 730
ROUND_SECONDS = 60


@dataclass(frozen=True)
class Box:
    x: float
    y: float
    width: float
    height: float

    def overlaps(self, other):
        return (self.x < other.x + other.width and self.x + self.width > other.x
                and self.y < other.y + other.height and self.y + self.height > other.y)


@dataclass(frozen=True)
class Attack:
    windup: float
    active: float
    recovery: float
    damage: int
    reach: int
    knockback: int
    stun: float

    @property
    def duration(self):
        return self.windup + self.active + self.recovery


ATTACKS = {
    "jab": Attack(.08, .09, .19, 8, 64, 18, .16),
    "cross": Attack(.18, .10, .32, 14, 88, 34, .25),
}


@dataclass
class Controls:
    move: int = 0
    block: bool = False
    jump: bool = False
    attack: str | None = None


@dataclass
class Fighter:
    x: float
    facing: int = 1
    character: str = "Burger"
    health: int = 100
    elevation: float = 0
    velocity: float = 0
    attack: str | None = None
    attack_time: float = 0
    connected: bool = False
    blocking: bool = False
    stun: float = 0
    flash: float = 0
    recoil: float = 0
    guard_hit: bool = False

    @property
    def body(self):
        return Box(self.x - BODY_WIDTH / 2, FLOOR - BODY_HEIGHT - self.elevation,
                   BODY_WIDTH, BODY_HEIGHT)

    @property
    def grounded(self):
        return self.elevation <= 0

    @property
    def attack_box(self):
        if self.attack is None:
            return None
        spec = ATTACKS[self.attack]
        if not spec.windup <= self.attack_time < spec.windup + spec.active:
            return None
        edge = self.x + self.facing * (BODY_WIDTH / 2 - 4)
        return Box(edge if self.facing == 1 else edge - spec.reach,
                   FLOOR - self.elevation - 86, spec.reach, 44)

    def start_attack(self, name):
        if (name not in ATTACKS or self.attack is not None or self.blocking
                or self.stun > 0 or self.health <= 0):
            return False
        self.attack = name
        self.attack_time = 0
        self.connected = False
        return True

    def update(self, dt, controls, pressed):
        self.stun = max(0, self.stun - dt)
        self.flash = max(0, self.flash - dt)
        self.recoil = max(0, self.recoil - dt * 5)
        self.blocking = (controls.block and self.grounded and self.attack is None
                         and (self.stun <= 0 or self.guard_hit) and self.health > 0)
        if pressed and controls.jump and self.grounded and self.stun <= 0 and self.health > 0:
            self.velocity = JUMP_SPEED
            self.blocking = False
        if pressed and controls.attack:
            self.start_attack(controls.attack)
        if self.attack:
            self.attack_time += dt
            if self.attack_time >= ATTACKS[self.attack].duration:
                self.attack = None
        speed = SPEED * (.32 if self.blocking else .55 if self.attack else 1)
        if self.stun <= 0 and self.health > 0:
            self.x += max(-1, min(1, controls.move)) * speed * dt
        if self.elevation > 0 or self.velocity > 0:
            self.elevation += self.velocity * dt - GRAVITY * dt * dt / 2
            self.velocity -= GRAVITY * dt
            if self.elevation <= 0:
                self.elevation = 0
                self.velocity = 0
        self.x = max(LEFT, min(RIGHT, self.x))


@dataclass(frozen=True)
class Hit:
    target: int
    blocked: bool
    damage: int


@dataclass
class Match:
    fighters: list[Fighter] = field(default_factory=lambda: [Fighter(330), Fighter(870, -1)])
    remaining: float = ROUND_SECONDS
    over: bool = False
    winner: int | None = None
    reason: str = ""

    def separate(self):
        a, b = self.fighters
        if not a.body.overlaps(b.body):
            return
        left, right = (a, b) if a.x <= b.x else (b, a)
        overlap = BODY_WIDTH - (right.x - left.x)
        left.x -= overlap / 2
        right.x += overlap / 2
        if left.x < LEFT:
            right.x += LEFT - left.x
            left.x = LEFT
        if right.x > RIGHT:
            left.x -= right.x - RIGHT
            right.x = RIGHT

    def update(self, dt, controls):
        """Substep combat so 30/60/120 Hz all observe short attack windows."""
        if self.over or not math.isfinite(dt) or dt <= 0:
            return []
        remaining = min(dt, .1)
        pressed = True
        hits = []
        while remaining > 1e-9 and not self.over:
            step = min(remaining, 1 / 120)
            for i, fighter in enumerate(self.fighters):
                other = self.fighters[1 - i]
                if fighter.attack is None and other.x != fighter.x:
                    fighter.facing = 1 if other.x > fighter.x else -1
                fighter.update(step, controls[i], pressed)
            self.separate()
            # Capture both attacks before applying damage, allowing simultaneous trades.
            contacts = []
            for i, attacker in enumerate(self.fighters):
                box = attacker.attack_box
                if box and not attacker.connected and box.overlaps(self.fighters[1 - i].body):
                    contacts.append((i, ATTACKS[attacker.attack]))
                    attacker.connected = True
            for i, spec in contacts:
                attacker, target = self.fighters[i], self.fighters[1 - i]
                blocked = target.blocking and (attacker.x - target.x) * target.facing > 0
                damage = (2 if spec.damage > 8 else 0) if blocked else spec.damage
                target.health = max(0, target.health - damage)
                target.stun = .07 if blocked else spec.stun
                target.flash = .12
                target.guard_hit = blocked
                target.recoil = .25 if blocked else 1
                if not blocked:
                    target.attack = None
                    target.blocking = False
                target.x = max(LEFT, min(RIGHT, target.x + attacker.facing * spec.knockback
                                        * (.35 if blocked else 1)))
                hits.append(Hit(1 - i, blocked, damage))
            self.remaining = max(0, self.remaining - step)
            a, b = self.fighters
            if a.health == 0 or b.health == 0 or self.remaining <= 0:
                self.over = True
                self.reason = "KO" if a.health == 0 or b.health == 0 else "TIME"
                self.winner = None if a.health == b.health else int(b.health > a.health)
            remaining -= step
            pressed = False
        return hits


class OpponentAI:
    """A reaction delay and distance checks keep the CPU readable and beatable."""

    def __init__(self, seed=None):
        self.random = random.Random(seed)
        self.wait = 0
        self.intent = Controls()

    def update(self, match, dt):
        self.wait -= dt
        if self.wait > 0:
            return self.intent
        self.wait = self.random.uniform(.12, .25)
        player, cpu = match.fighters
        distance = abs(player.x - cpu.x)
        direction = 1 if player.x > cpu.x else -1
        threat = player.attack is not None and distance < 170
        block = threat and cpu.grounded and self.random.random() < .65
        move = direction if distance > 128 else (-direction if distance < 90 else 0)
        attack = None
        if distance < 145 and not block and self.random.random() < .8:
            attack = "jab" if self.random.random() < .65 else "cross"
        self.intent = Controls(move=0 if block else move, block=block, attack=attack,
                               jump=distance < 210 and self.random.random() < .07)
        return self.intent
