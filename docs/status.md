# Status (first session)

Verification: spec and code reading only (no Spike 1 emulator or traces). MPF not installable (no PyPI/apt), so
the config was validated for YAML syntax, duplicate keys and cross-references only; the MPF glue (`got/*.py`)
and device syntax (tilt, ball_saves, extra_ball_groups, multiballs, sound_pools) are unrun and may need fixes.

Done
- Switch (S, 61 + 28 dedicated), coil (35), light (80) and 159 settings configs generated from data/*.csv.
- 8 house modes and 7 multiballs as MPF mode configs with timers, awards, start bonuses and ball saves (rules.yaml, with confidence).
- Ball save, tilt (2 warnings), slam tilt, extra ball group (limit 5), basic attract, base scoring (10/30 points).
- Wizard progression (Hand after 4 houses, extra ball at N, Iron Throne when all 7, Winter Has Come) in tested pure Python.
- Core sound map (21 events, from sound_effects.csv) and 9 DMD videos (128x32 frames) copied by gen_media.py (ignored by git).
- Tests: 11 pass without MPF (`tests/run_without_pytest.py`; pytest not installed here either).

Open (owner/emulation): exact award growth, shot-to-switch mapping, Winter link, multiball triggers, coil timings,
Godot project (project.godot, GMC add-on, frame playback), service menu, audits, high scores, remaining modes.
