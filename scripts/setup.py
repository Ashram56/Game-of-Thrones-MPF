#!/usr/bin/env python3
"""Prepare the game's workspace: a Python environment with MPF, the generated MPF config, the media, the GMC add-on.
Standard library only. This is the game's own build step (the convention of MPF-Godot-Packaging
`common/games/build_game_package.py`); it makes every generated file the package needs, so the platform generates nothing.

  python3 scripts/setup.py --assets DIR [--data DIR] [--no-monitor] [--skip-venv] [--skip-media] [--dry-run]

--assets DIR   the ROM-derived assets (DMD frames `dmd/`, sounds `audio/`; env GOT_ASSETS). Copyrighted: supplied by the owner
               (Game-of-Thrones repository's extraction), never committed here. Without it the media steps are skipped
               with a warning and the package is incomplete (`scripts/run.py --check` says what is missing).
--data DIR     the extraction's data tables (`data/*.csv` of Ashram56/Game-of-Thrones; env GOT_DATA). Default: ../Game-of-Thrones/data,
               else a shallow clone of GOT_DATA_REPO (default https://github.com/Ashram56/Game-of-Thrones) in .cache/.
Steps (each skipped when in place, so it is safe to re-run): venv + pins, MPF Monitor (+ its missing .ui files),
scripts/gen_config.py, scripts/gen_media.py, the GMC add-on (platform patched copy if MPF-Godot-Packaging is next to this
folder or MPF_GODOT_PACKAGING says where; else GMC v1.0.0 + scripts/gmc_patch.py). Godot itself is the platform's
(`python -m mpf_godot setup`); the Godot import is made by the bundler, not here.
"""
import argparse
import os
import shutil
import subprocess
import sys
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = os.path.join(ROOT, ".venv")
# Pins, each with its reason (MPF-Godot-Packaging fixes/mpf/):
REQUIREMENTS = ["mpf==0.80.1",
                'ruamel.yaml.clib==0.2.14; python_version < "3.13"',    # 0.2.15 stops `mpf` when MPF Monitor is installed
                "pyyaml"]                                              # scripts/gen_config.py, gen_media.py
MONITOR_REQUIREMENTS = ["mpf-monitor==1.0.0"]
MONITOR_UI_URL = "https://raw.githubusercontent.com/missionpinball/mpf-monitor/v1.0.0/mpfmonitor/core/ui/"
MONITOR_UI_FILES = ("events_table.ui", "inspector.ui", "searchable_table.ui", "searchable_tree.ui")   # absent from the PyPI wheel
GMC_GIT = "https://github.com/missionpinball/mpf-gmc"
GMC_TAG = "v1.0.0"


def say(msg):
    print(msg, flush=True)


def run(cmd, dry, **kw):
    say("   $ " + " ".join(cmd))
    if not dry:
        subprocess.check_call(cmd, **kw)


def venv_python():
    return os.path.join(VENV, "Scripts" if os.name == "nt" else "bin", "python" + (".exe" if os.name == "nt" else ""))


def step_venv(a):
    say("1. Python environment (.venv): " + ", ".join(REQUIREMENTS))
    if not os.path.exists(venv_python()):
        run([sys.executable, "-m", "venv", VENV], a.dry_run)
    run([venv_python(), "-m", "pip", "install", "--quiet", "--upgrade", "pip"], a.dry_run)
    reqs = REQUIREMENTS + ([] if a.no_monitor else MONITOR_REQUIREMENTS)
    run([venv_python(), "-m", "pip", "install", "--quiet"] + reqs, a.dry_run)
    if not a.no_monitor:
        step_monitor_ui(a)


