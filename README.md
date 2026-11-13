# Street Burger: Next Order

A local food fighting game built with Python and Pygame. Originally made for the
[two-hour Burgered Jam](https://itch.io/jam/burgered-jam), unsubmitted.

## Run

Use Python 3.11. From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python burgerJam/burgrerfight.py
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`.
The launcher resolves assets relative to the source, so it also works when invoked
by absolute path from another directory. Importing the game does not open a window.

```sh
.venv/bin/python -m burgerJam.burgrerfight --mute
.venv/bin/python -m burgerJam.burgrerfight --save-file ./my-profile.json
```

## Play

Choose **Fight the CPU** for a solo match or **Local Versus** for two players on
one keyboard. Each match has a countdown, 60-second timer, and a result screen with
rematch and character selection. A knockout ends the match; otherwise, the fighter
with more health wins when time runs out. Equal health is a draw.

| Action | Player 1 | Player 2 |
| --- | --- | --- |
| Move | A / D | Left / Right |
| Jump | W | Up |
| Jab | F | J |
| Cross | G | K |
| Hold guard | S | Down |

In solo mode, left/right mouse clicks also jab/cross; hold the middle mouse button
to guard. Every action can be rebound in **Settings / Keys**, with duplicate keys
rejected. Escape, Enter, and F1 are reserved. Some keyboards cannot register many
simultaneous keys; rebind controls if your keyboard exhibits ghosting.

- **Escape:** pause/resume; return from settings or the result screen.
- **F1:** show body and attack hitboxes during a match.
- **Menus:** Up/Down or Tab to navigate, Enter to select; mouse clicks also work.
- **Characters:** click to select P1, right-click to select P2/the CPU; Left/Right
  cycles P1, Shift+Left/Right cycles P2. Both players can choose the same character.
- Losing window focus automatically pauses a match.
- Quit buttons and the window close button ask "Are you sure?" before exiting.
  Choose **Yes, Quit** to exit, or **Cancel** / Escape to return to the game.

Jabs are fast and deal 8 damage. Crosses have longer startup/recovery and deal 14.
A punch connects once during its active frames; it must face and overlap the
opponent's body. Grounded guard stops jabs and reduces crosses to 2 chip damage.
Jumping avoids attacks when the body clears their hitbox. Attacks lock facing
until recovery, hits interrupt attacks, and both fighters can trade blows.

## Characters and progress

Burger and Tomato are available immediately. Win **1 CPU match** to unlock Italian
Scallion, **3** for French Fries, and **5** for Pizza. Local versus, CPU losses, and
draws do not award wins. All five characters share combat statistics and hitboxes;
the roster is cosmetic in this iteration.

Progress, volume, mute, and keybindings are stored in a versioned local JSON file at
`~/.street-burger/save.json`. Use `--save-file PATH` or the `BURGERJAM_SAVE_PATH`
environment variable for another profile. Writes replace the save atomically.
Unreadable, corrupt, or unsupported-version saves are preserved; play continues
with in-memory defaults and an on-screen warning. An unavailable audio device
does not prevent playing.

## This iteration and the GitHub backlog

| Issue | Included in Next Order |
| --- | --- |
| [#1 Menu functionality](https://github.com/kilometersperhour/burgered-jam-01/issues/1) | Character selection, CPU/versus, settings, quit, pause and rematch |
| [#2 Menu art/music](https://github.com/kilometersperhour/burgered-jam-01/issues/2) | Layered sauce-drip title; original Burgarena music plays across menus and matches, with volume/mute controls |
| [#3 Character art](https://github.com/kilometersperhour/burgered-jam-01/issues/3) | Tomato, Italian Scallion, French Fries and Pizza rendered with Pygame, alongside the original burger |
| [#4 Collisions/hitboxes](https://github.com/kilometersperhour/burgered-jam-01/issues/4) | Separate body and active attack boxes, facing, body separation, stable stage bounds, optional debug display |
| [#5 Combat](https://github.com/kilometersperhour/burgered-jam-01/issues/5) | Timed jab/cross, guard/chip, knockback, hit stun, health bars, KO/time/draw |
| [#6 Opponent AI](https://github.com/kilometersperhour/burgered-jam-01/issues/6) | CPU approaches, spaces, attacks, reacts to threats with guard, and occasionally jumps |
| [#7 Multiplayer](https://github.com/kilometersperhour/burgered-jam-01/issues/7) | Local shared-keyboard versus with independent configurable bindings |
| [#8 Unlockables](https://github.com/kilometersperhour/burgered-jam-01/issues/8) | CPU-win roster unlocks, selectable save file, versioned persistence |
| [#9 Art improvements](https://github.com/kilometersperhour/burgered-jam-01/issues/9) | Sprite shading, floor shadows, hit flashes/recoil and impact particles |

Online multiplayer, QR/portable save encoding, distinct character move sets, newly
composed menu music, and full lighting/animation artwork remain future work.
The original image/audio files and archived jam builds are preserved.

## Check the game

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Tests cover damage/guard, misses, recovery, simultaneous KOs, collision boundaries,
jumps, frame-rate consistency, CPU completion, save validation/unlocks, both players'
inputs, remapping, menus, health bars, rendering, queued events, and launcher imports.
Pygame integration tests use SDL's dummy display/audio drivers and temporary saves;
they do not open a window or modify your profile. To export test screenshots, set
`BURGERJAM_PREVIEW_DIR` to a temporary directory before running the suite.

The [combat rules](burgerJam/combat.py), [progress storage](burgerJam/progress.py),
and [presentation/input](burgerJam/game.py) are separated to make further changes
testable. The original entry point remains [burgrerfight.py](burgerJam/burgrerfight.py).

## Original credits

Code, revisions 0, 1 and 2: **Sean Radel**.

Art, sound and music, revisions 0, 1 and 2: **Miles Martin**.
