# VPX extraction (Agent B): Game of Thrones LE (Stern 2015) VPW 1.2.1

Source: `Game of Thrones LE (Stern 2015) VPW 1.2.1.vpx` (not committed). Extracted with Stern-SAM-Decryption
`tools/vpx/vpx_extract.py` (VPX 10.x: 175 images, 1,421 items, 28 collections, `script.vbs` 20,312 lines).

Outputs
- `game/monitor/monitor.yaml`, `game/monitor/playfield.jpg` (1904x4230): what MPF Monitor loads.
- `vpx/switches.csv`, `lights.csv`, `flashers.csv`: number, MPF name, VPX object, position (fractions of the picture).
- `vpx/script.vbs`: the table script, byte for byte (input for the VPX bridge agent).
- `vpx/overlay_small.png`: markers on the picture, for checking by eye. `vpx/build_monitor.py`: regenerates all of it.
- `vpx/shim/olefile.py`: minimal OLE2 reader, only because PyPI was unreachable (see below).

## What is different about this table
1. **No ROM, no PinMAME.** VPW wrote the whole game in VBScript. Its switch and lamp numbers (`sw1`..`sw84`, `STHit 9`,
   `Lampz.MassAssign(n)`) are the table's own and do not match Stern's, so `vpx_map.py` cannot join them to the MPF config
   (it reports 13 meaningless switches). Devices are placed by object name instead, from what the script does with them
   (`vpx/build_monitor.py` tables, each row has a note).
2. **No playfield picture.** `GameData IMAG` is `VLM.Nestmap2`, a 4096x4096 *light-map atlas* (Visual Pinball Light Mapper), not the
   playfield. The picture was rebuilt: the `playfield_mesh` primitive (M3CX/M3CI zlib vertex and index data, 8,928 vertices) was
   rasterised top-down (faces with normal z>0, rotated 180 degrees, UVs sampling Nestmap2), then brightened (the bake is the unlit
   "dark room" version; 99.5th percentile to white, gamma 0.55). Inserts line up with the VPX light positions. Weak spots: the upper-left
   (upper playfield plastics) is dark because those parts use other atlases, and the picture is the baked art (Stern/VPW), as Tron's.

## What was done without olefile/Pillow
Pillow was available (12.3.0). `olefile` was not and PyPI is unreachable, so `vpx/shim/olefile.py` (about 110 lines: header, DIFAT/FAT,
mini-FAT, directory tree, `listdir`/`openstream`/`exists`, `MAGIC`) was written and run with `sys.path` pointing at it. Pillow's FPX plugin
reads `olefile.MAGIC`, so the shim needs that constant. It extracted this 398 MB table in about 5 seconds.

## Counts
- Switches 78: 46 on table objects, 1 by hand (`s_kickback`), 7 trough (row, no objects), 24 cabinet strip (buttons, EOS, coins, tilt,
  service, plus `s_10_points`, `s_topper_dragon`, `s_dragon_home` which have no VPX object). The 8 dip switches are left out.
- Lights 67: 62 inserts from the table's `li*` lights, 5 button lamps on the strip. Only 6 have a name in the MPF config
  (`l_left/right_outlane`, `l_left/right_return_lane`, `l_extra_ball`, `l_shoot_again`) and the 5 buttons.
  The config's other lights are `l_lamp_NN` (generated from `lamps.csv`, unnamed); the table-data `lights.csv` (101 lights, `lt_*` names)
  is what the game really has, so the rest are named `l_<lt name>` (`in_mpf_config=no` in `lights.csv`). MPF ignores them until the config has them.
- Flashers 10 (`coil:` section, `f_` names). Two (`f_battering_ram`, `f_left_right_sling`) have no VPX flasher and are placed by hand;
  `f_sword_lock` and `f_throne` are uncertain.
- Not placed: GI (`gi*`), topper/backglass objects (off the picture), `l_right_ramp_combo` and the lamps with no match.

## Shot-to-switch mapping resolved from the script (`House(...).RegisterHit(h)`)
| House | Table shot | MPF switch |
|---|---|---|
| Stark | `sw42` right ramp switch (also `sw41` entrance) | `s_right_ramp_exit` |
| Lannister | `sw39` left ramp switch (arms lock switch `sw48`) | `s_left_ramp_exit` |
| Greyjoy | `LOrbitSW30` left orbit (after `sw30a`) | `s_left_loop` |
| Martell | `ROrbitsw31` right orbit | `s_right_loop` |
| Baratheon | LoL 3-bank complete (`Target7..9`, `DTHit 1..3`); spinner builds value | `s_3_bank_drop_tgt_*`, `s_left_spinner` |
| Tyrell | wildfire targets `Target43/44` | `s_right_2_bank_top/bottom` |
| Targaryen | `Kicker37` castle wall kicker (upper playfield) | none: the MPF config has no such switch |

Each house needs 3 hits of its shot to qualify (`QualifyCount < 3`, matches `house_shots_to_complete`). Battle modes: Stark ramps build value and
an orbit finishes; Baratheon spinner then 3-bank; Lannister gold targets light shots, 5 shots finish; Greyjoy `GreyjoyMask = 218` = Stark,
Lannister, Greyjoy, Martell, Targaryen shots, 15 s reset per shot; Tyrell 2-bank, 3 hits; Martell 3 orbits in a row, left ramp collects.
`rules.yaml` houses stark, baratheon, greyjoy, martell now use these (modes regenerated); lannister, tyrell, targaryen unchanged.

## Check by eye (owner)
1. `vpx/overlay_small.png`: green rings = switches, coloured dots = lights, magenta squares = flashers.
2. Uncertain: lock order `s_lock_1..3` (sw46/47/48), `f_sword_lock`, `f_throne`, `u_p_battle_mode_1..4`, upper-left darkness in the picture.
3. Targaryen shot has no MPF switch: the castle kicker; add one to the config (or map it to the upper-playfield switch you prefer).
