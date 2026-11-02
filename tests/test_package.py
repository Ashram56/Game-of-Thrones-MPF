"""The repository follows the platform's game-bundle contract (nothing is built here)."""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEYS = {"id", "name", "description", "icon", "game_dir", "git_tracked", "git_exclude", "copy", "optional", "never",
        "never_names", "format", "mpf", "dmd", "addons", "settings", "import_seed", "force_vram", "platform_addons", "requires", "run", "options", "pup",
        "keep_on_update", "monitor", "profiles", "gozen", "extra", "source_commits", "precheck"}


def load(name):
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return json.load(f)


def test_spec_keys_and_ids():
    spec, pkg = load("bundle_spec.json"), load("mpf-package.json")
    assert set(spec) <= KEYS
    assert spec["format"] == 2 and "run" not in spec and "env" not in spec.get("requires", {})
    assert spec["mpf"]["configs"] and spec["mpf"]["hardware"]["virtual"]
    assert spec["id"] == pkg["id"]


def test_no_cabinet_data_is_copied_or_tracked():
    spec = load("bundle_spec.json")
    assert not set(spec["copy"]) & set(spec["never"])
    tracked = subprocess.run(["git", "-C", ROOT, "ls-files"], capture_output=True, text=True).stdout.split()
    for p in tracked:
        assert not p.startswith(("game/data/", "game/logs/", "game/audits/")), p
        assert not p.endswith((".local.cfg", "machine_vars.yaml")), p


def test_scripts_compile():
    for s in ("run.py", "setup.py", "gmc_patch.py"):
        subprocess.run([sys.executable, "-m", "py_compile", os.path.join(ROOT, "scripts", s)], check=True)
