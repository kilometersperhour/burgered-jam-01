"""Display-independent six-button combat and CPU rules."""

from dataclasses import dataclass, field, replace
import math
import random

from .roster import PROFILES

WIDTH, HEIGHT, FLOOR = 1200, 700, 604
LEFT, RIGHT = 80, WIDTH - 80
BODY_WIDTH, BODY_HEIGHT = 72, 104
SPEED, GRAVITY, JUMP_SPEED = 290, 1900, 730
ROUND_SECONDS = 60
SHIELD_MAX, SHIELD_DRAIN, SHIELD_REGEN = 100, 5, 22
SHIELD_REGEN_DELAY, SHIELD_BREAK_TIME, SHIELD_RECOVER = .9, 1.25, 35
PARRY_TIME, PARRY_COOLDOWN, PARRY_INPUT_WINDOW = .14, .65, .10
COUNTER_TIME, COUNTER_RECOVERY, RIPOSTE_WINDOW = .22, .60, .60
NORMALS = ("lp", "mp", "hp", "lk", "mk", "hk")
DIVES = ("dive_kick", "elbow_drop")
DIFFICULTIES = ("easy", "medium", "hard")
ALIASES = {"jab": "lp", "cross": "hp"}


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
    rank: int = 1
    limb: str = "rear"
    level: str = "mid"
    kind: str = "normal"
    dash: float = 0
    launch: float = 0
    label: str = ""
    dive: float = 0

    @property
    def duration(self):
        return self.windup + self.active + self.recovery


ATTACKS = {
    "lp": Attack(.08, .09, .19, 8, 64, 12, .28, label="Light Punch"),
    "mp": Attack(.12, .10, .24, 10, 76, 15, .32, 2, "front", label="Medium Punch"),
    "hp": Attack(.18, .10, .32, 14, 88, 24, .36, 3, "front", label="Heavy Punch"),
    "lk": Attack(.09, .10, .20, 7, 76, 10, .28, 1, "kick", label="Light Kick"),
    "mk": Attack(.14, .11, .25, 11, 98, 16, .34, 2, "kick", label="Medium Kick"),
    "hk": Attack(.22, .12, .34, 15, 112, 30, .38, 3, "kick", "overhead", label="Heavy Kick"),
    "counter": Attack(.025, .10, .34, 18, 110, 55, .40, 4, "front", kind="counter", label="Counter"),
    "dive_kick": Attack(.045, .85, .20, 14, 50, 18, .35, 3, "kick", "overhead", "dive", label="Downward Kick", dive=1100),
    "elbow_drop": Attack(.06, .85, .26, 16, 52, 22, .38, 3, "front", "overhead", "dive", label="Elbow Drop", dive=950),
}
# Old names remain valid for existing imports and saved tooling.
ATTACKS.update({alias: ATTACKS[name] for alias, name in ALIASES.items()})


def move_for(character, name, crouch=False, airborne=False):
    name = ALIASES.get(name, name)
    profile = PROFILES[character]
    if name in ("special", "technique"):
        kind = profile.special_kind if name == "special" else profile.technique_kind
        label = profile.special if name == "special" else profile.technique
        spec = {
            "rush": Attack(.13, .15, .32, 17, 94, 38, .38, 4, "front", kind="special", dash=350),
            "rising": Attack(.10, .14, .36, 16, 76, 26, .42, 4, "rear", kind="special", launch=330),
            "long": Attack(.16, .13, .33, 16, 148, 30, .38, 4, "front", kind="special"),
            "overhead": Attack(.24, .13, .34, 21, 100, 38, .40, 4, "kick", "overhead", "special"),
            "sweep": Attack(.17, .14, .31, 15, 118, 28, .38, 4, "kick", "low", "special"),
            "slide": Attack(.15, .14, .32, 14, 104, 28, .36, 4, "kick", "low", "special", 280),
        }[kind]
        spec = replace(spec, label=label)
    else:
        spec = ATTACKS[name]
        if name in NORMALS:
            level = "overhead" if airborne else "low" if crouch and name.endswith("k") else spec.level
            spec = replace(spec, level=level, reach=spec.reach - (6 if crouch else 0))
    return replace(spec, damage=max(1, round(spec.damage * profile.damage)),
                   reach=max(30, spec.reach + profile.reach))


