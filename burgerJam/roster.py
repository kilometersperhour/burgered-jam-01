"""Shared character data for combat, selection, progression and the move list."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Character:
    name: str
    style: str
    special: str
    special_kind: str
    technique: str
    technique_kind: str
    speed: float = 1
    damage: float = 1
    reach: int = 0
    unlock_wins: int = 0
    arm_color: tuple | None = None


ROSTER = (
    Character("Burger", "Balanced pressure", "Bun Breaker", "rush", "Grill Sweep", "sweep"),
    Character("Tomato", "Quick rising attacks", "Vine Uppercut", "rising", "Salsa Slide", "slide", 1.06, .97, -3, arm_color=(233, 75, 55)),
    Character("Italian Scallion", "Long reach, light hits", "Stalk Strike", "long", "Leaf Cutter", "overhead", 1.03, .94, 16, 1, (136, 188, 91)),
    Character("French Fries", "Fast close-range rushes", "Salt Rush", "rush", "Basket Sweep", "sweep", 1.10, .94, -5, 3, (247, 191, 69)),
    Character("Pizza", "Slow, heavy pressure", "Pepperoni Press", "overhead", "Crust Cutter", "sweep", .93, 1.08, 4, 5, (244, 200, 88)),
    Character("Hot Dog", "Forward pressure and reach", "Frank Fury", "rush", "Relish Roll", "slide", 1.02, 1, 10, arm_color=(168, 74, 49)),
    Character("Pickle", "Rising defense and long sweeps", "Brine Uppercut", "rising", "Dill Sweep", "sweep", .98, 1, 14, arm_color=(115, 180, 66)),
    Character("Ketchup", "Quick slides and pressure", "Redline Rush", "rush", "Sauce Splash", "overhead", 1.08, .95, 2, arm_color=(220, 64, 50)),
    Character("Mustard", "Strong reversals", "Spicy Uppercut", "rising", "Yellow Sweep", "sweep", 1, 1.04, -2, arm_color=(240, 188, 42)),
    Character("Milk Shake", "Heavy slams and long pokes", "Frosty Slam", "overhead", "Straw Strike", "long", .91, 1.10, 6, arm_color=(244, 182, 205)),
)
PROFILES = {character.name: character for character in ROSTER}
CHARACTERS = tuple(character.name for character in ROSTER)
UNLOCK_WINS = tuple(character.unlock_wins for character in ROSTER)
