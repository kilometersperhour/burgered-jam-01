"""Versioned local progress. Importing this module never creates files."""

from dataclasses import dataclass, field
import json
import math
import os
from pathlib import Path

from .roster import CHARACTERS, UNLOCK_WINS

SAVE_VERSION = 2


@dataclass
class Progress:
    path: Path
    wins: int = 0
    volume: float = .35
    muted: bool = False
    bindings: dict[str, int] = field(default_factory=dict)
    warning: str = ""
    writable: bool = True
    difficulty: str = "medium"

    @classmethod
    def load(cls, defaults, path=None):
        save_path = Path(path) if path is not None else Path(os.environ.get(
            "BURGERJAM_SAVE_PATH", str(Path.home() / ".street-burger" / "save.json")))
        progress = cls(save_path, bindings=dict(defaults))
        try:
            data = json.loads(save_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return progress
        except (OSError, ValueError):
            progress.warning = "Save unavailable. Progress stays in memory this session."
            progress.writable = False
            return progress
        if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] not in (1, SAVE_VERSION):
            progress.warning = "Unsupported save version. Existing save will be preserved."
            progress.writable = False
            return progress
        wins = data.get("wins")
        if type(wins) is int and wins >= 0:
            progress.wins = wins
        volume = data.get("volume")
        if type(volume) in (int, float) and (type(volume) is int or math.isfinite(volume)):
            progress.volume = max(0, min(1, volume))
        if type(data.get("muted")) is bool:
            progress.muted = data["muted"]
        if data.get("difficulty") in ("easy", "medium", "hard"):
            progress.difficulty = data["difficulty"]
        bindings = data.get("bindings")
        if isinstance(bindings, dict) and bindings.keys() <= defaults.keys():
            merged = dict(defaults, **bindings)
            if (all(type(key) is int and 0 < key < 2 ** 31 for key in merged.values())
                    and len(set(merged.values())) == len(merged)):
                progress.bindings = merged
        return progress

    def unlocked(self, character):
        return character in CHARACTERS and self.wins >= UNLOCK_WINS[CHARACTERS.index(character)]

    def save(self):
        if not self.writable:
            return False
        data = {"version": SAVE_VERSION, "wins": self.wins, "volume": self.volume, "muted": self.muted,
                "bindings": self.bindings, "difficulty": self.difficulty}
        temporary = self.path.with_name(self.path.name + ".tmp")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
            temporary.replace(self.path)
        except OSError:
            self.warning = "Could not save. Progress stays in memory this session."
            return False
        self.warning = ""
        return True
