"""Combo X, swords and Wildfire. Source: Game-of-Thrones docs/10 (ELF 1.37.0), H unless noted; data/swords.csv."""
import csv
import os
import random

from mpf.core.mode import Mode

from got.powers import HOUSES

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


BANK = ("s_3_bank_drop_tgt_top", "s_3_bank_drop_tgt_mid", "s_3_bank_drop_tgt_btm")
SPINNER_START, SPINNER_STEP, SPINNER_CAP = 2500, 150, 250000
B_INC = (0, 10000, 25000, 50000, 75000, 100000, 125000, 150000, 175000, 200000)
B_CAP = (0, 50000, 125000, 250000, 375000, 500000, 625000, 750000, 875000, 1000000)
TWO_BANK = ("s_right_2_bank_top", "s_right_2_bank_bottom")
SJ_BASE, SJ_PER_LEVEL, SJ_BONUS = 250000, 6, 10000000
TWO_BANK_DIFFICULTY = 2               # adjustment 122 default
# cmode::GetTickleShots (docs/14, H): the shot that counts toward lighting each house; every house needs 3
TICKLE = {"targaryen": ("s_kickback",), "stark": ("s_right_ramp_exit",), "baratheon": BANK, "lannister": ("s_left_ramp_exit",),
          "greyjoy": ("s_left_loop",), "tyrell": ("s_right_2_bank_top", "s_right_2_bank_bottom"), "martell": ("s_right_loop",)}
TICKLE_NEEDED, TICKLE_BASE, TICKLE_STEP = 3, 75000, 25000
# set_button_ability on house completion (docs/14 house_select_awards.csv); Greyjoy (0) keeps the previous one
ABILITY_ON_COMPLETE = {"targaryen": 1, "stark": 2, "baratheon": 3, "lannister": 4, "tyrell": 5, "martell": 6}
LORD_LIMIT = 10                       # adjustment 123 default (10 = unlimited)


