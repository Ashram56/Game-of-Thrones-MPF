# Learnings for Stern-SAM-Decryption (not filed there; list only)

1. A game with no emulator or traces (Spike 1 GOT) can still be recreated config-first: keep one `rules.yaml` with a
   confidence tag per value (H/M/L/CFG) and generate mode YAML from it; a test cross-checks it against the extraction CSVs.
2. Adjustments store signed values as u32 (min 4294967236 = -60 for music attenuation): convert before building settings.
3. Where PyPI/apt are unreachable, put the pure rules in an MPF-free module so pytest still covers them; test YAML with a
   duplicate-key loader (PyYAML merges duplicates silently, see playbook s6).
4. Playbook s6 assumes the asset repo as a submodule; for Spike 1 the data tables sit in a sibling repo (env GOT_DATA).
