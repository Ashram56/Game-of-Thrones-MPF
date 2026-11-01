"""Static validation (MPF is not installed in the build sandbox): YAML parses, no duplicate keys, every device
reference resolves, generated files are current, rules.yaml matches the extraction CSVs when they are available."""
import csv
import glob
import os
import re
import subprocess
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "game")
DATA = os.environ.get("GOT_DATA", os.path.join(ROOT, "..", "Game-of-Thrones", "data"))
sys.path.insert(0, GAME)
from got.rules_core import Award, ExtraBalls, Progression, load_rules  # noqa: E402


class _Loader(yaml.SafeLoader):
    pass


def _no_dups(loader, node):
    seen = set()
    for k, _ in node.value:
        key = loader.construct_object(k)
        assert key not in seen, "duplicate key %r" % (key,)
        seen.add(key)
    return loader.construct_mapping(node)


_Loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dups)


def load(path):
    with open(path, encoding="utf-8") as f:
        text = f.read()
    assert text.startswith("#config_version=6"), path
    return yaml.load(text, _Loader)


def all_yaml():
    return glob.glob(GAME + "/config/**/*.yaml", recursive=True) + glob.glob(GAME + "/modes/**/*.yaml", recursive=True)


def merged_config():
    cfg = {}
    for p in glob.glob(GAME + "/config/**/*.yaml", recursive=True) + glob.glob(GAME + "/modes/**/*.yaml", recursive=True):
        if p.endswith("rules.yaml") or "hw_" in p:
            continue
        for k, v in load(p).items():
            if isinstance(v, dict):
                cfg.setdefault(k, {}).update(v)
    return cfg


def test_yaml_parses_without_duplicates():
    for p in all_yaml():
        if p.endswith("rules.yaml"):
            yaml.load(open(p, encoding="utf-8").read(), _Loader)
        else:
            load(p)


def test_references_resolve():
    c = merged_config()
    sw, coils = set(c["switches"]), set(c["coils"])
    for name, bd in c["ball_devices"].items():
        for s in re.split(r"\s*,\s*", bd["ball_switches"]) + [bd.get("jam_switch", "")]:
            assert not s or s in sw, (name, s)
        assert bd["eject_coil"] in coils
    for name, f in c["flippers"].items():
        assert f["main_coil"] in coils and f["activation_switch"] in sw, name
    for name, a in c["autofire_coils"].items():
        assert a["coil"] in coils and a["switch"] in sw, name
    assert c["tilt"]["tilt_warning_switch"] in sw and c["tilt"]["slam_tilt_switch"] in sw
    rules = load_rules()
    for h in rules["houses"]:
        for s in h["shots"]:
            assert s in sw, (h["key"], s)
    for m in rules["multiballs"]:
        for s in m["jackpot_switches"]:
            assert s in sw, (m["key"], s)


def test_modes_listed_and_exist():
    cfg = load(GAME + "/config/config.yaml")
    for m in cfg["modes"]:
        assert os.path.exists(os.path.join(GAME, "modes", m, "config", m + ".yaml")), m
    rules = load_rules()
    assert len(rules["houses"]) == 8 and len(rules["multiballs"]) == 7
    for m in [h["key"] for h in rules["houses"]] + [h["key"] for h in rules["multiballs"]]:
        assert m in cfg["modes"]


def test_every_value_has_a_confidence():
    r = load_rules()
    for h in r["houses"]:
        assert h["timer_conf"] in "HMLCFG" and h["award"]["conf"] in "HMLCFG"
    for m in r["multiballs"]:
        assert m["jackpot"]["conf"] in "HMLCFG"


@pytest.mark.skipif(not os.path.isdir(DATA), reason="extraction data not available")
def test_generated_files_current():
    r = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "gen_config.py"), "--check", "--data", DATA],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.mark.skipif(not os.path.isdir(DATA), reason="extraction data not available")
def test_rules_match_csv():
    rules = load_rules()
    modes = {int(r["mode_id"]): r for r in csv.DictReader(open(os.path.join(DATA, "modes.csv")))}
    awards = {int(r["award_id"]): int(r["initial_value_points"]) for r in csv.DictReader(open(os.path.join(DATA, "awards.csv")))}
    for h in rules["houses"]:
        m = modes[h["id"]]
        assert int(m["timer_id"]) == h["timer_id"], h["key"]
        assert awards[int(m["award_id"])] == h["award"]["start"], h["key"]
    mbs = {int(r["mball_id"]): r for r in csv.DictReader(open(os.path.join(DATA, "multiballs.csv")))}
    for m in rules["multiballs"]:
        row = mbs[m["id"]]
        assert int(row["running_flag"]) == m["flag"]
        assert int(row["start_bonus_points"]) == m["start_bonus"]
        assert row["ball_save_adjustment"] == m["ball_save_adjustment"]
        first_award = int(row["award_ids"].split("/")[0])
        assert awards[first_award] == m["jackpot"]["start"], m["key"]
    adj = {r["name"]: r for r in csv.DictReader(open(os.path.join(DATA, "adjustments.csv")))}
    for m in rules["multiballs"]:
        assert int(adj[m["ball_save_adjustment"]]["default"]) == m["ball_save_s"]
    g = rules["game_rules"]
    assert int(adj["ad_balls_per_game"]["default"]) == g["balls_per_game"]
    assert int(adj["ad_tilt_warnings"]["default"]) == g["tilt_warnings"]
    assert int(adj["ad_ball_save_time"]["default"]) == g["ball_save_time_s"]


# ---- rules core (pure Python)

def test_award_bump_and_cap():
    a = Award(500000, 375000, 75000000)
    assert a.give() == 500000 and a.give(global_mult=2) == 1000000
    a.bump()
    assert a.value == 875000
    for _ in range(500):
        a.bump()
    assert a.value == 75000000
    a.reset()
    assert a.value == 500000


def test_hurry_up_linear():
    assert Award(8000000).hurry_up(10, 20) == 4000000


def test_progression_wizard_path():
    p = Progression(load_rules())
    assert p.house_complete(0) == [] and p.house_complete(1) == [] and p.house_complete(2) == []
    assert p.house_complete(3) == ["ready_hand_of_the_king"]
    assert p.house_complete(3) == []
    p.house_complete(4)
    p.house_complete(5)
    assert p.house_complete(6) == ["ready_iron_throne"]
    assert p.house_complete(7) == ["ready_winter_has_come"]


def test_extra_ball_light_at_adjustment():
    p = Progression(load_rules(), extra_ball_after=2)
    p.house_complete(0)
    assert p.house_complete(1) == ["light_extra_ball"]


def test_extra_ball_limit():
    e = ExtraBalls(limit=1)
    e.light()
    assert e.collect() and not e.collect()
    e.light()
    assert not e.collect()
