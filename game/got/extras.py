"""Gold + Mystery, Bonus X and the playfield multiplier (PFx). Source: community rulesheet rev 1.37 (Mystery prices from v1.26),
confidence M; per-standup gold amounts are CFG placeholders (not in the rulesheet). The end-of-ball bonus amounts and the pop-bumper
award trigger are not recovered, so they are not modelled."""
import random

from mpf.core.mode import Mode

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

# name: (gold cost, effect)  effects: ("points", n) ("bonus_x", n) ("wall_advance", 1) ("light_extra_ball",) ("hold_bonus",)
MYSTERY = {
    "big_points": (120, ("points", 1000000)),
    "bonus_x_1": (160, ("bonus_x", 1)),
    "advance_wall": (830, ("wall_advance", 1)),
    "bonus_x_2": (1430, ("bonus_x", 2)),
    "bigger_points": (2600, ("points", 5000000)),
    "bonus_x_3": (2970, ("bonus_x", 3)),
    "hold_bonus": (4200, ("hold_bonus",)),
    "light_extra_ball": (4500, ("light_extra_ball",)),
    "biggest_points": (6000, ("points", 25000000)),
}


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
        self.add_mode_event_handler("got_house_chosen", self._house_chosen)
        self.machine.events.post("got_extras_ready")

    def _house_chosen(self, **kwargs):
        pass

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
        p = self.player
        if not p.got_mystery_lit:
            return
        p.got_mystery_lit = 0
        affordable = [n for n, (cost, _) in MYSTERY.items() if cost <= p.got_gold]
        if not affordable:
            return
        name = self.rng.choice(affordable)        # rulesheet: keep gold / random affordable / most expensive; random here
        cost, effect = MYSTERY[name]
        p.got_gold -= cost
        self._apply(name, effect)

    def _apply(self, name, effect):
        p = self.player
        kind = effect[0]
        if kind == "points":
            p.score += effect[1] * (p.got_multiplier or 1)
        elif kind == "bonus_x":
            p.got_bonus_x = min(BONUS_X_MAX, max(1, int(p.got_bonus_x or 1)) + effect[1])
        elif kind == "wall_advance":
            p.got_wall_advances += 1
        elif kind == "light_extra_ball":
            self.machine.events.post("got_light_extra_ball")
        elif kind == "hold_bonus":
            p.got_hold_bonus = 1
        self.machine.events.post("got_mystery_award", award=name)

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