@dataclass
class MotionBuffer:
    samples: list = field(default_factory=list)

    def record(self, move, down, facing, now):
        direction = "f" if move * facing > 0 else "b" if move * facing < 0 else "n"
        direction = "d" + (direction if direction != "n" else "") if down else direction
        self.samples = [(time, value) for time, value in self.samples if now - time <= .45]
        if not self.samples or self.samples[-1][1] != direction:
            self.samples.append((now, direction))

    def consume(self, attack, now):
        sequence = [(time, value) for time, value in self.samples if value != "n" and now - time <= .45]
        if len(sequence) < 3 or now - sequence[-1][0] > .15:
            return attack
        motion = tuple(value for _, value in sequence[-3:])
        result = "special" if attack.endswith("p") and motion == ("d", "df", "f") else (
            "technique" if attack.endswith("k") and motion == ("d", "db", "b") else attack)
        if result != attack:
            self.samples.clear()
        return result


@dataclass
class Controls:
    move: int = 0
    block: bool = False
    jump: bool = False
    attack: str | None = None
    crouch: bool = False
    parry: bool = False
    counter: bool = False
    allow_cancel: bool = True
    motions: tuple = ()


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
    crouching: bool = False
    spec: Attack | None = None
    parry_time: float = 0
    parry_cooldown: float = 0
    counter_window: float = 0
    cancel_window: float = 0
    buffered: str | None = None
    buffer_time: float = 0
    combo_hits: int = 0
    combo_damage: int = 0
    combo_time: float = 0
    last_attacker: int | None = None
    clock: float = 0
    motion: MotionBuffer = field(default_factory=MotionBuffer)
    announcement: str = ""
    announcement_time: float = 0
    min_x: float = LEFT
    max_x: float = RIGHT
    dive_landed: bool = False
    shield: float = SHIELD_MAX
    shield_delay: float = 0
    shield_break: float = 0
    counter_time: float = 0
    counter_recovery: float = 0
    shield_held: bool = False
    forward_held: bool = False
    shield_pressed_at: float = -math.inf
    forward_pressed_at: float = -math.inf

    def break_shield(self):
        self.shield = 0
        self.shield_break = SHIELD_BREAK_TIME
        self.stun = max(self.stun, SHIELD_BREAK_TIME)
        self.shield_delay = SHIELD_REGEN_DELAY
        self.blocking = self.guard_hit = False
        self.parry_time = self.counter_time = self.counter_window = 0
        self.attack, self.spec, self.buffered = None, None, None
        self.announcement, self.announcement_time = "SHIELD BREAK!", SHIELD_BREAK_TIME

    @property
    def body(self):
        height = 62 if self.crouching else BODY_HEIGHT
        return Box(self.x - BODY_WIDTH / 2, FLOOR - height - self.elevation, BODY_WIDTH, height)

    @property
    def grounded(self):
        return self.elevation <= 0

    @property
    def current_move(self):
        return self.spec or (move_for(self.character, self.attack) if self.attack else None)

    @property
    def attack_box(self):
        spec = self.current_move
        if spec and spec.kind == "dive":
            if self.dive_landed or self.attack_time < spec.windup:
                return None
            kick = self.attack == "dive_kick"
            center = self.x + self.facing * (18 if kick else 33)
            return Box(center - spec.reach / 2, FLOOR - self.elevation - (25 if kick else 60),
                       spec.reach, 100 if kick else 92)
        if spec is None or not spec.windup <= self.attack_time < spec.windup + spec.active:
            return None
        edge = self.x + self.facing * (BODY_WIDTH / 2 - 4)
        top, height = (38, 30) if spec.level == "low" else (118, 68) if spec.level == "overhead" else (86, 44)
        return Box(edge if self.facing == 1 else edge - spec.reach,
                   FLOOR - self.elevation - top, spec.reach, height)

    def start_attack(self, name, allow_cancel=True):
        name = ALIASES.get(name, name)
        if name not in NORMALS + DIVES + ("special", "technique", "counter"):
            return False
        if (self.stun > 0 or self.health <= 0 or self.parry_time > 0
                or self.shield_break > 0 or self.counter_recovery > 0):
            return False
        if self.blocking or (self.parry_cooldown > .4 and self.counter_window <= 0):
            return False
        if name == "counter" and self.counter_window <= 0:
            return False
        if name in ("special", "technique", "counter") and (not self.grounded or self.velocity > 0):
            return False
        if name in DIVES and self.grounded and self.velocity <= 0:
            return False
        spec = move_for(self.character, name, self.crouching, not self.grounded or self.velocity > 0)
        if self.attack is not None:
            old = self.current_move
            if not (allow_cancel and self.cancel_window > 0 and spec.rank > old.rank and name != "counter"):
                return False
        self.attack, self.spec = name, spec
        self.attack_time = 0
        self.connected = False
        self.cancel_window = 0
        self.buffered = None
        self.dive_landed = False
        if spec.kind == "dive":
            self.elevation = max(1, self.elevation)
            self.velocity = -spec.dive
            self.crouching = False
        if name == "counter":
            self.counter_window = 0
        if spec.kind != "normal":
            self.announcement, self.announcement_time = spec.label.upper(), .8
        return True

    def update(self, dt, controls, pressed):
        self.clock += dt
        was_broken = self.shield_break > 0
        for timer in ("stun", "flash", "parry_time", "parry_cooldown", "counter_window", "cancel_window",
                      "buffer_time", "combo_time", "announcement_time", "shield_delay", "shield_break",
                      "counter_time", "counter_recovery"):
            setattr(self, timer, max(0, getattr(self, timer) - dt))
        if was_broken and self.shield_break == 0:
            self.shield = SHIELD_RECOVER
        forward = controls.move * self.facing > 0
        shield_edge = controls.block and not self.shield_held
        forward_edge = forward and not self.forward_held
        if shield_edge:
            self.shield_pressed_at = self.clock - dt
        if forward_edge:
            self.forward_pressed_at = self.clock - dt
        gesture = (controls.block and forward and (shield_edge or forward_edge)
                   and abs(self.shield_pressed_at - self.forward_pressed_at) <= PARRY_INPUT_WINDOW)
        self.shield_held, self.forward_held = controls.block, forward
        self.recoil = max(0, self.recoil - dt * 5)
        if self.combo_time == 0:
            self.combo_hits = self.combo_damage = 0
        if self.buffer_time == 0:
            self.buffered = None
        if self.attack is None:
            self.crouching = controls.crouch and self.grounded
        self.motion.record(controls.move, controls.crouch, self.facing, self.clock)
        ready = (self.grounded and self.velocity <= 0 and self.attack is None and self.health > 0
                 and self.shield_break == 0 and self.counter_recovery == 0)
        self.blocking = (controls.block and ready and self.shield > 0
                         and (self.stun <= 0 or self.guard_hit) and self.parry_time == 0)
        if ((gesture or (pressed and controls.parry)) and ready and self.stun <= 0
                and self.parry_cooldown == 0):
            self.parry_time, self.parry_cooldown = PARRY_TIME, PARRY_COOLDOWN
            self.blocking = False
        if (pressed and controls.counter and self.counter_window == 0 and ready
                and self.stun <= 0 and self.parry_time == 0 and self.parry_cooldown <= .4):
            self.counter_time, self.counter_recovery = COUNTER_TIME, COUNTER_RECOVERY
            self.blocking = False
            self.announcement, self.announcement_time = "COUNTER STANCE", COUNTER_TIME
        if (pressed and controls.jump and self.grounded and self.stun <= 0 and self.parry_time == 0
                and self.health > 0 and self.shield_break == 0 and self.counter_recovery == 0):
            self.velocity = JUMP_SPEED
            self.crouching = self.blocking = False
        requested = "counter" if controls.counter else controls.attack
        if pressed and requested:
            # A parry grants a fast reply even while the shield button is still held.
            if self.counter_window > 0 and self.grounded and (controls.counter or requested in NORMALS):
                requested = "counter"
                self.blocking = False
            elif not controls.block:
                self.blocking = False
            requested = ALIASES.get(requested, requested)
            if requested in NORMALS:
                if controls.crouch and (not self.grounded or self.velocity > 0):
                    requested = "dive_kick" if requested.endswith("k") else "elbow_drop"
                elif self.grounded:
                    requested = self.motion.consume(requested, self.clock)
            if not self.start_attack(requested, controls.allow_cancel) and controls.allow_cancel and self.attack:
                if requested in NORMALS + DIVES + ("special", "technique"):
                    new = move_for(self.character, requested)
                    if new.rank > self.current_move.rank:
                        self.buffered, self.buffer_time = requested, .14
        if self.buffered and self.cancel_window > 0 and controls.allow_cancel:
            self.start_attack(self.buffered)
        if self.attack:
            self.attack_time += dt
            if (self.current_move.kind != "dive" or self.dive_landed) and self.attack_time >= self.current_move.duration:
                self.attack, self.spec = None, None
        speed = SPEED * PROFILES[self.character].speed
        speed *= 0 if self.blocking else .55 if self.attack else 1
        if self.stun <= 0 and self.health > 0 and self.shield_break == 0 and self.counter_recovery == 0:
            if not self.crouching and self.parry_time <= 0:
                self.x += max(-1, min(1, controls.move)) * speed * dt
            spec = self.current_move
            if spec and spec.dash and self.attack_time < spec.windup + spec.active:
                self.x += self.facing * spec.dash * dt
        if self.elevation > 0 or self.velocity > 0:
            self.elevation += self.velocity * dt - GRAVITY * dt * dt / 2
            self.velocity -= GRAVITY * dt
            if self.elevation <= 0:
                self.elevation = self.velocity = 0
                if self.current_move and self.current_move.kind == "dive" and not self.dive_landed:
                    self.dive_landed = True
                    self.attack_time = self.current_move.windup + self.current_move.active
        if self.blocking:
            self.shield = max(0, self.shield - SHIELD_DRAIN * dt)
            self.shield_delay = SHIELD_REGEN_DELAY
            if self.shield == 0:
                self.break_shield()
        elif (not controls.block and self.shield_break == 0 and self.shield_delay == 0
              and self.counter_recovery == 0 and self.parry_time == 0):
            self.shield = min(SHIELD_MAX, self.shield + SHIELD_REGEN * dt)
        self.x = max(self.min_x, min(self.max_x, self.x))


