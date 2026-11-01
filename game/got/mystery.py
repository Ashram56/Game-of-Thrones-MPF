"""Mystery (mystery.cpp): the 40-entry award table, the 3-slot menu, selection and payment. Source: Game-of-Thrones
docs/11-mystery-awards.md and data/mystery_awards.csv (ELF 1.37.0, H unless noted; the arg = combo multiplier is M)."""
import csv
import os
import random

MIN_GOLD = 300                 # can_we_start_mystery_now
TIMEOUT_S = 10                 # timer 22 (seconds: M)
HOUSE_KEYS = ("targaryen", "stark", "baratheon", "lannister", "greyjoy", "tyrell", "martell")
POINTS = {"Big Points": 1000000, "Bigger Points": 5000000, "Biggest Points": 25000000}
UPPER_LEVEL = {"Arrows": 1, "Charge": 2, "Breach": 3}
BUTTON = {"Baratheon button ability": 3, "Lannister button ability": 4, "Martell button ability": 6}
BONUS_X = {"+1 Bonus X": 1, "+2 Bonus X": 2, "+3 Bonus X": 3}
BONUS_X_MAX = 20
KEEP_GOLD = "Keep gold"


def load_table():
    here = os.path.dirname(__file__)
    for path in (os.path.join(os.environ.get("GOT_DATA", ""), "mystery_awards.csv"),
                 os.path.join(here, "..", "config", "rom", "mystery_awards.csv")):
        if os.path.isfile(path):
            with open(path) as f:
                return [{"index": int(r["table_index"]), "name": r["name"], "category": int(r["category"]),
                         "price": int(r["gold_price"]), "audit": r["audit_name"]} for r in csv.DictReader(f)]
    raise FileNotFoundError("mystery_awards.csv")


