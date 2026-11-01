# Status (first session)

Verification: MPF 0.80.1 boots the game headless (smart_virtual) and tests/test_mpf_game.py plays a full 3-ball game (start, house mode shot, drains, game end). Still no Spike 1 traces.

Run with display and sound (headless check, Linux): `pip install mpf==0.80.1 ruamel.yaml.clib==0.2.14 pyyaml`; clone
github.com/missionpinball/mpf-gmc tag v1.0.0 and copy `addons/mpf-gmc` to `game/addons/`; `python scripts/gmc_patch.py`;
`python scripts/gen_media.py` (ROM media, gitignored); `godot --headless --path game --import` (twice); start
`godot --path game` first, then `mpf game game -t` (add `-c smoke` for the sound and DMD slide smoke test).
Verified 2026-11-01: Godot 4.5.2 + GMC 1.0.0 connect to MPF 0.80.1, the game-start music plays on the music bus and the
DMD video slide loads. Pooled sounds play their first sample only (GMC has no pool section).

Done
- Switch (S, 61 + 28 dedicated), coil (35), light (80) and 159 settings configs generated from data/*.csv.
- 8 house modes and 7 multiballs as MPF mode configs with timers, awards, start bonuses and ball saves (rules.yaml, with confidence).
- Ball save, tilt (2 warnings), slam tilt, extra ball group (limit 5), basic attract, base scoring (10/30 points).
- Wizard progression (Hand after 4 houses, extra ball at N, Iron Throne when all 7, Winter Has Come) in tested pure Python.
- Core sound map (21 events, from sound_effects.csv) and 9 DMD videos (128x32 frames) copied by gen_media.py (ignored by git).
- Tests: 11 pass without MPF (`tests/run_without_pytest.py`; pytest not installed here either).

Open (owner/emulation): exact award growth, shot-to-switch mapping, Winter link, multiball triggers, coil timings,
Godot project (project.godot, GMC add-on, frame playback), service menu, audits, high scores, remaining modes.
