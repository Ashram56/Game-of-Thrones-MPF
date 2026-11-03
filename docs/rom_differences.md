# Departures from the ROM, and what is not built

Updated 2026-11-03. No reference traces or PinMAME exist for Spike 1, so everything is checked against the extraction
(Game-of-Thrones `docs/`, `data/*.csv`, ROM wins over the VPX table) and by MPF tests, not against the real game.
Confidence per rule: `game/config/rules.yaml` (H table/constant, M constants plus names, L inferred, CFG not recovered).

## Departures (built differently from the ROM)

| # | Area | ROM | Here | Why |
|---|---|---|---|---|
| 1 | House start with no lit house | Choose Your Battle always decides | The throne starts the next incomplete house; with lit houses Choose Your Battle opens (single, stacked pair, PASS) | Entry set of the ROM menu is M |
| 2 | Service menu | The ROM's own menu | `got.servicemenu` on the four service buttons: audits (207 ROM counters), adjustments (159, edit and save), switch test, coil test, drawn on the DMD | ROM screen layouts, coin and utility pages not rebuilt |
| 3 | DMD effects | Procedural `def_*` effects, ROM font and text layout | Text screens drawn by Godot slides (score with ball/player, attract pages, credits, high scores, initials, match, game over, Mystery, Choose Your Battle, video duel); ROM videos play for the 9 extracted clips | Effect table and font not decoded |
| 4 | Attract, credits, high scores, match | ROM screens and rules | Mine (CFG): pages every 4 s, 1 coin = 1 credit (adj 65 limit, adj 66 free play), initials by flippers + Start, tables 75/50/40/30/20 M from docs/03, match draw from adj 61 | Screens and match odds not decoded |
| 5 | Lamps, flashers | ROM lamp and flasher effects (`lef_*`) | The ROM's 101 named lights; attract sweep, GI, Start, Shoot Again, house sigils, flasher pulses on switch events (CFG choreography) | Effects not decoded |
| 6 | Coils | Per-coil drive times | From data/coil_timing.csv (call-site pulse H, node reflex M); the shaker is 100 ms (table 1000) | Held coils (diverter, sword, lock hold levels) not modelled |
| 7 | Video mode duel | ROM duel (docs/33) | Rules and collision matrix as the ROM; M: sprite width (16 px), how long an attack or parry lasts, the AI's idle thresholds, knockback recovery; the Godot duel screen still draws from the health values only | Not recovered |
| 8 | Iron Bank, Greyjoy/Lannister/Tyrell/Baratheon/Martell abilities | ROM routines | Built from `house_select_awards.csv` and docs/14; Iron Bank `c` is M; no dragon waves | Partly M |
| 9 | Hardware | Spike 1 node bus | smart_virtual and a virtual overlay only | Different platform |

## Built since the first version (no longer missing)
Houses and multiballs with ROM scoring tables, Combo X, swords, Wildfire, spinner, Lord of Light, Mystery (40 entries, 3-slot menu),
Blackwater rounds and Super Jackpots, lock and ram Super Jackpot, Special (credit or extra ball), Tickle, button abilities,
casual mode, Wall, Castle, Hand of the King, Iron Throne, Midnight Madness, bonus, tilt, ball save, extra balls.

## Not built
- About 100 of the 207 audit counters (score and game-time histograms, ball search, fixture, remaining mystery light counters); the ROM service menu screen layouts. Counted: flippers, shots, multiballs, battles, house select, mystery awards, coins, Pict-O-Pops awards, video mode results, matches.
- Display effects with runtime values or lines without a known position (they fall back to a Godot font); the 'ready' music states and `_spacer` tunes; (video duel graphics are in: ROM sprites, labels, health bars). Castle Collection and the Iron Throne victory lap do not exist in the ROM (docs/17 of Game-of-Thrones): not missing.
- Tyrell's +1 return lane at the house start; the dragon fights are built from docs/18 (three dragons, Drogon HP and banked waves) with the lit-shot masks simplified (M); Wildfire details beyond docs/10.
- Real-machine checks: nothing ran on a Spike 1 board.


Built since: background music by state from `music_stack.csv` (`got.music`); ROM bitmap fonts at the ROM's x/y on 162 text effects (`scripts/dmd_text.py`, `dmd_text_pages.gd`; multi-screen effects rotate every 1.2 s).

## Audits not counted (decided 2026-11-03)
The ROM itself never chalks mystery ARROWS, CHARGE and BREACH separately (all chalk 118), nor 170 (castle super jackpot) and 171 (house select Targaryen chalks 172): they stay at 0 here too. Fixture (198-203) and auto-play (204-206) audits are written by a fixture tool outside the game binary; ball search counters wait for the extraction's data. Histogram and time audits follow docs/19.