@dataclass(frozen=True)
class Hit:
    target: int
    blocked: bool
    damage: int
    parried: bool = False
    countered: bool = False
    shield_broken: bool = False


@dataclass
class Match:
    fighters: list[Fighter] = field(default_factory=lambda: [Fighter(330), Fighter(870, -1)])
    remaining: float = ROUND_SECONDS
    over: bool = False
    winner: int | None = None
    reason: str = ""
    training: bool = False

    def separate(self):
        a, b = self.fighters
        if not a.body.overlaps(b.body):
            return
        left, right = (a, b) if a.x <= b.x else (b, a)
        overlap = BODY_WIDTH - (right.x - left.x)
        left.x -= overlap / 2
        right.x += overlap / 2
        if left.x < left.min_x:
            right.x += left.min_x - left.x
            left.x = left.min_x
        if right.x > right.max_x:
            left.x -= right.x - right.max_x
            right.x = right.max_x

    def update(self, dt, controls):
        if self.over or not math.isfinite(dt) or dt <= 0:
            return []
        for fighter, control in zip(self.fighters, controls):
            for move, down in control.motions:
                fighter.motion.record(move, down, fighter.facing, fighter.clock)
        remaining, pressed, hits = min(dt, .1), True, []
        while remaining > 1e-9 and not self.over:
            step = min(remaining, 1 / 120)
            for i, fighter in enumerate(self.fighters):
                other = self.fighters[1 - i]
                if fighter.attack is None and other.x != fighter.x:
                    fighter.facing = 1 if other.x > fighter.x else -1
                fighter.update(step, controls[i], pressed)
            self.separate()
            contacts = []
            for i, attacker in enumerate(self.fighters):
                box = attacker.attack_box
                if box and not attacker.connected and box.overlaps(self.fighters[1 - i].body):
                    contacts.append((i, attacker.current_move))
                    attacker.connected = True
            for i, spec in contacts:
                attacker, target = self.fighters[i], self.fighters[1 - i]
                front = (attacker.x - target.x) * target.facing > 0
                if target.parry_time > 0 and target.stun <= 0 and front:
                    target.parry_time = 0
                    target.counter_window = RIPOSTE_WINDOW
                    target.announcement, target.announcement_time = "PARRY!", .6
                    attacker.stun = .32
                    attacker.attack, attacker.spec, attacker.buffered = None, None, None
                    hits.append(Hit(1 - i, False, 0, True))
                    continue
                if target.counter_time > 0 and target.stun <= 0 and front:
                    target.counter_time = target.counter_recovery = 0
                    target.blocking = False
                    target.counter_window = RIPOSTE_WINDOW
                    target.start_attack("counter")
                    target.spec = replace(target.current_move, damage=max(target.current_move.damage, round(spec.damage * 1.25)))
                    target.announcement, target.announcement_time = "COUNTER!", .8
                    attacker.stun = .32
                    attacker.attack, attacker.spec, attacker.buffered = None, None, None
                    hits.append(Hit(1 - i, False, 0, countered=True))
                    continue
                blocked = target.blocking and front
                chained = target.stun > 0 and target.last_attacker == i and attacker.combo_time > 0
                count = attacker.combo_hits + 1 if chained else 1
                damage = 0 if blocked else max(1, round(spec.damage * .85 ** (count - 1)))
                shield_broken = False
                if blocked:
                    target.shield = max(0, target.shield - max(8, spec.damage * 1.6 + spec.rank * 2))
                    target.shield_delay = SHIELD_REGEN_DELAY
                    shield_broken = target.shield == 0
                if not self.training:
                    target.health = max(0, target.health - damage)
                target.stun = .09 if blocked else spec.stun
                target.flash, target.guard_hit, target.recoil = .12, blocked, .25 if blocked else 1
                if not blocked:
                    target.attack, target.spec, target.buffered = None, None, None
                    target.parry_time = target.counter_time = target.counter_window = 0
                    target.blocking = False
                    target.last_attacker = i
                    target.velocity = spec.launch if spec.launch else target.velocity
                    if spec.launch:
                        target.elevation = max(1, target.elevation)
                        target.crouching = False
                    attacker.cancel_window = .22
                    attacker.combo_hits = count
                    attacker.combo_damage = attacker.combo_damage + damage if chained else damage
                    attacker.combo_time = 1.2
                target.x = max(target.min_x, min(target.max_x, target.x + attacker.facing * spec.knockback * (.35 if blocked else 1)))
                if shield_broken:
                    target.break_shield()
                hits.append(Hit(1 - i, blocked, damage, shield_broken=shield_broken))
            if not self.training:
                self.remaining = max(0, self.remaining - step)
            a, b = self.fighters
            if not self.training and (a.health == 0 or b.health == 0 or self.remaining <= 0):
                self.over = True
                self.reason = "KO" if a.health == 0 or b.health == 0 else "TIME"
                self.winner = None if a.health == b.health else int(b.health > a.health)
            remaining -= step
            pressed = False
        return hits


