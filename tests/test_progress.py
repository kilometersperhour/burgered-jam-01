import json
from pathlib import Path
import tempfile
import unittest

from burgerJam.progress import CHARACTERS, Progress

DEFAULTS = {"p1_jab": 102, "p2_jab": 106}


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.path = Path(self.temporary.name) / "profile" / "save.json"

    def write(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def test_loading_missing_save_does_not_create_files(self):
        progress = Progress.load(DEFAULTS, self.path)
        self.assertEqual(progress.wins, 0)
        self.assertFalse(self.path.exists())

    def test_progress_volume_mute_and_custom_controls_round_trip(self):
        progress = Progress.load(DEFAULTS, self.path)
        progress.wins = 3
        progress.volume = .7
        progress.muted = True
        progress.bindings["p1_jab"] = 104
        self.assertTrue(progress.save())
        restored = Progress.load(DEFAULTS, self.path)
        self.assertEqual(restored.wins, 3)
        self.assertEqual(restored.volume, .7)
        self.assertTrue(restored.muted)
        self.assertEqual(restored.bindings["p1_jab"], 104)
        self.assertFalse(self.path.with_name("save.json.tmp").exists())

    def test_roster_unlocks_at_one_three_and_five_cpu_wins(self):
        progress = Progress.load(DEFAULTS, self.path)
        for wins, count in ((0, 2), (1, 3), (3, 4), (5, 5)):
            progress.wins = wins
            self.assertEqual(sum(progress.unlocked(name) for name in CHARACTERS), count)

    def test_corrupt_and_future_saves_are_not_overwritten(self):
        for content in ("not json", '{"version": 99, "wins": 200}', "null", "[]"):
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(content, encoding="utf-8")
            progress = Progress.load(DEFAULTS, self.path)
            self.assertTrue(progress.warning)
            self.assertFalse(progress.save())
            self.assertEqual(self.path.read_text(encoding="utf-8"), content)

    def test_bad_fields_revert_to_defaults(self):
        self.write({"version": 1, "wins": -5, "volume": "loud", "muted": "yes",
                    "bindings": {"p1_jab": 102, "p2_jab": 102}})
        progress = Progress.load(DEFAULTS, self.path)
        self.assertEqual(progress.wins, 0)
        self.assertEqual(progress.volume, .35)
        self.assertFalse(progress.muted)
        self.assertEqual(progress.bindings, DEFAULTS)

    def test_volume_clamps_and_rejects_non_finite_values(self):
        for value, expected in ((-4, 0), (10 ** 400, 1), (float("nan"), .35), (float("inf"), .35)):
            self.write({"version": 1, "volume": value})
            self.assertEqual(Progress.load(DEFAULTS, self.path).volume, expected)

    def test_unwritable_save_reports_failure_without_crashing(self):
        self.path.parent.mkdir(parents=True)
        self.path.mkdir()
        progress = Progress(self.path, bindings=DEFAULTS)
        self.assertFalse(progress.save())
        self.assertTrue(progress.warning)


if __name__ == "__main__":
    unittest.main()
