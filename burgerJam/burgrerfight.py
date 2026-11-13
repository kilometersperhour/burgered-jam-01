"""Launch Street Burger from any working directory."""

import argparse
from pathlib import Path
import sys

if sys.version_info < (3, 11):
    raise SystemExit("Street Burger requires Python 3.11+. From the burgerJam folder, run: "
                     "../.venv/bin/python burgrerfight.py (or python3.11 burgrerfight.py).")

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from burgerJam.game import Game


def main():
    parser = argparse.ArgumentParser(description="Street Burger: a local food fight.")
    parser.add_argument("--mute", action="store_true", help="Start without sound.")
    parser.add_argument("--save-file", type=Path, help="Use a specific progress/settings file.")
    args = parser.parse_args()
    Game(save_path=args.save_file, mute=args.mute).run()


if __name__ == "__main__":
    main()