class OpponentAI:
    """Difficulty changes the allowed decisions, not just reaction speed."""

    def __init__(self, seed=None, difficulty="medium"):
        if difficulty not in DIFFICULTIES:
            raise ValueError("Unknown CPU difficulty")
        self.random = random.Random(seed)
        self.difficulty = difficulty
        self.wait = 0
        self.intent = Controls(allow_cancel=difficulty == "hard")

    def update(self, match, dt):
        self.wait -= dt
        player, cpu = match.fighters
        distance = abs(player.x - cpu.x)
        direction = 1 if player.x > cpu.x else -1
        if self.difficulty == "hard" and cpu.cancel_window > 0 and cpu.attack:
            next_move = {1: "mp", 2: "hp", 3: "special"}.get(cpu.current_move.rank)
            if next_move:
                return Controls(move=direction, attack=next_move)
        if self.difficulty != "hard" and player.stun > 0 and player.last_attacker == 1:
            # Wait for recovery as well as forbidding cancels: Medium never links a combo.
            return replace(self.intent, attack=None, parry=False, counter=False, jump=False)
        if self.wait > 0:
            return replace(self.intent, attack=None, parry=False, counter=False, jump=False)
        self.wait = self.random.uniform(*{"easy": (.28, .46), "medium": (.15, .26), "hard": (.07, .15)}[self.difficulty])
        threat = player.attack is not None and distance < 190
        advanced = self.difficulty != "easy"
        parry = advanced and threat and self.random.random() < (.22 if self.difficulty == "hard" else .1)
        counter = advanced and (cpu.counter_window > 0 or (threat and not parry and self.random.random() < .12))
        block = threat and not parry and not counter and cpu.shield_break == 0 and cpu.shield > 15 and self.random.random() < .55
        crouch = advanced and ((block and player.current_move and player.current_move.level == "low")
                               or self.random.random() < .10)
        attack = None
        if distance < 155 and not block and not parry:
            pool = NORMALS if not advanced else NORMALS + ("special", "technique")
            attack = self.random.choice(pool)
            if self.difficulty == "hard" and cpu.attack is None and self.random.random() < .6:
                attack = "lp"
        if advanced and not cpu.grounded and attack in NORMALS and self.random.random() < .5:
            crouch = True
        self.intent = Controls(move=0 if block else direction if distance > 122 else 0,
            block=block, crouch=bool(crouch), parry=parry, counter=counter,
            jump=advanced and not threat and distance < 200 and self.random.random() < .06,
            attack=attack, allow_cancel=self.difficulty == "hard")
        return self.intent