def step_monitor_ui(a):
    """mpf-monitor 1.0.0 on PyPI lacks mpfmonitor/core/ui/*.ui (fixes/mpf-monitor/missing-ui-files.md): add the missing ones."""
    if a.dry_run:
        say("   (would add the missing MPF Monitor .ui files from the v1.0.0 tag)")
        return
    out = subprocess.run([venv_python(), "-c", "import os, mpfmonitor; print(os.path.dirname(mpfmonitor.__file__))"],
                         capture_output=True, text=True)
    if out.returncode:
        say("   MPF Monitor is not installed, skipped")
        return
    ui = os.path.join(out.stdout.strip(), "core", "ui")
    os.makedirs(ui, exist_ok=True)
    for name in MONITOR_UI_FILES:
        dst = os.path.join(ui, name)
        if os.path.exists(dst):
            continue
        with urllib.request.urlopen(MONITOR_UI_URL + name, timeout=60) as r:
            data = r.read()
        if b"<ui" not in data[:300]:
            raise SystemExit("MPF Monitor's %s is not a Qt Designer file" % name)
        with open(dst, "wb") as f:
            f.write(data)
        say("   added " + name)


def find_data(a):
    for d in (a.data, os.environ.get("GOT_DATA"), os.path.join(ROOT, "..", "Game-of-Thrones", "data")):
        if d and os.path.isfile(os.path.join(d, "swords.csv")):
            return os.path.abspath(d)
    repo = os.environ.get("GOT_DATA_REPO", "https://github.com/Ashram56/Game-of-Thrones")
    cache = os.path.join(ROOT, ".cache", "Game-of-Thrones")
    if not os.path.isdir(cache):
        run(["git", "clone", "--depth", "1", repo, cache], a.dry_run)
    return os.path.join(cache, "data")


def step_config(a):
    data = find_data(a)
    say("2. MPF config and modes from %s (scripts/gen_config.py)" % data)
    run([venv_python() if not a.dry_run and os.path.exists(venv_python()) else sys.executable,
         os.path.join(ROOT, "scripts", "gen_config.py"), "--data", data], a.dry_run)
    return data


def step_media(a, data):
    assets = a.assets or os.environ.get("GOT_ASSETS")
    if a.skip_media or not assets:
        say("3. Media SKIPPED (%s): the package is incomplete until scripts/setup.py --assets DIR runs"
            % ("--skip-media" if a.skip_media else "no --assets / GOT_ASSETS"))
        return
    say("3. Sounds and DMD frames from %s (scripts/gen_media.py)" % assets)
    run([venv_python() if os.path.exists(venv_python()) else sys.executable, os.path.join(ROOT, "scripts", "gen_media.py"),
         "--assets", assets, "--data", data], a.dry_run)


def step_gmc(a):
    gmc = os.path.join(ROOT, "game", "addons", "mpf-gmc")
    say("4. GMC add-on (game/addons/mpf-gmc)")
    platform = os.environ.get("MPF_GODOT_PACKAGING") or os.path.join(ROOT, "..", "MPF-Godot-Packaging")
    if os.path.exists(os.path.join(gmc, "plugin.cfg")):
        say("   in place")
    elif os.path.isdir(os.path.join(platform, "mpf_godot")):
        run([sys.executable, "-m", "mpf_godot", "addons", os.path.join(ROOT, "game")], a.dry_run, cwd=platform)
    else:
        tmp = os.path.join(ROOT, ".cache", "mpf-gmc")
        if not os.path.isdir(tmp):
            run(["git", "clone", "--depth", "1", "--branch", GMC_TAG, GMC_GIT, tmp], a.dry_run)
        if not a.dry_run:
            shutil.copytree(os.path.join(tmp, "addons", "mpf-gmc") if os.path.isdir(os.path.join(tmp, "addons")) else tmp,
                            gmc, ignore=shutil.ignore_patterns(".git"))
    run([sys.executable, os.path.join(ROOT, "scripts", "gmc_patch.py"), gmc], a.dry_run)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--assets")
    ap.add_argument("--data")
    ap.add_argument("--no-monitor", action="store_true")
    ap.add_argument("--skip-venv", action="store_true")
    ap.add_argument("--skip-media", action="store_true")
    ap.add_argument("--skip-gmc", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, change nothing")
    a = ap.parse_args()
    if not a.skip_venv:
        step_venv(a)
    data = step_config(a)
    step_media(a, data)
    if not a.skip_gmc:
        step_gmc(a)
    say("Done. Check: %s scripts/run.py --check    Run: %s scripts/run.py"
        % (os.path.relpath(venv_python(), ROOT), os.path.relpath(venv_python(), ROOT)))


if __name__ == "__main__":
    main()