## Text drawn with the ROM fonts (2026-11-03)
Score, attract, mystery and choose-your-battle screens now use the ROM bitmap fonts (scripts dmd_score.gd, dmd_labels.gd); the score takes the largest digit font (19-26) that fits 128 px (the ROM's own size table is not applied yet). Text placement follows docs/21 of the extraction (per-glyph advance, dx/dy, font spacing, centre anchor), so "OUTLANE BALL SAVE" (font 7, x=39) is 68 px wide and fits; text is still clamped on screen as a safety.

## Ball search (2026-11-03, docs/20)
MPF's ball search replaces the ROM's: 10 s without activity, then slingshots, elevator popper, throne, pops one after another (300 ms apart, the ROM pulses 64 ms); flippers and the lock device are excluded; a failed search is a virtual recovery (new ball from the trough, adjustment 98 default). Audits 39 and 40 count `ball_search_started` / `ball_search_failed`. Not modelled: the ROM's delay_search callers (video mode, choreos, Madness), the drop-target and gate moves of step 8, kickbacks.

## Skill shot, top lanes and initials entry (docs/22, 2026-11-03)
The ROM's "SKILL SHOT" display needs flag 27, which nothing sets in 1.37.0, so it is not built (dead code, medium confidence). Top lanes follow the ROM: 5,000 for a newly lit lane, 500 if already lit, a flipper swaps the lanes, both lit = 25,000 and +1 bonus X. Initials entry: alphabet A-Z plus SPACE, BACKSPACE and END, 30 s timer reloaded to 15 s at each input, default initials when nothing is typed (SSR, XAQ, GGF, JMR, T), cursor sounds 278-280 and tune_hstd. Not done: the 1.45 s / 3.2 s launch windows that route a fast right-loop shot to the elevator, the 13 champion tables, the ROM's entry screen layout (fonts and alphabet strip), 10-letter initials (adjustment 95).

## Mode champion tables (docs/22 2b, 2026-11-03)
12 tables (7 houses, Winter Is Coming, Winter Has Come, Hand of the King, Iron Throne, Midnight Madness) with the ROM default initials and scores (adjustments 134-145). A player's best score in a mode is the points gained while the mode ran (inferred). The entry runs after the main high-score entry. Tracked now: the AwardMode modes (houses, Hand, Iron Throne, Winter Has Come); the champion attract pages follow the high scores. Winter Is Coming uses the best hurry-up award, Midnight Madness the points gained while it ran.

## Iron Throne: ciron state machine (got.iron)
Iron Throne runs the ROM's state machine (docs/23 of Game-of-Thrones, H states/transitions, M multipliers): choose castle, defeat it with the 7 shot groups, battering-ram super (+1 ball), King's Landing final ram, then the 22-castle tour with random 3-group masks. The 3-bank counts as one shot group on any of its three drops, the right 2-bank on either target (the ROM's individual-drop bits are not modelled). Not modelled: state 3 with one ball returns to state 0 with an empty mask and the mode simply waits for the drain; when all castles were taken before a new start the mask is refilled (inferred); lamp effects 89/91/92 and audits 164/166 only partly.

## Hand of the King: chand state machine (got.hand)
The Hand runs the ROM's state machine (Game-of-Thrones docs/25, docs/24; H logic, M timer durations): single shots (the shot groups of the completed houses, all seven with Baratheon, two hits each with Martell), ram super jackpot, bonus round (Stark bit, 20 timer seconds of free shots), 3 sets (2 with Greyjoy), then the 16 s super-jackpot hurry-up, which loops back to set 1; the mode ends only when the balls drain, there is no +10 s add-time (no ROM caller). The return lanes no longer count as Hand shots. Not modelled: the bonus-round alternate increment fields (75,000 / 750,000, M), lamps 109-112/124 and the def_hand_bg state screens, the ball-save / balls-in-play-at-start rules of chand::Start beyond the existing multiball configuration.

## Modes rebuilt on the ROM state machines (2026-11-03)
Wall, Blackwater, Castle, Winter Has Come, Winter Is Coming, six houses, Midnight Madness and the video duel now follow Game-of-Thrones docs/26-33. Remaining departures:
- Winter Is Coming: which counted shots are frozen (a lit house's tickle shot, `AddFrozenShot`) is not enforced; any mode shot counts (M).
- Castle: the upper multiplier is fixed at 1 (M); effect 160 (loop award) has no caller in the ROM and is not built.
- Blackwater: Wildfire, lock and the upper-playfield chain as docs/12-14; the intro delay (proc 228) that ignores shots is not modelled.
- Wall: the +20,000,000 super bonus of the house-select instance and the 218 tick grace are not modelled; jackpot/super screens use the generic layouts.
- Winter Has Come: sound/lamp steps and the walking-animation background are not built; the accumulator `AddSuperJackpot` has no reader in the ROM and is not paid.
- Houses: the Greyjoy bonus mask (first hit only bumps) is not enforced; lamp effects 29-33 internals are not built.
- Video mode: see departure 7.
