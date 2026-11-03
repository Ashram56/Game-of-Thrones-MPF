"""Pure-Python rules core: no MPF import, so it is unit-tested without MPF (MPF cannot be installed offline).

Models what 03-rules.md recovered: a caward-like award (current value, per-hit bump, cap), the hurry-up decay,
and the house-completion progression (03 s6). Values come from game/config/rules.yaml; unknown ones are CFG there.
"""
import os

from ruamel.yaml import YAML   # MPF's own dependency: the platform installs no PyYAML

RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "rules.yaml")


def load_rules(path=RULES_PATH):
    with open(path, encoding="utf-8") as f:
        return YAML(typ="safe").load(f)


class Award:
    """caward: value starts at `start`; bump() adds the increment, clamped to `cap` when cap > 0 (03 s7)."""

    def __init__(self, start, bump=0, cap=0):
        self.start, self.increment, self.cap = int(start), int(bump), int(cap)
        self.value = self.start

    def reset(self):
        self.value = self.start

    def bump(self, amount=None):
        self.value += self.increment if amount is None else int(amount)
        if self.cap and self.value > self.cap:
            self.value = self.cap
        return self.value

    def give(self, mult=1, global_mult=1):
        """GiveAward(mult): value x mult x the global score multiplier."""
        return self.value * mult * global_mult

    UPDATES_PER_S = 5.5          # M: cgametimer update frequency 2 of 11 sub-steps/s (Game-of-Thrones docs/06)

    def hurry_up(self, remaining_s, total_s):
        """ROM decay (caward::DecAward, docs/06, H formula, M update rate): floor = 10% of the award (rounded down to a
        multiple of 100,000 when above 100,000); every update subtracts ((A - floor) / T / 10 + 1) x 10, T = updates in
        the timer. Winter 4,000,000 / 16 s: floor 400,000, about 40,900 per update."""
        a = self.value
        floor = a // 10
        if floor > 100000:
            floor -= floor % 100000
        t = max(1, int(self.UPDATES_PER_S * total_s))
        dec = ((a - floor) // t // 10 + 1) * 10
        updates = int(self.UPDATES_PER_S * max(0, total_s - remaining_s))
        return max(floor, a - dec * updates)


class Progression:
    """Per-player wizard path, from cmode_manager::ModeComplete (03 s6)."""

    def __init__(self, rules, extra_ball_after=None):
        p = rules["progression"]
        self.hand_after = p["hand_of_the_king_ready_after_houses"]
        self.houses = set(p["houses_counted"])
        self.eb_after = extra_ball_after or 8   # ad_house_complete_extra_ball default 8, range 2-8
        self.complete = set()
        self.ready = set()          # multiball keys that became ready
        self.started = set()        # ready multiballs already started
        self.extra_ball_lit = False

    def house_complete(self, house_id):
        """Returns the events this completion causes, in the ROM's order."""
        events = []
        if house_id in self.complete:
            return events
        self.complete.add(house_id)
        counted = len(self.complete & self.houses)
        if house_id in self.houses:
            if counted == self.eb_after and not self.extra_ball_lit:
                self.extra_ball_lit = True
                events.append("light_extra_ball")
            if counted == self.hand_after:
                self.ready.add("hand_of_the_king")
                events.append("ready_hand_of_the_king")
            if self.houses <= self.complete:
                self.ready.add("iron_throne")
                events.append("ready_iron_throne")
        return events


class ExtraBalls:
    """Extra ball bookkeeping with the adjustment limit (ad_extra_ball_limit, default 5)."""

    def __init__(self, limit=5):
        self.limit, self.awarded, self.lit = limit, 0, False

    def light(self):
        self.lit = True

    def collect(self):
        if self.lit and self.awarded < self.limit:
            self.lit = False
            self.awarded += 1
            return True
        return False
