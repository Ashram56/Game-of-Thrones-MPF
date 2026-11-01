"""Gold + Mystery, Bonus X and the playfield multiplier (PFx). Source: community rulesheet rev 1.37 (Mystery prices from v1.26),
confidence M; per-standup gold amounts are CFG placeholders (not in the rulesheet). The end-of-ball bonus amounts and the pop-bumper
award trigger are not recovered, so they are not modelled."""
import random

from mpf.core.mode import Mode

from got import pops
from got.mystery import Mystery

STANDUPS = ("s_target_1", "s_target_2", "s_target_3", "s_target_4", "s_target_5")
GOLD_PER_STANDUP = 100                 # CFG
LANNISTER_STANDUP_FACTOR = 2.43        # rulesheet: standups give 143% more gold as Lannister
LANNISTER_START_GOLD = 500             # rulesheet: 500 gold at start
TOP_LANES = ("s_left_top_lane", "s_right_top_lane")
BONUS_X_MAX = 20
RAM = "s_battering_ram"
MYSTERY_SWITCH = "s_elevator_popper"   # StartMystery is called from the elevator awards (docs/06)
# PFx: 3 ram hits qualify, the 4th starts 2x, then every 4 further hits +1x up to 5x
PFX_FIRST = 4
PFX_STEP = 4
PFX_MAX = 5

