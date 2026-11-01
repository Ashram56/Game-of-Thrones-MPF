# Learnings for Stern-SAM-Decryption (not filed there; list only)

1. A game with no emulator or traces (Spike 1 GOT) can still be recreated config-first: keep one `rules.yaml` with a
   confidence tag per value (H/M/L/CFG) and generate mode YAML from it; a test cross-checks it against the extraction CSVs.
2. Adjustments store signed values as u32 (min 4294967236 = -60 for music attenuation): convert before building settings.
3. Where PyPI/apt are unreachable, put the pure rules in an MPF-free module so pytest still covers them; test YAML with a
   duplicate-key loader (PyYAML merges duplicates silently, see playbook s6).
4. Playbook s6 assumes the asset repo as a submodule; for Spike 1 the data tables sit in a sibling repo (env GOT_DATA).
5. VPX (Agent B), tables with no ROM (VPW GoT 1.2.1): the script is the whole game, switch/lamp numbers are the table's own (sw1..sw84, Lampz 1..82),
   so `vpx_map.py` finds only meaningless numbers. Place devices by object name and read what each `_Hit` does (`House.RegisterHit` etc.). That also
   yields the shot-to-switch mapping for free. Worth a note in agents/vpx_extraction.md.
6. VPX tables baked with VLM (Visual Pinball Light Mapper) have `GameData IMAG` = a `VLM.NestmapN` light-map atlas, not a playfield. Rebuild the picture
   by rasterising the `playfield_mesh` primitive (M3CX/M3CI are zlib; 32-byte vertices x y z nx ny nz u v; table is rotated 180 degrees) and sampling the atlas
   with its UVs; brighten (the bake is the unlit room). `vpx_extract.py` should detect `VLM.` and do this (script: vpx/render_playfield.py in this repo).
7. No olefile and no PyPI: a ~110-line pure-Python OLE2 reader (vpx/shim/olefile.py here) is enough for vpx_extract.py; Pillow needs `olefile.MAGIC` too.
   vpx_extract.py could fall back to it. Also: Pillow was installed even though the brief said not; check `import PIL` first.
8. VPX object names differ in case between items.json and the script (target7 vs Target7): match case-insensitively in vpx_map.py.
9. The light list the MPF generator used (lamps.csv, `l_lamp_NN`) is not the light list of the Spike-1 game (lights.csv, `lt_*`, 101 entries). A monitor can only
   be named by the former; generate lights.yaml from lights.csv when the data has it.
