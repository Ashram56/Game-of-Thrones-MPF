# Departures from the ROM

No reference traces exist, so these are departures from the *spec*; every item also lists what is simply not built.

| # | Area | ROM (spec) | Here | Why |
|---|---|---|---|---|
| 1 | House start | Choose Your Battle (flag 46) selects lit houses; timer 23 (3 s, +8 s per press, max 20 s) | The throne switch starts the next incomplete house | Selection flow not built |
| 2 | House shots | ROM-defined shot logic per house (M) | `shots` switch lists in rules.yaml (L), 3 shots complete a house (CFG) | Shot mapping not extracted |
| 3 | Award growth | `BumpAward` increments computed at run time; some values only in 03 s7 | Bump on every shot, caps from 03 s7; Targaryen, Winter Is Coming, Hand, Madness growth = 0 (CFG) | Needs emulation (docs/05-emulation.md) |
| 4 | Hurry-ups | Decay computed by `CalcHurryUpDecValue` | Linear decay helper exists, not wired into modes | Amounts not recovered |
| 5 | Multiball start | Blackwater by locks, Castle by upper-playfield levels, Wall by left 3-bank, Madness by ? | Modes start only by `start_mode_<key>` events (progression events `got_ready_*` are posted) | Triggers are M/L |
| 6 | Multiballs | Super jackpots, sub-modes (wildfire, freeze, horde) | One jackpot award per mode, ball count 3 (CFG), ball save from the ROM defaults | Scope |
| 7 | Not built | Lannister gold, playfield multipliers, combos, mystery, video mode, Lord of Light, swords, bonus, match, high scores, service menu, audits, credits | - | Scope; settings.yaml has the 159 adjustments for the menu |
| 8 | Operator settings | Adjustments drive the rules | Static defaults in YAML; adjustments exist as MPF settings only | Lean first build |
| 9 | Coils | Per-coil Spike 1 drive times | 25 ms pulse for all (CFG), shaker 100 ms | Timing not decoded |
| 10 | Hardware | Spike 1 node bus | smart_virtual only; no P-ROC route for Spike 1 | Different platform |
| 11 | DMD | Procedural display effects (`def_*`) | Slides show the first frame of selected `play_video` ranges; frame playback not wired (fps CFG 20) | Display effect table not decoded |