class Extras(Mode):
    rng = None

    def mode_start(self, **kwargs):
        self.rng = self.rng or random.Random()
        p = self.player
        if p.got_gold == 0 and not p.got_gold_started:
            p.got_gold_started = 1
            if p.got_house == "lannister":
                p.got_gold = LANNISTER_START_GOLD
        self._standups = set(getattr(p, "got_standups_hit", None) or ())
        for sw in STANDUPS:
            self.add_mode_event_handler(sw + "_active", self._standup, sw=sw)
        for sw in TOP_LANES:
            self.add_mode_event_handler(sw + "_active", self._top_lane, sw=sw)
        self._lanes = set()
        self.add_mode_event_handler(RAM + "_active", self._ram)
        self.add_mode_event_handler(MYSTERY_SWITCH + "_active", self._mystery_shot)
        self.mystery = Mystery(self)
        self.mystery.rng = self.rng
        self.add_mode_event_handler("s_l_flipper_button_active", self._mystery_cursor, step=-1)
        self.add_mode_event_handler("s_r_flipper_button_active", self._mystery_cursor, step=1)
        self.add_mode_event_handler("s_lockdown_active", self.mystery.confirm)
        self.add_mode_event_handler("got_house_chosen", self._house_chosen)
        self._bonus_start()
        for sw in self.machine.modes["scoring"].config.get("mode_settings", {}).get("bonus_hit_switches", []):
            self.add_mode_event_handler(sw + "_active", self._bonus_hit)
        self.add_mode_event_handler("ball_will_end", self._bonus_pay)
        self.add_mode_event_handler("tilt", self._tilted)
        self.add_mode_event_handler("mode_castle_started", self._castle)
        self._tilt = False
        self._tape, self._pop_names = pops.load_tape()
        self._reels = pops.Reels(self._tape)
        for reel, sw in ((30, "s_left_pop_bumper"), (31, "s_right_pop_bumper"), (32, "s_bottom_pop_bumper")):
            self.add_mode_event_handler(sw + "_active", self._pop_hit, reel=reel)
        self.machine.events.post("got_extras_ready")

    def _house_chosen(self, **kwargs):
        pass

    # --- End-of-ball bonus (docs/09, H): base 125,000 + 3,330 per switch event + 175,000 per house + 150,000 per sword
    # + 7,500,000 per castle + 300 per gold + 5,500 per wildfire + 750,000 Golden Hand, times Bonus X (max 20)
    BONUS_BASE = 125000
    PER_HIT, PER_HOUSE, PER_SWORD, PER_CASTLE, PER_GOLD, PER_WILDFIRE, GOLDEN_HAND = 3330, 175000, 150000, 7500000, 300, 5500, 750000

    def _bonus_start(self):
        p = self.player
        if p.got_hold_bonus:                    # Hold Bonus (Mystery): keep base, hits and Bonus X this ball
            p.got_hold_bonus = 0
            return
        p.got_bonus_base = self.BONUS_BASE
        p.got_bonus_hits = 0
        p.got_bonus_x = 1
        if p.ball == 1:
            p.got_golden_hand = 0

    def _bonus_hit(self, **kwargs):
        self.player.got_bonus_hits += 1

    def _castle(self, **kwargs):
        self.player.got_castles += 1

    def _tilted(self, **kwargs):
        self._tilt = True

    def bonus_total(self):
        p = self.player
        prog = p.got_progression
        houses = len(prog.complete - {7}) if prog else 0
        unmult = (int(p.got_bonus_base or self.BONUS_BASE) + self.PER_HIT * int(p.got_bonus_hits) + self.PER_HOUSE * houses
                  + self.PER_SWORD * int(p.got_swords) + self.PER_CASTLE * int(p.got_castles) + self.PER_GOLD * int(p.got_gold)
                  + self.PER_WILDFIRE * int(p.got_wildfire) + (self.GOLDEN_HAND if p.got_golden_hand else 0))
        return unmult * max(1, int(p.got_bonus_x or 1))

    def _bonus_pay(self, **kwargs):
        if self._tilt:
            return
        total = self.bonus_total()
        self.player.score += total
        self.machine.events.post("got_end_of_ball_bonus", points=total)

    # --- Pict-O-Pops awards (docs/09)
    def _go(self, i):
        p = self.player
        if i == self._reels.last:
            return False
        name = self._pop_names.get(i, "")
        if name == "Light Mystery":
            return not p.got_mystery_lit and p.got_gold >= 500
        if name == "Bump Wall Jackpot":
            return not self.machine.modes["wall"].active
        if name == "Advance Toward Wall MB":
            return not p.got_wall_lit and not any(m.active and m.config.get("mode_settings", {}).get("kind") == "multiball" for m in self.machine.modes)
        if name == "Add Mode Time":
            return any(m.active and m.config.get("mode_settings", {}).get("kind") == "house" for m in self.machine.modes)
        if name == "Add A Ball":
            return not p.got_add_a_ball_flag and not any(m.active and m.config.get("mode_settings", {}).get("kind") == "multiball" for m in self.machine.modes)
        if name == "Light Extra Ball":
            return not p.got_extra_ball_lit
        if name == "Bump Winter Is Coming value":
            return not self.machine.modes["winter_is_coming"].active
        return True

    def _pop_hit(self, reel, **kwargs):
        win = self._reels.hit(reel, self._go)
        if win is None:
            return
        name = self._pop_names[win]
        p = self.player
        mult = p.got_multiplier or 1
        if name == "Big Points":
            p.score += 1000000 * mult
        elif name == "+1 Bonus X":
            p.got_bonus_x = min(BONUS_X_MAX, max(1, int(p.got_bonus_x or 1)) + 1)
        elif name == "+3 Bonus X":
            p.got_bonus_x = min(BONUS_X_MAX, max(1, int(p.got_bonus_x or 1)) + 3)
        elif name in ("Gold", "Lannister Gold"):
            p.got_gold += 750 if p.got_house == "lannister" else 150
        elif name == "Advance Toward Wall MB":
            p.got_wall_advances += 1
        elif name == "+5 Wild Fire":
            self.machine.events.post("got_wildfire_bump", n=5)
        elif name == "Light Wild Fire":
            p.got_wildfire_lit = 1
        elif name == "Light Lord of Light":
            self.machine.events.post("got_light_lord_of_light")
        elif name == "Light Swords":
            self.machine.events.post("got_light_swords")
        elif name == "Light Mystery":
            p.got_mystery_lit = 1
        elif name == "Add Mode Time":
            for m in self.machine.modes:
                cfg = m.config.get("mode_settings", {})
                if m.active and cfg.get("kind") == "house":
                    t = self.machine.timers.get(cfg["key"] + "_timer")
                    if t is not None:
                        t.add(10)
        elif name == "Add A Ball":
            p.got_add_a_ball_flag = 1
        elif name == "Light Extra Ball":
            p.got_extra_ball_lit = 1
            self.machine.events.post("got_light_extra_ball")
        elif name == "Bump Winter Is Coming value":
            p.got_winter_award = int(p.got_winter_award or 4000000) + 75000
        self.machine.events.post("got_pop_award", award=name)

    # --- gold and Mystery
    def _standup(self, sw, **kwargs):
        p = self.player
        gold = GOLD_PER_STANDUP * (LANNISTER_STANDUP_FACTOR if p.got_house == "lannister" else 1)
        p.got_gold += int(gold)
        self._standups.add(sw)
        if self._standups >= set(STANDUPS):                  # all gold standups: Mystery lit
            self._standups = set()
            p.got_mystery_lit = 1
            self.machine.events.post("got_mystery_lit")

    def _mystery_shot(self, **kwargs):
        if self.mystery.can_start():
            self.mystery.start()

    def _mystery_cursor(self, step, **kwargs):
        self.mystery.move(step)

    # --- Bonus X
    def _top_lane(self, sw, **kwargs):
        p = self.player
        self._lanes.add(sw)
        if self._lanes >= set(TOP_LANES):
            self._lanes = set()
            p.got_bonus_x = min(BONUS_X_MAX, max(1, int(p.got_bonus_x or 1)) + 1)
            self.machine.events.post("got_bonus_x", value=p.got_bonus_x)

    # --- playfield multiplier
    def _ram(self, **kwargs):
        p = self.player
        p.got_ram_hits += 1
        hits = p.got_ram_hits
        if hits >= PFX_FIRST and (hits - PFX_FIRST) % PFX_STEP == 0:
            p.got_multiplier = min(PFX_MAX, 2 + (hits - PFX_FIRST) // PFX_STEP)
            self.machine.events.post("got_pfx", value=p.got_multiplier)
