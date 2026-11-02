# Preparing a game image (contract only)

Rules from [MPF-Godot-Packaging](https://github.com/Ashram56/MPF-Godot-Packaging) (`common/games/README.md`, `platforms/game-bundles.md`) and
Stern-SAM-Decryption `agents/packaging.md`, applied here. This repository does **not** build the image or archive.

| Contract item | Here |
|---|---|
| `bundle_spec.json` (checked by `mpf_godot.bundle.validate_spec`, no problems) | root; id `game-of-thrones-mpf`; copies `game/config/rom`, `game/sounds`, `game/images`, `scripts/run.py`; `never` lists cabinet data |
| `mpf-package.json` (id equals the spec id) | tools `git`, setup `python3 scripts/setup.py --no-monitor` |
| Complete package before the build | `scripts/setup.py` generates config, media and the GMC add-on; nothing is generated at start |
| Start command and check | `python3 scripts/run.py` (needs Godot and display), `python3 scripts/run.py --check` |
| Patched GMC (rule 5) | `scripts/gmc_patch.py` skips an add-on already patched by the platform (`# mpf-godot fix`) |
| No cabinet data | `game/data`, audits, logs, `*.local.cfg` are never tracked or copied (tested in `tests/test_package.py`) |

Open before a real image: the ROM-derived sounds/DMD frames must be present in the builder's `GOT_ASSETS`; a Godot import pass and a run on the
target (the tool does not check that the game runs); MPF Monitor `.ui` files are fetched by `setup.py` (platform fix `fixes/mpf-monitor`).
