"""Combo X, swords and Wildfire. Source: Game-of-Thrones docs/10 (ELF 1.37.0), H unless noted; data/swords.csv."""
import csv
import os
import random

from mpf.core.mode import Mode

# shot switch -> combo index (ccombo_manager ctor: 0 left loop, 1 kickback, 2 left ramp exit, 3 right ramp exit, 4 right loop)
SHOTS = {"s_left_loop": 0, "s_kickback": 1, "s_left_ramp_exit": 2, "s_right_ramp_exit": 3, "s_right_loop": 4}
# StartNewCombos follow-up lists (docs/10 section 1), by combo index
FOLLOW = {0: {4, 2}, 1: {0, 1, 2, 3, 4}, 2: {0, 1, 3, 4}, 3: {0, 1, 2, 4}, 4: {2, 1, 3}}
WINDOW_S = 7.0
GRACE_S = 93 / 66.0                   # 93 ticks at 66 ticks/s (M for the tick rate)
COMBO_CAP, COMBO_CAP_HAND = 5, 6
SWORD_SWITCH = "s_right_ramp_exit"
DIFFICULTY = 1                        # adjustment 120 ad_multiplers_difficulty default (range 0-2)
RAM = "s_battering_ram"
WILDFIRE_S, WILDFIRE_ADD_S, WILDFIRE_RAM_POINTS = 20, 2, 10
SWORDS_CSV = os.environ.get("GOT_SWORDS_CSV", "")


def load_swords():
    here = os.path.dirname(__file__)
    for path in (SWORDS_CSV, os.path.join(os.environ.get("GOT_DATA", ""), "swords.csv"),
                 os.path.join(here, "..", "config", "rom", "swords.csv")):
        if path and os.path.exists(path):
            with open(path) as f:
                return [(int(r["sword_index"]), int(r["weight"]), int(r["award_value"])) for r in csv.DictReader(f)]
    raise FileNotFoundError("swords.csv")


def jackpot_value(n):
    """cblackwater::CalcJackpotValue(n): 250,000 + sum(55,000 - 10 i^2), each term floored at 1,000 (docs/10 section 3)."""
    total = 250000
    for i in range(n):
        total += max(55000 - 10 * i * i, 1000)
    return total


class Combos(Mode):
    rng = None

    def mode_start(self, **kwargs):
        self.rng = self.rng or random.Random()
        self._swords = load_swords()
        self._armed = {}               # combo index -> multiplier it pays (follow-ups of the last shot)
        self._next = 2
        self._expire = None
        p = self.player
        p.got_combo_mult = 1
        for sw in SHOTS:
            self.add_mode_event_handler(sw + "_active", self._shot, sw=sw)
        self.add_mode_event_handler("got_house_complete", self._light_sword)
        self.add_mode_event_handler("got_light_swords", self._light_sword)
        self.add_mode_event_handler(RAM + "_active", self._ram)
        self.add_mode_event_handler("got_wildfire_bump", self._wildfire_bump)

    # --- Combo X
    def max_level(self):
        p = self.player
        hand = any(m.active and m.config.get("mode_settings", {}).get("key") == "hand_of_the_king" for m in self.machine.modes)
        return min(COMBO_CAP_HAND if hand else COMBO_CAP, 4 - DIFFICULTY + int(p.got_swords or 0))

    def _shot(self, sw, **kwargs):
        idx = SHOTS[sw]
        p = self.player
        mult = self._armed.get(idx, 1)          # multiplier before the bump (ccombo_manager::ShotMade)
        if idx in self._armed:
            self._next = min(self._next + 1, self.max_level())
        else:
            self._next = 2
        p.got_combo_mult = mult
        self._armed = {i: min(self._next, self.max_level()) for i in FOLLOW[idx]}
        if self._expire:
            self.delay.remove("combo_expire")
        self.delay.add(int((WINDOW_S + GRACE_S) * 1000), self._end, name="combo_expire")
        self._expire = True
        if sw == SWORD_SWITCH:
            self._collect_sword(mult)
        self.machine.events.post("got_combo", mult=mult)

    def _end(self, **kwargs):
        self._armed = {}
        self._next = 2
        self._expire = None
        self.player.got_combo_mult = 1

    # --- swords
    def _light_sword(self, **kwargs):
        p = self.player
        if int(p.got_swords or 0) + int(p.got_swords_lit or 0) < 7:
            p.got_swords_lit = int(p.got_swords_lit or 0) + 1

    def _collect_sword(self, mult):
        p = self.player
        if not p.got_swords_lit:
            return
        owned = {int(x) for x in str(p.got_swords_owned or "").split(",") if x != ""}
        pool = [s for s in self._swords if s[0] not in owned]
        if not pool:
            return
        idx, _, value = self.rng.choices(pool, weights=[s[1] for s in pool])[0]
        owned.add(idx)
        p.got_swords_owned = ",".join(str(i) for i in sorted(owned))
        p.got_swords = len(owned)
        p.got_swords_lit = int(p.got_swords_lit) - 1
        p.score += value * mult * (p.got_multiplier or 1)
        self.machine.events.post("got_sword", sword=idx, points=value * mult)

    # --- Wildfire (battering ram)
    def _wildfire_bump(self, n=5, **kwargs):
        self.player.got_wildfire = int(self.player.got_wildfire or 0) + int(n)

    def _ram(self, **kwargs):
        p = self.player
        if getattr(self, "_wf_running", False):
            self._wildfire_bump(WILDFIRE_RAM_POINTS)
            self.delay.remove("wildfire_end")
            self._wf_left = getattr(self, "_wf_left", WILDFIRE_S) + WILDFIRE_ADD_S
            self.delay.add(int(self._wf_left * 1000), self._wf_end, name="wildfire_end")
        elif p.got_wildfire_lit:
            p.got_wildfire_lit = 0
            self._wf_running = True
            self._wf_left = WILDFIRE_S
            self.delay.add(WILDFIRE_S * 1000, self._wf_end, name="wildfire_end")
            self.machine.events.post("got_wildfire_start")

    def _wf_end(self, **kwargs):
        self._wf_running = False
        self.machine.events.post("got_wildfire_end")