class Mystery:
    def __init__(self, mode):
        self.mode = mode
        self.machine = mode.machine
        self.table = load_table()
        self.rng = random.Random()
        self.menu = None            # {"slots": [None, entry, entry], "cursor": int}

    @property
    def player(self):
        return self.mode.player

    # --- availability
    def can_start(self):
        """can_we_start_mystery_now: lit, no multiball or house running, Hand/Iron/Wall not waiting, gold >= 300."""
        from got import state
        p, m = self.player, self.machine
        return bool(p.got_mystery_lit and p.got_gold >= MIN_GOLD and not self.menu
                    and not state.multiball_running(m) and not state.house_running(m)
                    and not state.hand_startable(m, p) and not state.iron_startable(m, p) and not p.got_wall_lit)

    def go(self, e):
        """The award's GoNoGo."""
        p, m, n = self.player, self.machine, e["name"]
        swords = int(p.got_swords or 0)
        if n in HOUSE_KEYS_NAMES:
            key = HOUSE_KEYS_NAMES[n]
            prog = p.got_progression
            hid = HOUSE_KEYS.index(key)
            lit = set((p.got_lit_houses or "").split(",")) - {""}
            if key in lit or (prog and hid in prog.complete):
                return False
            return key != "baratheon" or True        # Baratheon's per-player ability gate is not modelled
        if n == "Light Wild Fire":
            return not p.got_wildfire_lit
        if n in BONUS_X:
            return int(p.got_bonus_x or 1) + BONUS_X[n] <= BONUS_X_MAX
        if n == "Advance Wall Multiball":
            from got import state
            return not p.got_wall_lit and not state.multiball_running(m)
        if n == "Light Swords":
            return not p.got_swords_lit and swords <= 6
        if n == "Award Sword":
            return swords <= 2
        if n.startswith("Light ") and n.endswith("Super Jackpot"):
            return not p.got_super_lit
        if n.startswith("Video Mode"):
            return bool(self._setting("ad_allow_video_mode", 1))
        if n in UPPER_LEVEL:
            return int(p.got_upper_level or 0) < UPPER_LEVEL[n]
        if n == "Golden Hand":
            return not p.got_golden_hand
        if n == "Light Lord of Light":
            return not m.modes["combos"]._lol and int(p.got_lol_count or 0) < 10
        if n == "Light Playfield Multiplier":
            return int(p.got_ram_hits or 0) == 0 or int(p.got_multiplier or 1) > 4
        if n == "Light Extra Ball":
            return not p.got_extra_ball_lit
        if n == "Special":
            return int(self._setting("ad_special_limit", 1) or 0) > 0
        if n == "Start Winter Is Coming":
            return bool((p.got_lit_houses or "")) and not m.modes["winter_is_coming"].active \
                and not m.modes["winter_has_come"].active
        if n == "Hold Bonus":
            return not p.got_hold_bonus
        if n in BUTTON:
            return int(p.got_button_ability or 0) != BUTTON[n]
        return True

    def _setting(self, name, default):
        s = self.machine.settings
        return s.get_setting_value(name) if name in s._settings else default

    # --- menu
    def build(self):
        gold = int(self.player.got_gold)
        eligible = [e for e in self.table if e["price"] <= gold and self.go(e)]
        if not eligible:
            return None
        best = eligible[0]
        for e in eligible:
            if e["price"] > best["price"]:         # strict: ties keep the lower table index
                best = e
        others = [e for e in eligible if e["category"] != best["category"] and e is not best]
        mid = self.rng.choice(others) if others else None
        return {"slots": [None, mid, best], "cursor": 2}

    def start(self):
        self.menu = self.build()
        if not self.menu:
            return False
        self.player.got_mystery_lit = 0
        self.mode.delay.add(TIMEOUT_S * 1000, self.confirm, name="mystery_timeout")
        self.machine.events.post("got_mystery_menu", **self._labels())
        return True

    def _labels(self):
        """Slide text with the cursor marked: slot 2 top, slot 1 middle, slot 0 keep gold."""
        slots, cur = self.menu["slots"], self.menu["cursor"]
        names = {2: slots[2]["name"], 1: (slots[1] or {}).get("name", ""), 0: KEEP_GOLD}
        return {k: ("> " if cur == i else "  ") + names[i] for k, i in (("top", 2), ("middle", 1), ("keep", 0))}

    def move(self, step):
        if self.menu:
            self.menu["cursor"] = (self.menu["cursor"] + step) % 3
            self.machine.events.post("got_mystery_cursor", cursor=self.menu["cursor"], **self._labels())

    def confirm(self, **kwargs):
        if not self.menu:
            return
        self.mode.delay.remove("mystery_timeout")
        entry = self.menu["slots"][self.menu["cursor"]]
        self.menu = None
        if entry is None:
            self.machine.events.post("got_mystery_award", award=KEEP_GOLD)
            return
        self.pay(entry)

    def pay(self, e):
        p = self.player
        p.got_gold = max(int(p.got_gold) - e["price"], 0)
        self.give(e["name"])
        self.machine.events.post("got_mystery_award", award=e["name"])

    # --- effects (GiveOne)
    def give(self, n):
        p, ev = self.player, self.machine.events
        arg = int(p.got_combo_mult or 1)
        if n in POINTS:
            p.score += POINTS[n] * arg * (p.got_multiplier or 1)
        elif n in HOUSE_KEYS_NAMES:
            lit = set((p.got_lit_houses or "").split(",")) - {""}
            lit.add(HOUSE_KEYS_NAMES[n])
            p.got_lit_houses = ",".join(sorted(lit))
            ev.post("got_light_house", house=HOUSE_KEYS_NAMES[n])
        elif n == "Light Wild Fire":
            p.got_wildfire_lit = 1
        elif n in ("+5 Wild Fire", "+10 Wild Fire"):
            ev.post("got_wildfire_bump", n=5 if n.startswith("+5") else 10)
        elif n in BONUS_X:
            p.got_bonus_x = min(BONUS_X_MAX, max(1, int(p.got_bonus_x or 1)) + BONUS_X[n])
        elif n == "Grow Wall Jackpot":
            ev.post("got_bump_wall_jackpot")
        elif n == "Advance Wall Multiball":
            p.got_wall_advances += 1
        elif n == "Light Swords":
            ev.post("got_light_swords")
        elif n == "Award Sword":
            p.got_mystery_arg = arg
            ev.post("got_award_sword")
        elif n.endswith("Super Jackpot"):
            p.got_super_lit = int(n[6])
        elif n.startswith("Video Mode"):
            ev.post("got_video_mode_start", n=int(n[11]))
        elif n in UPPER_LEVEL:
            p.got_upper_level = max(int(p.got_upper_level or 0), UPPER_LEVEL[n])
        elif n == "Light Lock":
            p.got_lock_lit = 1
        elif n == "Golden Hand":
            p.got_golden_hand = 1
        elif n == "Light Lord of Light":
            ev.post("got_light_lord_of_light")
        elif n == "Light Playfield Multiplier":
            p.got_ram_hits = max(int(p.got_ram_hits or 0), 3)       # the next ram hit starts the multiplier (M)
        elif n == "Light Extra Ball":
            p.got_extra_ball_lit = 1
            ev.post("got_light_extra_ball")
        elif n == "Special":
            ev.post("got_special")
        elif n == "Start Winter Is Coming":
            p.got_winter_award = int(p.got_winter_award or 4000000) * 4
            ev.post("start_mode_winter_is_coming")
        elif n == "Hold Bonus":
            p.got_hold_bonus = 1
        elif n in BUTTON:
            p.got_button_ability = BUTTON[n]
            p.got_ability_uses = 8 if BUTTON[n] == 4 else 0           # Lannister buttons per game (default 8)


HOUSE_KEYS_NAMES = {"Light " + k.capitalize(): k for k in HOUSE_KEYS}