def video_mode_score(outcome, n, level):
    """cvideomode scores (docs/10 section 6): win / tie / loss, times the Mystery multiplier n (1-3)."""
    if outcome == "win":
        return (5000000 * level + 20000000) * n
    if outcome == "tie":
        return (1500000 * level + 2500000) * n
    return 500000 * level * n


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
        self.add_mode_event_handler("got_house_complete", self._ability_on_complete)
        for house, switches in TICKLE.items():
            for sw in switches:
                self.add_mode_event_handler(sw + "_active", self._tickle, house=house)
        self.add_mode_event_handler("got_bump_wall_jackpot", self._bump_wall_jackpot)
        self.add_mode_event_handler("got_special", self._special)
        self.add_mode_event_handler("got_award_sword", self._award_sword)
        self.add_mode_event_handler(RAM + "_active", self._ram)
        self.add_mode_event_handler("got_wildfire_bump", self._wildfire_bump)
        # spinner (docs/10 section 4) and Lord of Light (section 5)
        self._lol = False
        self._b = 0
        self._level = 0
        self._banks = 0
        if p.got_spinner_v is None or not p.got_spinner_v:
            p.got_spinner_v = SPINNER_START
        for sw in BANK:
            self.add_mode_event_handler(sw + "_active", self._spinner_bump)
        self.add_mode_event_handler("s_1_bank_drop_active", self._spinner_bump)
        self.add_mode_event_handler("got_pfx", self._spinner_bump)
        self.add_mode_event_handler("got_bank_complete", self._bank_complete)
        self.add_mode_event_handler("s_left_spinner_active", self._spin)
        self.add_mode_event_handler("s_left_outlane_active", self._outlane)
        self.add_mode_event_handler("s_right_outlane_active", self._outlane)
        self.add_mode_event_handler("got_light_lord_of_light", self._light_lol)
        self.add_mode_event_handler("got_video_mode_result", self._video_result)
        # ram Super Jackpot (docs/12) and the lock (flag 36), both reset at ball start (InitializeFirstBall)
        if not p.got_bw_init:                  # InitializeFirstBall runs at the player's first ball (M: once, not every ball)
            p.got_bw_init = 1
            p.got_super_lit = 0
            p.got_lock_lit = 0
        for sw in TWO_BANK:
            self.add_mode_event_handler(sw + "_active", self._two_bank, sw=sw)
        self._two_bank_hit = set()
        self.add_mode_event_handler("mode_blackwater_started", self._bw_played)

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

    def _award_sword(self, **kwargs):
        """Mystery "Award Sword": the same pick and pay as a collection, without needing a lit sword."""
        p = self.player
        p.got_swords_lit = int(p.got_swords_lit or 0) + 1
        self._collect_sword(int(p.got_mystery_arg or 1))

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
        if p.got_super_lit:
            self._super_jackpot()
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

    # --- spinner (cspinner): per spin V[p] + B, V rises 150 per bump, B by level (reset each ball)
    def spin_value(self):
        return int(self.player.got_spinner_v) + self._b

    def _spin(self, **kwargs):
        self.player.score += self.spin_value() * (self.player.got_multiplier or 1)

    def _spinner_bump(self, **kwargs):
        p = self.player
        p.got_spinner_v = min(SPINNER_CAP, int(p.got_spinner_v) + SPINNER_STEP)
        self._b = min(B_CAP[self._level], self._b + B_INC[self._level])

    def _bank_complete(self, **kwargs):
        """BumpLevel on the 1st and every 3rd completion (1, 3, 6, 9...) when completed houses > level (max 9)."""
        self._banks += 1
        if self._banks == 1 or self._banks % 3 == 0:
            prog = self.player.got_progression
            done = len(prog.complete) if prog else 0
            if done > self._level and self._level < 9:
                self._level += 1
            self._light_lol()

    # --- Lord of Light: both outlanes save one ball until used or end of ball
    def _light_lol(self, **kwargs):
        p = self.player
        if self._lol or int(p.got_lol_count or 0) >= LORD_LIMIT:
            return
        self._lol = True
        p.got_lol_count = int(p.got_lol_count or 0) + 1
        self.machine.events.post("got_lord_of_light_lit")

    def _outlane(self, **kwargs):
        if self._lol:
            self._lol = False
            self.machine.playfield.add_ball(1)
            self.machine.events.post("got_lord_of_light_save")

    # --- video mode: the duel runs in the display; its result pays here
    def _video_result(self, outcome="tie", n=1, level=2, **kwargs):
        self.player.score += video_mode_score(outcome, int(n), int(level))

    # --- ram Super Jackpot: V x 6 x level + 10M, V = Blackwater jackpot (award #8); recomputed from Wildfire when idle
    def _super_jackpot(self):
        p = self.player
        level = int(p.got_super_lit)
        if not self.machine.modes["blackwater"].active:
            p.got_bw_jackpot = jackpot_value(int(p.got_wildfire or 0))
        v = int(p.got_bw_jackpot or SJ_BASE)
        points = (v * SJ_PER_LEVEL * level + SJ_BONUS) * (p.got_multiplier or 1)
        p.got_super_lit = 0
        p.score += points
        self.machine.events.post("got_ram_super_jackpot", level=level, points=points)

    # --- Light Lock from the right two-bank (two_bank_light_lock): never in a multiball; before Blackwater was ever played it
    # lights when adjustment 122 <= 2 (default). The bool of later banks is M, so later completions do not relight here.
    def _two_bank(self, sw, **kwargs):
        """TwoBankTargetHandler calls two_bank_light_lock(false) on every hit and (true) when the bank completes (docs/13)."""
        p = self.player
        self._two_bank_hit.add(sw)
        complete = self._two_bank_hit >= set(TWO_BANK)
        if complete:
            self._two_bank_hit = set()
        from got import state
        if state.multiball_running(self.machine) or p.got_lock_lit:
            return
        if not p.got_bw_played and TWO_BANK_DIFFICULTY <= 2:
            p.got_lock_lit = 1                  # never played Blackwater: any hit lights it at difficulty <= 2
        elif complete:
            p.got_lock_lit = 1                  # otherwise only a completed bank
        else:
            return
        self.machine.events.post("got_lock_lit")

    def _bw_played(self, **kwargs):
        self.player.got_bw_played = int(self.player.got_bw_played or 0) + 1

    # --- Grow Wall Jackpot (Mystery / pop award): cwall::BumpJackpotValue raises the Wall award by its own bump, capped
    def _bump_wall_jackpot(self, **kwargs):
        p = self.player
        award = self.machine.modes["wall"].config["mode_settings"]["award"]
        value = int(p.got_award_wall or award["start"])
        p.got_award_wall = min(award["cap"], value + award["bump"]) if award.get("cap") else value + award["bump"]

    # --- Special (docs/13, H): adjustment 54 picks the payout (0 one credit, 3 = 25M points, 4 extra ball, 1/2 nothing);
    # adjustment 53 = Specials per player per game (0 = none); over the limit it pays the 25M points instead.
    SPECIAL_POINTS = 25000000

    def _special(self, **kwargs):
        p = self.player
        limit = int(self._setting("ad_special_limit", 1) or 0)
        award = int(self._setting("ad_special_award", 0) or 0)
        if limit == 0 or int(p.got_specials or 0) >= limit:
            award = 3
        else:
            p.got_specials = int(p.got_specials or 0) + 1
        if award == 3:
            p.score += self.SPECIAL_POINTS
        elif award == 0:
            self.machine.events.post("got_special_credit")
        elif award == 4:
            self.machine.events.post("got_special_extra_ball")
        self.machine.events.post("got_special_awarded", award=award)

    def _setting(self, name, default):
        s = self.machine.settings
        return s.get_setting_value(name) if name in getattr(s, "setting_definitions", {}) else default

    # --- house tickle: three hits of the house's tickle shot light it (the throne then starts lit houses first)
    def _tickle(self, house, **kwargs):
        p = self.player
        from got import state
        prog = p.got_progression
        hid = HOUSES.index(house)
        lit = set((p.got_lit_houses or "").split(",")) - {""}
        if house in lit or (prog and hid in prog.complete) or state.multiball_running(self.machine):
            return
        n = int(getattr(p, "got_tickle_" + house) or 0)
        p.score += (TICKLE_BASE + TICKLE_STEP * n) * (p.got_multiplier or 1)
        n += 1
        setattr(p, "got_tickle_" + house, n)
        if n >= TICKLE_NEEDED:
            setattr(p, "got_tickle_" + house, 0)
            lit.add(house)
            p.got_lit_houses = ",".join(sorted(lit))
            self.machine.events.post("got_light_house", house=house)

    def _ability_on_complete(self, key=None, **kwargs):
        ab = ABILITY_ON_COMPLETE.get(key)
        if key == "lannister":                                 # docs/14: completing Lannister gives 200 gold (400 with the ability)
            self.player.got_gold += 400 if int(self.player.got_button_ability or 0) == 4 else 200
        if ab:
            p = self.player
            p.got_button_ability = ab
            p.got_ability_uses = 8 if ab == 4 else 1          # Lannister buttons per game (adjustment 116); the others once per grant (M)
        lit = set((self.player.got_lit_houses or "").split(",")) - {""}
        lit.discard(key)                                      # a completed house is no longer lit
        self.player.got_lit_houses = ",".join(sorted(lit))

    # --- Tyrell Iron Bank (ability 5): 20M x m - 18M + 75,000 x m^2 x min(c, 120), c = sum of combo multipliers x m (M)
    def iron_bank(self):
        p = self.player
        m = int(p.got_multiplier or 1)
        c = sum(self._armed.values()) * m
        if int(p.got_button_ability or 0) != 5 or int(p.got_ability_uses or 0) <= 0 or c <= 5:
            return False
        points = 20000000 * m - 18000000 + 75000 * m * m * min(c, 120)
        p.score += points
        p.got_ability_uses -= 1
        p.got_multiplier = 0
        self._end()
        self.machine.events.post("got_iron_bank", points=points)
        return True
