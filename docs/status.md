# Status

Current state (2026-11-03, 122 tests pass; the mode sections at the end of this page, "Modes on the ROM state machines", supersede older mode bullets): built from the extraction: lights, attract, credits, high scores, match, all sounds and clips available, ROM display effects wired from def_callers (text effects drawn with the ROM bitmap fonts, run-time values for score, award, mode timer, shots, player and ball), background music by state, coil times, Pict-O-Pops and other audits, a ROM-style service menu on the DMD. Missing and departures: docs/rom_differences.md. The notes below are the running log of each feature.

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
- Service menu: MPF's built-in service mode on the four service buttons; the ROM's 159 adjustments appear in its settings menu and drive balls per game, ball save time and tilt warnings (tests). Audits: MPF's auditor (switches, shots, score, key events) shows in the menu, plus about 70 of the ROM's 207 audit counters (`got/audit_map.py`: flippers, shot switches, balls played, tilts, saves, multiball starts and supers, Mystery awards, house select and battles, player-count games). Not mapped: coins/credits, histograms, ball search, fixtures, video mode, pops, wildfire/lock/sword/PFx awards, Lord of Light, Castle shots.
- Hurry-ups use the ROM formula (floor 10% of the award, per-update decrement, 5.5 updates/s; Game-of-Thrones docs/06, H formula, M update rate). Winter: 4,000,000 start, ROM lit-shot switches (mask 0xEF). Tested.
- Winter Is Coming chain (docs/06, H from code, not seen live): offered with a house while completed+running <= 6; 3 accepted lit shots start the hurry-up; each completion adds its decayed award to the Winter super jackpot (`got_winter_super`, stored, not yet paid in Winter Has Come); the 4th completion starts Winter Has Come (`got/winter.py`).
- Scoring tables (Game-of-Thrones docs/07, data/scoring.csv, ELF values win over the VPX table): all house and multiball award start/bump/cap are generated from it; Winter's award grows +75,000 per completion. Fixed switch scores (docs/08, data/switch_events.csv): 530 return lanes, 25,000 outlanes, 3,330 kickback, 1,170 pops, ... in the generated `scoring` mode. Not wired: the tickle award #0 (75,000 +25,000 per hit) for shots without an award object, the awards 1 and 9 growth (not extracted).
- Castle: the three upper standups advance the upper-playfield level (award #19: 5,000,000, +2,500,000 per level to 15,000,000; the per-level bump is M); level 4 starts Castle. Standup switches M.
- Wall: advances (left 3-bank hits and the kickback, H for the kickback; the ROM also advances from pops and Mystery, not wired) light it at min(11, 6 + 5 x Walls awarded); starts at the elevator kick when no multiball runs and Iron Throne is not ready.
- Midnight Madness: starts in the 10 minutes after local midnight (the ROM's RTC wait; the VPX table uses 3 min, ROM wins) when a ball is in play and no multiball runs; every switch listed pays 100,000.
- Wizard starts (docs/06, H from code, not seen live): at the left ramp exit or when a ball enters the lock, Iron Throne is checked first (all 7 houses done, no multiball), then Hand of the King (4 houses done, no multiball, no house running); Wall starts at the elevator kick (lit, no multiball, Iron not startable). Winter's lit shots count only while no house mode or multiball runs and Hand is not startable. Wall advances: kickback and a completed left 3-bank (H); Mystery and the pop-award list also advance it in the ROM (not wired: no Mystery yet).
- Award growth: Hand of the King jackpot 2,500,000 start, +175,000, cap 25,000,000 (the +100,000,000 super-jackpot carry-over and the later-phase table are not wired); Targaryen's value per dragon level (8/10/12/15M) is not wired.
- House details (community rulesheet rev 1.37 over the ROM values, M): Stark = 3 ramp shots build the kill list, then an orbit collects; Martell = 3 orbits within 10 s then either ramp collects (mode timer 30 s from the rulesheet; the ROM's 10 s timer id 10 is read as the hurry-up part). Baratheon (spinner builds, left 3-bank cashes in), Lannister (gold standups give credit, 5 main shots), Greyjoy (each main shot once, 15 s refresh), Tyrell (ramps, lock targets, right ramp) follow the rulesheet in simplified form (M; no dragon waves, Castle collection, stacking, PASS or Greyjoy extras). Targaryen: four dragon battles kept per player (waves on ramps and loops, then the kickback shot collects 8/10/12/15M, ROM values; wave randomness, DRAGON FIRE and Greyjoy extras not modelled).
- Multiball phases (rulesheet over ROM award values, structure M, Super multiplier CFG placeholder): Blackwater = the 5 majors once each light a 20 s Super at the ram; Wall = 3 ramp shots, dragon (kickback) Super, then 3 loop shots; Hand = 4-shot sets, Super at the ram, ends after 3 sets; Iron Throne = 5-shot sets (7 sets, one per house). Not modelled: Blackwater's double-value rework after a timed-out Super, Wildfire, Castle Collection, Hand house carry-ins, Iron Throne victory lap and per-house shields. Winter Has Come: Horde (7 majors once each) then Lieutenant (3 random hurry-up shots, 5 collected pay the stored Winter super jackpot and return to Horde); Horde timer, Lieutenant timeouts and the frozen flipper not modelled.
- House choice and powers (rulesheet, M): on ball 1 the flippers cycle the 7 houses (default Stark) until the ball leaves the shooter lane; Targaryen and Greyjoy start complete; Stark adds 10M to Winter Is Coming's base; Baratheon starts with 2 Wall advances. Action button (the top player button, `s_lockdown`), once per ball: Stark Direwolf completes the current house for 5M; Targaryen freezes timers 15 s; Martell adds a ball in multiball. Not modelled: Lannister gold and Golden PFx, Greyjoy persistent powers and Plunder, Tyrell inlane/Iron Bank, Baratheon's Lord of Light, purchasable actions, casual mode, the house-choice display.
- Secondary systems (`got/extras.py`, rulesheet, M): gold from the five standups (100 each, CFG placeholder; Lannister 2.43x and 500 at start); all five light Mystery, collected at the elevator, which opens the ROM's 3-slot Mystery menu over the 40-entry table (docs/11, see Mystery section below); Bonus X +1 per completed top lanes (max 20); playfield multiplier from battering-ram hits (4th hit 2x, +1x every 4 hits, max 5x). End-of-ball bonus (Game-of-Thrones docs/09, H): 125,000 base per ball + 3,330 per playfield switch event + 175,000 per house + 150,000 per sword + 7,500,000 per castle + 300 per gold + 5,500 per wildfire + 750,000 Golden Hand, x Bonus X (max 20), paid on ball end (not on tilt); Hold Bonus keeps value and Bonus X for the next ball; the double-up of the last ball is not modelled. Pict-O-Pops (docs/09): three reels over a strip rebuilt on every hit, a pair completes itself, never the same award twice, 14 of the 18 awards have effects (the tape order is a fixed interleaving of the ROM's per-id counts, M); Their effects are now wired (see the later sections). Not modelled: the video-mode duel itself, Tyrell's Iron Bank, Golden PFx, Add-A-Ball award.
- Tickle (docs/06 c): the house pre-light shot counter (3 shots, award #0 75,000 +25,000), which shots count per house is not enumerated: not wired.
- Still PROVISIONAL: Greyjoy needing 4 Winter shots.
- Emulator facts (Game-of-Thrones docs/05): the left bumper adds 1,170 per scoring call; n x 1170 counts switch events, not a multiplier. Winter link still unconfirmed.

Open (owner/emulation): exact award growth, shot-to-switch mapping, Winter link, multiball triggers, coil timings,
Godot project (project.godot, GMC add-on, frame playback), service menu, audits, high scores, remaining modes.

## Godot display test (Xvfb, opengl3)
Checked: GMC connects to MPF, music plays on the music bus, slide vid004 plays the ROM video frames at 8x (1024x256 window
= 128x32 DMD). The frame on screen matches the source frame scaled 8x, so the scaling code is correct; the earlier
"cropped" view was just a close-up video frame. Not yet checked: text/score overlays and MPF Monitor on a real display.

## Combo X, swords, Wildfire (docs/10 part 1, H) - mode `combos` (got/combos.py)
- Combo X: 5 shots, follow-up lists from the ELF, 7 s window + 1.4 s grace, multiplier bumps per follow-up, ceiling 4 - difficulty(1) + swords, max 5 (6 in Hand). `got_combo_mult` is applied by AwardMode (houses) and to sword awards. NOT yet applied to multiball/Winter awards. Hand-of-the-King detection uses the mode key.
- Swords: lit by each completed house, Mystery/pop "Light Swords"; collected at the right ramp exit, weighted pick from data/swords.csv (copied by gen_config). The Mystery table (rulesheet) has no sword entry, so only the pop award and houses light swords.
- Wildfire: counter bumped through event `got_wildfire_bump` (pop +5); ram hit while running +10 and +2 s, 20 s timer, lit by pop "Light Wild Fire". `jackpot_value(n)` implements CalcJackpotValue but is not yet wired to the Blackwater award #8.
- Spinner, Lord of Light and video mode scoring followed in docs/10 part 2 (below).

## Spinner, Lord of Light, video mode (docs/10 part 2, H) - in got/combos.py
- Spinner: per spin V[p] + B (V starts 2,500, +150 per left-bank/single-drop/PFx bump, cap 250k; B by level table, reset per ball); level rises on the 1st and every 3rd left-bank completion when completed houses > level. The usual 970 per switch stays in scoring.yaml. Baratheon's own spinner logic is unchanged.
- Lord of Light: lit by bank completion rise (M gating), Mystery/pop "Light Lord of Light"; either outlane then adds a ball once (limit 10 per player, adjustment 123). Not modelled: timer-38 ability, adjustment 124.
- Video mode: superseded, the duel is built on docs/33 (see the last section). Old note: only the scoring was in; needs a Godot scene.

## DMD score slide (checked on Xvfb)
`game/slides/score.tscn` (MPFVariable score, comma separated) is played on `ball_started` and removed on `game_ended` (`config/display.yaml`). Headless display run: `mpf game . -c smoke_game -t` (fills the trough, starts a game, hits the spinner) with Godot `--rendering-driver opengl3` under Xvfb; the screenshot showed 10,410 after 3 spins (2,500 + 970 each, matching MPF). The slide must start after the player exists (not on `game_started`). Still plain text: no ROM font, no ball/player line, no mode text; ROM videos play over it.

## Mystery from docs/11 (H) - got/mystery.py, data config/rom/mystery_awards.csv
- All 40 ELF entries with the ROM gold prices and GoNoGo; the rulesheet price table is gone. Start needs flag lit, no multiball/house running, Hand/Iron/Wall not waiting and gold >= 300.
- Menu of 3 slots: 0 keep gold, 2 the most expensive eligible (ties: lower index), 1 a random eligible award of another category. Flipper buttons move the cursor (wrap), the action button confirms, 10 s auto-confirm (cursor starts on slot 2: M). Gold is `max(gold - price, 0)`, paid before the effect; audits come from the CSV.
- Effects wired: points (x combo multiplier, M), Light <house> (the throne starts lit houses first: our departure from Choose Your Battle), Wildfire, Bonus X, Wall jackpot/advance, swords, video mode start event, Arrows/Charge/Breach (absolute upper level), Light Lock (flag only), Golden Hand, Lord of Light, PF multiplier (next ram hit, M), Extra Ball, Hold Bonus, Winter (award x4 and start), button abilities (Baratheon = Lord of Light, Lannister = buy a multiplier 1,200-3,000, Martell = add a ball; the Lannister counter is fixed at 8).
- Stubs: Special, Super Jackpot 1-3x (sets `got_super_lit`, no consumer yet), Light Lock (no consumer), Grow Wall Jackpot (event only), Baratheon ability gate for Light Baratheon. Mystery argument = combo multiplier is M.

## Mystery DMD slide (checked on Xvfb: `-c smoke_mystery`, shows the top/middle/keep lines, then returns to the score)
`game/slides/mystery.tscn` shows the top and middle awards and "Keep gold" for 10 s from `got_mystery_menu` (tokens top/middle/keep, `config/display.yaml`); removed on `got_mystery_award`. The cursor is marked with `> ` (event `got_mystery_cursor` replays the slide with new tokens; not yet checked on a display).

## Ram Super Jackpot and Blackwater lock (docs/12, H)
- Lock: flag 36 (`got_lock_lit`) is cleared at ball start, lit by Mystery "Light Lock" and by the right two-bank completion (only while Blackwater was never played; later relights are M). A ball locks only when lit and no multiball runs: count + 1, gold +75 (+250 during Lannister), +5 Wildfire, flag cleared; the 3rd lock starts Blackwater. The lock switches no longer lock unlit.
- Ram Super Jackpot (`got_super_lit` 1-3, lit by Mystery): the next ram shot pays V x 6 x level + 10M (x playfield multiplier), V = `got_bw_jackpot` or, when Blackwater is not running, `jackpot_value(wildfire)`. No timeout; reset at ball start. Not wired: pop-award source (M), Blackwater's own in-multiball Super.

## Stubs closed
Grow Wall Jackpot (Mystery and pop award) raises the Wall award by its own bump; Special counts `got_specials` (a free-game credit is not paid, limits 53/55 not modelled); pop awards Light Lock, Bump Wall Jackpot, Special are wired. The pop-award list has no Super Jackpot entry (config/rom/pop_awards.json), so that "M" source is closed: Mystery only. Open: Blackwater's in-multiball Super Jackpot (ours uses the rulesheet 6x set total, not V x 6 x level + 10M).

## docs/13 wired (H unless noted)
- Blackwater (`BlackwaterMode`): rounds R = 1, 2, 3 (then stays 3), the 5 mask-0x6e shots (left loop, kickback, left ramp, right ramp, right loop) R times each (5, 10, 15 hits); a hit pays V x combo x R, V = `jackpot_value(wildfire)` fixed at the start; the last hit lights the Super (level R) for 20 s + 1.4 s; a ram shot pays V x 6 x R + 10M; expiry or collect starts the next round. The start's 10M and the upper-playfield SJ route (state machine 0..3) are not modelled.
- Special: adjustment 54 (0 credit event `got_special_credit`, 3 = 25M points, 4 extra-ball event, 1/2 nothing); adjustment 53 limit per player (over it: 25M); 55 (percentage) not modelled; no real credit/extra ball is added to the game yet.
- Two-bank lock: before the first Blackwater any hit lights it (difficulty <= 2), afterwards only a completed bank.
- Greyjoy: 5 shots (adds the kickback). Hand of the King: 2 sets when Greyjoy is complete, else 3. The ready byte persistence after a drain is M.
- M: the lock flag and the ram Super Jackpot are cleared once per player (InitializeFirstBall at the first ball), so they now persist across balls; if the ROM runs it every ball this is a one-line change in `Combos.mode_start`.

## Video mode duel (CFG gameplay, H scoring) - got/videomode.py, slides/videomode.tscn
Mystery "Video Mode nX" starts `modes/videomode`: 20 s, either flipper button hits the AI, the AI strikes every max(0.4, 1.6 - 0.2 x level) s, 10 health each (CFG: the ROM's health, damage and AI timing are not recovered). Win/lose ends it at once, timeout is a tie; the payout is the ROM's (docs/10 section 6) with level from `ad_video_mode_difficulty` (default 2). Slide shows "YOU n / FOE n" (not yet checked on a display; no graphics from the ROM's video-mode assets).

## docs/14 wired
- House tickle (H masks): three hits of each house's tickle shot light it (Targaryen kickback, Stark right ramp, Baratheon left bank, Lannister left ramp, Greyjoy left loop, Tyrell right 2-bank, Martell right loop), each hit pays 75,000 + 25,000 per earlier hit; the throne starts lit houses first. A completed house is unlit again. The "only while unlit/not in a multiball" gate is M.
- Button ability on completion (house_select_awards.csv): 1 Targaryen, 2 Stark, 3 Baratheon, 4 Lannister (8 uses), 5 Tyrell, 6 Martell, Greyjoy keeps the previous; the ability overrides the chosen-house power in `_action`. Use counters other than Lannister's are 1 per grant (M).
- Tyrell Iron Bank: 20M m - 18M + 75,000 m^2 min(c,120), c = sum of the armed combo multipliers x m (the ROM's c counts the 5 combo shots: M), then resets the combo and the playfield multiplier.
- Blackwater upper playfield: standup, left/right standup, centre standup, upper rollover = Super Jackpot (V x 6 + 10M; upper multiplier fixed at 1: M); steps 0-2 pay jackpots.
- Video duel: player health 3, AI 3-7 by level, damage 1 (heavy 2: 30% share is CFG).
- First-ball semantics: lock flag, ram SJ per player once (already so). Hand ready persists (the progression object is per player).
- Not done: Choose Your Battle / PASS / two stacked houses (our throne-starts-house departure stays), casual mode (adj 108), Greyjoy start-of-ball award, audits_meaning.csv (the 137 uncounted audits), Special extra-ball payout.
- Lannister completion pays 200 gold (400 if the Lannister ability was already set).

## Choose Your Battle, stacking, PASS (docs/14 section 10)
With lit houses (tickle or Mystery) the throne opens Choose Your Battle in `Combos` (no multiball, no running house): entries are each lit house, each pair of lit houses (stacking: two houses run together) and PASS (starts nothing, houses stay lit); flipper buttons move the cursor (wrap), the action button starts it (event `got_cyb_menu` carries the label; no slide yet). Winter Is Coming is offered with the start as before. With no lit house the throne still starts the next house (our departure; rom_differences). Not modelled: the ROM's entry set (M), casual mode's auto-pick.

## Casual mode and a settings fix
Casual mode (`ad_casual_mode`, default off): the right flipper starts a game in attract (`got.casual.Attract` subclasses MPF's attract), the house choice is skipped, and Choose Your Battle auto-picks its first entry. Fix: earlier code that read service-menu settings through a non-existent `setting_definitions` attribute silently used the defaults (Special award/limit, video-mode difficulty and permission); it now reads `settings._settings`, with a test.

Choose Your Battle slide (`slides/cyb.tscn`, `-c smoke_cyb`) checked on Xvfb: shows the highlighted entry (TARGARYEN) after three kickback shots and the throne.

## MPF Monitor on a display (Xvfb)
mpf-monitor 1.0.0 starts, connects to MPF 0.80.1 (port 5051) and shows its control window with the Devices/Monitor/Layers tabs. Needs: system libs `libegl1 libxkbcommon-x11-0 libxcb-cursor0 ...` (apt) and the `mpfmonitor/core/ui/*.ui` files, which are MISSING from both the PyPI wheel and the sdist of 1.0.0 (copy them from the upstream repo missionpinball/mpf-monitor `mpfmonitor/core/ui/` or install from git). The Playfield window (Toggle Playfield window) shows the VPX playfield picture from `game/monitor/monitor.yaml` ([docs/img/monitor_playfield.png](img/monitor_playfield.png)); the switch/light markers were not inspected. Run: Xvfb, `mpf game . -c smoke_game -t`, `mpf-monitor`, click the button (xdotool).

Special now pays for real: award 0 adds 1 to the machine var `credits`, award 4 adds an MPF extra ball (limit adj 'ad_extra_ball_limit', else 25M), award 3 and over-limit pay 25M points.

## Modes on the ROM state machines (2026-11-03, Game-of-Thrones docs/23-33; ROM wins over the VPX and the rulesheet)
Every mode below follows the extraction's state machine (H logic, M timings and lamp steps where marked in the docs) and has at least one test.
| Mode | Code | Source | What is in |
|---|---|---|---|
| Iron Throne | `got/iron.py` | docs/23 | states 0-4, castle choice, 22-castle tour, awards 15/16, audit 166 |
| Hand of the King | `got/hand.py` | docs/25 | states 1-4, 20 s bonus round, 16 s hurry-up, 3 sets (2 with Greyjoy), lamps 109-112/124, background screen |
| Wall | `got/wall.py` | docs/26 | ramps / orbits / kickback super cycle, 3 jackpots per phase, +175,000 bump, super +10M, background screen, lamps 119/121-123, audits 152/153 |
| Blackwater | `BlackwaterMode` | docs/27 | rounds R=1..3, 20 s + 93 tick super window, ram super, upper playfield chain, background screen with the seconds left |
| Castle | `got/castle.py` | docs/28 | main shots and standups pay award 12 (+250k, super +750k), rollovers pay the super (+10M), first super adds a ball |
| Winter Has Come | `WinterHasComeMode` | docs/29 B | horde (mask 239, 10 s add-back), boss triples (5 hits, combo+2, 10 s timers), super (3V+30M) x combo, frozen phase (8 s, left ramp thaws) |
| Winter Is Coming | `got/winter.py` | docs/29 A | each counted shot +75,000, third starts the 16 s hurry-up on the shot hit, reset to 4,000,000 after each end |
| Stark, Baratheon, Lannister, Greyjoy, Tyrell, Martell | `got/houses.py` | docs/30 | Baratheon ladder, Lannister red shots, Greyjoy +10 s per shot and double last payment, Tyrell run shots and 2-bank x3, Martell mini timer and hurry-up |
| Targaryen | `TargaryenMode` | docs/18, docs/30 s9 | three dragons; audits 178-183 checked |
| Mystery | `got/mystery.py` | docs/11, docs/31 | 3-slot menu, 10 s timer, cursor, keep gold (already matched docs/31) |
| Midnight Madness | `got/base.py` | docs/32 | only in the first minute after midnight, 10 minute wait for a ball, once per game, adjustment 152 |
| Video mode | `got/videomode.py` | docs/33 | 125 tick countdown, collision matrix, AI reactions, level = adjustment 132 + wins, loss (500,000 x level + 1,000,000) x n |
Display fixes found by the Xvfb pass (mode screens captured with `smoke_a` / `smoke_b`): total screens now show the mode total, "%dX SUPER JACKPOT IS LIT" shows the level, Wall / Hand / Blackwater / Castle publish their own live values.

## Choose your house + more ROM effects wired (2026-11-08)
Ball 1 now starts the ROM chooser (docs/18 1.2): hand animation (video 144) with the prompt, voice `vo_fn_choose_a_house`, `tune_shooter_groove`, flippers cycle RANDOM + 7 houses (voice `just_house_name`), the plunge or the action button confirms (`vo_fn_house_selected`). Adjustment 109: 0 players' choice (default), 1-7 fixed, 8 random. Undecided = random house (ROM house 9), no longer Stark. Captured on Xvfb (`-c smoke_choose`). House mode backgrounds (`tx_<house>_bg_live`: title left, score right) and the callers for winter grows, thawed/frozen, battering ram, hand/winter add time are wired. Audit: 121 of 234 ROM display effects still have no trigger (mostly hardware/service screens and easter eggs, plus the remaining *_BG layouts, credits, skill shot, tickle, Big Points awards): next.
