"""Repeatable combo practice using exactly the normal combat rules."""

from dataclasses import dataclass, field

from .combat import LEFT, RIGHT, Controls, Fighter, Match

DUMMY_MODES = ("stand", "guard", "crouch guard")
CENTER = (LEFT + RIGHT) / 2
DUMMY_LEFT = CENTER - (CENTER - LEFT) * .75
DUMMY_RIGHT = CENTER + (RIGHT - CENTER) * .75


@dataclass
class TrainingSession:
    character: str
    dummy_mode: str = "stand"
    match: Match = field(init=False)
    last_hits: int = 0
    last_damage: int = 0
    last_hit_damage: int = 0
    best_hits: int = 0
    best_damage: int = 0
    total_damage: int = 0

    def __post_init__(self):
        if self.dummy_mode not in DUMMY_MODES:
            raise ValueError("Unknown training dummy mode")
        self.match = Match(training=True)
        self.reset()

    def reset(self):
        """Restore positions and combat state, keeping the session's records."""
        self.match.fighters[:] = [Fighter(480, 1, self.character),
                                  Fighter(600, -1, min_x=DUMMY_LEFT, max_x=DUMMY_RIGHT)]
        self.match.over, self.match.winner, self.match.reason = False, None, ""

    def cycle_dummy(self):
        index = DUMMY_MODES.index(self.dummy_mode)
        self.dummy_mode = DUMMY_MODES[(index + 1) % len(DUMMY_MODES)]

    def update(self, dt, player_controls):
        dummy_controls = Controls(block=self.dummy_mode != "stand", crouch=self.dummy_mode == "crouch guard")
        hits = self.match.update(dt, [player_controls, dummy_controls])
        player = self.match.fighters[0]
        if hits:
            for hit in hits:
                if hit.target == 1:
                    self.last_hit_damage = hit.damage
                    self.total_damage += hit.damage
                    if not hit.blocked and not hit.parried and not hit.countered:
                        self.last_hits, self.last_damage = player.combo_hits, player.combo_damage
                        self.best_hits = max(self.best_hits, self.last_hits)
                        self.best_damage = max(self.best_damage, self.last_damage)
        return hits
