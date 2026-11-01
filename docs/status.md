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
- Service menu: MPF's built-in service mode on the four service buttons; the ROM's 159 adjustments appear in its settings menu and drive balls per game, ball save time and tilt warnings (tests). Audits: MPF's auditor (switches, shots, score, key events) shows in the menu; the ROM's 207 own audit counters are not mapped yet.
- Hurry-ups use the ROM formula (floor 10% of the award, per-update decrement, 5.5 updates/s; Game-of-Thrones docs/06, H formula, M update rate). Winter: 4,000,000 start, ROM lit-shot switches (mask 0xEF). Tested.
- Winter Is Coming chain (docs/06, H from code, not seen live): offered with a house while completed+running <= 6; 3 accepted lit shots start the hurry-up; each completion adds its decayed award to the Winter super jackpot (`got_winter_super`, stored, not yet paid in Winter Has Come); the 4th completion starts Winter Has Come (`got/winter.py`).
- Castle: the three upper standups advance the upper-playfield level (award #19 = 5,000,000 per level, constant; the VPX table grows it, ROM wins); level 4 starts Castle. Standup switches M.
- Wall: advances (left 3-bank hits here; the ROM also advances from pops and Mystery, not wired) light it at min(11, 6 + 5 x Walls awarded); starts at the elevator kick when no multiball runs and Iron Throne is not ready.
- Midnight Madness: starts in the 10 minutes after local midnight (the ROM's RTC wait; the VPX table uses 3 min, ROM wins) when a ball is in play and no multiball runs; every switch listed pays 100,000.
- Still PROVISIONAL: Hand of the King / Iron Throne start on a throne hit (ready conditions are H, start shot is M); Blackwater on three locked balls; the Wall's pop/Mystery advances; Greyjoy needing 4 Winter shots.
- Emulator facts (Game-of-Thrones docs/05): the left bumper adds 1,170 per scoring call; n x 1170 counts switch events, not a multiplier. Winter link still unconfirmed.

Open (owner/emulation): exact award growth, shot-to-switch mapping, Winter link, multiball triggers, coil timings,
Godot project (project.godot, GMC add-on, frame playback), service menu, audits, high scores, remaining modes.
