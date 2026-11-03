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
| 7 | Video mode duel | ROM duel | 20 s, player health 3, AI 3-7 by level, damage 1 (heavy 2 at 30 %, CFG); text only | Health, AI timing, graphics not recovered |
| 8 | Iron Bank, Greyjoy/Lannister/Tyrell/Baratheon/Martell abilities | ROM routines | Built from `house_select_awards.csv` and docs/14; Iron Bank `c` is M; no dragon waves | Partly M |
| 9 | Hardware | Spike 1 node bus | smart_virtual and a virtual overlay only | Different platform |

## Built since the first version (no longer missing)
Houses and multiballs with ROM scoring tables, Combo X, swords, Wildfire, spinner, Lord of Light, Mystery (40 entries, 3-slot menu),
Blackwater rounds and Super Jackpots, lock and ram Super Jackpot, Special (credit or extra ball), Tickle, button abilities,
casual mode, Wall, Castle, Hand of the King, Iron Throne, Midnight Madness, bonus, tilt, ball save, extra balls.

## Not built
- About 100 of the 207 audit counters (score and game-time histograms, ball search, fixture, remaining mystery light counters); the ROM service menu screen layouts. Counted: flippers, shots, multiballs, battles, house select, mystery awards, coins, Pict-O-Pops awards, video mode results, matches.
- Display effects with runtime values or lines without a known position (they fall back to a Godot font); the 'ready' music states and `_spacer` tunes; graphics for the video duel; Castle Collection; the Iron Throne victory lap.
- Greyjoy start-of-ball award; Wildfire details beyond docs/10; dragon waves and Stark/Targaryen refinements beyond docs/14.
- ROM coil times and lamp/flasher choreography (CFG values above).
- Real-machine checks: nothing ran on a Spike 1 board.


Built since: background music by state from `music_stack.csv` (`got.music`); ROM bitmap fonts at the ROM's x/y on 162 text effects (`scripts/dmd_text.py`, `dmd_text_pages.gd`; multi-screen effects rotate every 1.2 s).
