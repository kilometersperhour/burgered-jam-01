# Street Burger: Next Order

A food fighting game built with Python and Pygame. Originally made for the
[two-hour Burgered Jam](https://itch.io/jam/burgered-jam), unsubmitted.

## Run with Python 3.11

The game requires **Python 3.11 or newer**. From the repository root:

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python burgerJam/burgrerfight.py
```

If your terminal is already inside the **burgerJam** folder, use:

```sh
../.venv/bin/python -m pip install -r ../requirements.txt
../.venv/bin/python burgrerfight.py
```

Use these explicit paths even when your prompt says `.venv` or `(base)`.
A bare `python` or `python3` can resolve to macOS's Python 3.9 or a Conda
interpreter instead. A virtual environment created using Python 3.9 remains a 3.9
environment; creating it with `python3.11` selects the required interpreter.

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`.
Assets resolve relative to the source, so launching by absolute path also works.
Importing the game never opens a window.

```sh
.venv/bin/python -m burgerJam.burgrerfight --mute
.venv/bin/python -m burgerJam.burgrerfight --save-file ./my-profile.json
```

## Six-button controls

**Local shared-keyboard versus is currently unavailable.** Choose a player fighter
and CPU opponent, select Easy / Medium / Hard, then choose **Fight the CPU**.
Choose **Go to the Grill** instead to practice combos against a dummy in the kitchen.

The default layout uses letters; Settings also provides a full numpad attack preset.
Either preset can be customized action by action. Duplicate bindings are rejected.

| Action | Default | Numpad preset |
| --- | --- | --- |
| Left / back when facing right | A | A |
| Down / crouch | S | S |
| Right / forward when facing right | D | D |
| Jump | Space or W | Space or W |
| Light Punch (LP) | U | Numpad 4 |
| Medium Punch (MP) | I | Numpad 5 |
| Heavy Punch (HP) | O | Numpad 6 |
| Light Kick (LK) | J | Numpad 1 |
| Medium Kick (MK) | K | Numpad 2 |
| Heavy Kick (HK) | L | Numpad 3 |
| Hold shield | Left Shift | Left Shift |
| Timed parry | Forward + Left Shift, or Q | Forward + Left Shift, or Q |
| Counter stance / reply after parry | E | E |

Back and forward are relative to the opponent; the fighter turns automatically
when free to act. Attacks lock facing until recovery. Holding both A and D is neutral.
A and D move at the same full speed in either direction. Moving backward never
automatically guards. Shielding uses its own button and stops walking.
Crouching stops walking and shrinks the body hitbox. Space and W both jump;
each jump binding can be customized separately.

Left/right mouse clicks remain optional shortcuts for LP/HP; hold middle mouse
to shield. The full move set uses the keyboard.

- **F2:** open the move list during a match; gameplay freezes until you return.
- **Escape:** pause/resume, return from menus, or cancel quitting.
- **F1:** show body and active attack hitboxes.
- **F3 (at the Grill):** reset practice positions, health and combat state.
- **F4 (at the Grill):** cycle the dummy between Stand, Guard and Crouch Guard.
- **Menus:** Up/Down or Tab navigates; Enter selects; mouse clicks also work.
- **Character selection:** click for your fighter, right-click for the CPU.
  Left/Right cycles your fighter; Shift+Left/Right cycles the CPU.
- **Move list:** Left/Right browses all ten fighters, including locked characters.
  Tabs cover basics/defense, character specials, air/dives, and combos.
- Losing focus automatically pauses. Quit buttons and closing the window ask
  "Are you sure?" with Cancel selected initially.

Escape, Enter and F1-F4 are reserved. Some keyboards cannot register many held
keys simultaneously; rebind controls if your keyboard exhibits ghosting.

## Go to the Grill: combo training

Select your fighter, then choose **Go to the Grill** on the main menu. Training
takes place in a pixel-art kitchen with a flat-top grill, extractor hood, prep
counter and kitchen utensils, using the same colors and sprite style as the game.
Your opponent is a spring-mounted flour-sack dummy. It never moves or attacks on
its own; CPU selection and difficulty do not affect training.

- **Unlimited practice:** no countdown, round timer, health depletion, knockouts
  or match results.
- **Persistent positions:** the dummy stays where you push it. Its travel stops
  75% of the distance from the arena center toward either wall, leaving room to
  jump behind it and attack from the other side. There is no automatic recentering.
- **Feedback:** a total-damage meter replaces the dummy's health bar and keeps
  counting beyond 100 damage. Shielded hits cause no health damage and do not add
  to this total. The HUD also shows the last
  combo's hits and damage, last-hit damage, and best hit count/damage.
- **F3:** reset positions and combat state immediately while preserving total
  damage and the session's combo records.
- **F4:** cycle Stand, standing Guard, and Crouch Guard to test hit confirms and
  shield pressure. Both guard modes use the new shield rules; repeated hits can
  break the dummy's shield. Changing guard mode preserves positions and durability.
- **F2:** pause practice to review your fighter's normals, specials, dives and combos.
- **Escape:** pause to reset practice, change dummy behavior, review moves, adjust
  settings, or return to the main menu.

Training uses the same hitboxes, timing, motion inputs, cancels and damage scaling
as regular matches. It does not award wins or unlocks, and session records reset
when you leave and start a new training session.

## Attacks, defense and combos

Six normal attacks have different startup, recovery, range, damage and animations.
Both arms remain visible; punches use the rear/front arms and kicks extend a leg.
Arms and legs use each character's food palette, including green Pickle limbs;
Burger retains its original arm artwork.
Crouching kicks hit **low**, standing Heavy Kick hits **overhead**, and airborne
normal attacks also hit overhead.

Two downward attacks are available to every character while airborne:

- **Downward Kick:** hold S and press any kick (J/K/L or Numpad 1/2/3).
  Descend quickly with a leg pointed down.
- **Elbow Drop:** hold S and press any punch (U/I/O or Numpad 4/5/6).
  Tilt the body and descend elbow-first.

Both dives hit overhead once per descent and recover after landing. A shield,
timed parry or counter stance can stop them. On the ground,
Down + attack still performs the normal crouching attack. See the **Air / Dives**
tab in the move list for current bindings and character-specific damage.

**Shield:** hold Left Shift to raise a visible shield. It blocks frontal punches,
kicks and specials at every height, whether standing or crouching. Hits reduce
shield durability instead of health, and strong attacks wear it down faster.
The HUD shows a separate shield meter; the bubble shrinks and turns red when weak.
Shielding and parrying require the ground.

The shield starts at 100 durability and drains 5 per second while held. Release
it for 0.9 seconds to begin recovering 22 per second. At zero it breaks: the bubble
vanishes, stars and a **SHIELD BREAK** warning appear, and movement, attacks and
defense are disabled for 1.25 seconds. Follow-up attacks deal full health damage.
The fighter then recovers with 35 shield durability. F3 at the Grill restores
shields as part of resetting combat, while keeping the session's damage records.

**Parry:** press Forward and Shield within 100 ms of one another, just before the
incoming hit lands. Facing right, use D + Left Shift; facing left, use A + Left Shift.
Q remains a dedicated parry shortcut. The 140 ms window catches an incoming attack,
prevents damage to both health and shield, and interrupts the attacker. Within
600 ms after a successful parry, press **any punch, any kick, or E** to deliver a
fast counterattack. This works even while still holding Shield. Holding Forward
and Shield does not repeatedly parry: release and time a fresh input. Missed
parries briefly prevent attacking and have a cooldown.

**Counter stance:** press E without a parry to brace for 220 ms. If a frontal hit
lands during that window, it deals no damage and automatically triggers a fast
counterattack, dealing at least the character's normal counter damage or 125% of
the incoming attack's damage, whichever is greater. An unsuccessful stance leaves
you open until 600 ms after activation; it cannot be cancelled into a shield,
jump or attack. The stance requires the ground. Yellow effects distinguish it
from the shield and white parry flash. E after a successful parry still performs
the immediate reply instead of entering a stance.

Each fighter has two named specials:

- **Quarter-circle forward + any punch:** Down > Down+Forward > Forward + LP/MP/HP.
  Facing right on default keys: S > S+D > D + U/I/O.
- **Quarter-circle back + any kick:** Down > Down+Back > Back + LK/MK/HK.
  Facing right: S > S+A > A + J/K/L.

Directions mirror when facing left. Complete the motion within 450 ms and press the
attack promptly. Motion inputs are consumed once, and specials require the ground.
Depending on the character, specials rush, slide, launch, sweep, hit overhead,
or strike at long range.

**Hit-confirm combos** let a connected attack cancel into a stronger one:

| Combo | Default letters |
| --- | --- |
| LP > MP > HP | U > I > O |
| LK > MK > HK | J > K > L |
| LP > MK > HP | U > K > O |
| Light > Medium > Heavy > Special | Finish either chain with the quarter-circle motion |

Press the next button near impact; a 140 ms buffer accepts slightly early inputs.
Only ascending strengths can cancel, and misses or blocked attacks cannot cancel.
Keep close or hold Forward to maintain range. A hit counts toward the same combo
only while the defender is still in hit stun. Later hits deal progressively less
damage; the HUD shows the combo count and total damage.

The in-game move list uses the actual character move data and your current
keybindings, so its damage values, specials and combo inputs stay in sync.

## CPU difficulty

| Level | Behavior |
| --- | --- |
| Easy | Movement, shielding, and simple six-button normal attacks; no specials, parries, counters or combos |
| Medium | All moves, including specials, dives, parries and counters; waits for recovery and does not chain combos |
| Hard | All moves plus confirmed-hit combo chains and special finishers, with quicker reactions |

The chosen difficulty is saved in your profile and shown in the match HUD.
Each match has a countdown and a 60-second timer. A knockout ends the match;
otherwise higher health wins at time, with equal health resulting in a draw.
Every knockout, including an ordinary punch or kick, plays a 1.6-second final-hit
sequence before the results menu: a brief impact freeze and flash, a small screen
shake, the defeated fighter falling with both arms attached, and a K.O. banner.
Airborne fighters settle back to the floor; double knockouts animate both fighters.
Combat and the round timer stop immediately, and attacks or clicks during the
sequence cannot accidentally select a results-menu action. Losing window focus
or opening the quit confirmation freezes the sequence. Timeouts show results
directly without a knockout animation, and training never triggers it.
The result screen supports rematches, character selection, the move list, and quit.

## Ten fighters

Each fighter has slightly different movement speed, normal damage/reach and two
special moves. Stats are shared by the CPU and player; difficulty does not change
a fighter's damage or health.

| Fighter | Style | Forward + Punch special | Back + Kick special | Availability |
| --- | --- | --- | --- | --- |
| Burger | Balanced pressure | Bun Breaker: rush | Grill Sweep: low sweep | Immediately |
| Tomato | Quick rising attacks | Vine Uppercut: launcher | Salsa Slide: low slide | Immediately |
| Italian Scallion | Long reach, lighter hits | Stalk Strike: long poke | Leaf Cutter: overhead | 1 CPU win |
| French Fries | Fast close-range rushes | Salt Rush: rush | Basket Sweep: low sweep | 3 CPU wins |
| Pizza | Slow, heavy pressure | Pepperoni Press: overhead | Crust Cutter: low sweep | 5 CPU wins |
| Hot Dog | Forward pressure and reach | Frank Fury: rush | Relish Roll: low slide | Immediately |
| Pickle | Rising defense and long sweeps | Brine Uppercut: launcher | Dill Sweep: low sweep | Immediately |
| Ketchup | Quick slides and pressure | Redline Rush: rush | Sauce Splash: overhead | Immediately |
| Mustard | Strong reversals | Spicy Uppercut: launcher | Yellow Sweep: low sweep | Immediately |
| Milk Shake | Heavy slams and long pokes | Frosty Slam: overhead | Straw Strike: long poke | Immediately |

## Progress and settings

Wins, unlocks, difficulty, volume, mute, and bindings are saved at
`~/.street-burger/save.json`. Use `--save-file PATH` or the
`BURGERJAM_SAVE_PATH` environment variable for a different profile.

Version 1 profiles migrate to version 2 while keeping wins and audio preferences.
The old two-player bindings reset to the new six-button defaults. Existing
character unlocks remain; all five new fighters are immediately available.
Compatible saved six-button bindings are preserved when adding the alternate
W jump binding; conflicting or invalid maps fall back to the defaults.

Writes replace the save atomically. Unreadable, corrupt, or unsupported future
saves are preserved; play continues with in-memory defaults and a warning.
An unavailable audio device does not prevent playing.

## Checks and code

```sh
.venv/bin/python -m unittest discover -s tests -v
```

Tests cover normal and special attacks, full-speed backward movement, shield
durability/break/recovery, timed forward-shield parries and reactive counters,
motion recognition in both directions, combo buffering/scaling, CPU restrictions
and match completion, dive collisions/landing/guarding, bounded training dummy
movement and cumulative damage, training resets/guard modes/records, persistence/migration,
input presets/remapping, rendering, knockout timing/poses/input handling,
pause/quit flow, and launching outside the repository.

Pygame checks use dummy display/audio drivers and temporary saves. They do not open
a window or change your profile. Set `BURGERJAM_PREVIEW_DIR` to a temporary directory
to export test screenshots.

- [Combat rules and CPU](burgerJam/combat.py)
- [Shared roster and character move profiles](burgerJam/roster.py)
- [Rendering, controls and menus](burgerJam/game.py)
- [Profile storage](burgerJam/progress.py)
- [Training sessions and dummy behavior](burgerJam/training.py)
- [Kitchen and practice dummy artwork](burgerJam/kitchen.py)
- [Launcher](burgerJam/burgrerfight.py)

Online multiplayer, a replacement for shared-keyboard versus, and portable/QR saves
remain future work. The original image/audio files and archived jam builds are
preserved. The title credits remain "Sean and Miles present" and "burger jam".

## Original credits

Code, revisions 0, 1 and 2: **Sean Radel**.

Art, sound and music, revisions 0, 1 and 2: **Miles Martin**.
