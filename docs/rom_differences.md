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
