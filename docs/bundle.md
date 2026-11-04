# Preparing a game image (contract only, bundle format 2)

Rules from [MPF-Godot-Packaging](https://github.com/Ashram56/MPF-Godot-Packaging) (`common/games/README.md`, `platforms/game-bundles.md`) and
Stern-SAM-Decryption `agents/packaging.md`, applied here. This repository does **not** build the image or archive.

| Contract item | Here |
|---|---|
| `bundle_spec.json` (`format: 2`; `mpf_godot.bundle.validate_spec` and `mpf_contract.problems` report nothing) | root; id `game-of-thrones-mpf`; `mpf.configs` `config`, hardware `virtual` = `hw_virtual`; copies `game/config/rom`, `game/sounds`, `game/images`; `never` lists cabinet data; no `run`, no `requires.env` (the platform runs `mpf_godot run`) |
| `mpf-package.json` (id equals the spec id) | tools `git`, setup `python3 scripts/setup.py --no-monitor` |
| Complete package before the build | `scripts/setup.py` generates config, media and the GMC add-on; nothing is generated at start |
| Start | the platform's `mpf_godot run`; `scripts/run.py` is only the one-line start on a PC and is never called by the platform (`--check` for a local check) |
| Patched GMC (rule 5) | `scripts/gmc_patch.py` skips an add-on already patched by the platform (`# mpf-godot fix`) |
| No cabinet data | `game/data`, audits, logs, `*.local.cfg` are never tracked or copied (tested in `tests/test_package.py`) |

The ROM-derived sounds, DMD frames, fonts and text pages are committed in `game/sounds` and `game/images` (owner decision 2026-11-04, the repository is to be made private); `scripts/gen_media.py` regenerates them from `GOT_ASSETS`. Open before a real image: a Godot import pass and a run on the
target (the tool does not check that the game runs); MPF Monitor `.ui` files are fetched by `setup.py` (platform fix `fixes/mpf-monitor`).

## Faster test bundles
MPF-Godot-Packaging PR #82 adds `--fast` to `python -m mpf_godot bundle`: the staged tree and the Godot import stay in `OUT/cache/` and only what changed is synced and reimported (warm rebuild about 16 s instead of about 4 min). For test bundles: `python -m mpf_godot bundle bundle_spec.json --target all --label test --fast --out dist`, always with the same `--out` folder. Nothing changes in this repository.
