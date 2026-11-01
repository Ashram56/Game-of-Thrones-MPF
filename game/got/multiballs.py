"""Multiball phases: shot sets that light a Super Jackpot at the battering ram. Rules: community rulesheet (pinballrulesheets.com
rev 1.37) over the ROM award values; the set/ram structure is M, the Super multiplier is a placeholder (CFG: the ROM's
AwardSuperJackpot formula is not recovered)."""
from got.award_mode import AwardMode
from got.phases import PHASES, RAM


class SetMultiball(AwardMode):
    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._ph = PHASES[self._cfg["key"]]
        self._group = 0
        self._done = set()
        self._set_points = 0
        self._super_until = None
        self._sets = 0

    def _group_shots(self):
        groups = self._ph["groups"]
        return groups[self._group % len(groups)]

    def _super_switch(self):
        return self._ph.get("super_switch", RAM)

    def _super_lit(self):
        if self._super_until is None:
            return False
        if self._super_until == 0:
            return True
        return self.machine.clock.get_time() <= self._super_until

    def _accepts(self, sw):
        self._shots = 0
        if sw == self._super_switch() and self._super_lit():
            self._collect_super()
            return False
        if sw in self._group_shots() and sw not in self._done and not self._super_lit():
            self._done.add(sw)
            return True
        return False

    def _pay(self):
        super()._pay()
        self._set_points += self._last_points
        if self._done >= set(self._group_shots()):
            window = self._ph["window"]
            self._super_until = 0 if not window else self.machine.clock.get_time() + window
            self.machine.events.post("got_%s_super_lit" % self._cfg["key"])

    def _collect_super(self):
        points = int(self._set_points * self._ph["super_mult"]) * (self.player.got_multiplier or 1)
        self.player.score += points
        self.machine.events.post("got_%s_super" % self._cfg["key"], points=points)
        self._sets += 1
        self._done, self._set_points, self._super_until = set(), 0, None
        self._group += 1
        if self._ph["sets"] and self._sets >= self._ph["sets"]:
            self.machine.events.post("multiball_%s_ended" % self._cfg["key"])
            self.stop()


SHOT_OF = {"s_left_ramp_exit": "left_ramp", "s_right_ramp_exit": "right_ramp", "s_left_loop": "left_loop",
           "s_right_loop": "right_loop", "s_kickback": "kickback",
           "s_3_bank_drop_tgt_top": "bank", "s_3_bank_drop_tgt_mid": "bank", "s_3_bank_drop_tgt_btm": "bank",
           "s_right_2_bank_top": "right2", "s_right_2_bank_bottom": "right2"}
WHC_SHOTS = ("left_ramp", "right_ramp", "left_loop", "right_loop", "kickback", "bank", "right2")      # H: Winter shot mask 0xEF (docs/06)
LIEUTENANT_NEEDED = 5


class WinterHasComeMode(AwardMode):
    """Four-ball mini wizard (rulesheet, M). Horde: all seven major shots lit, each collected once; the last one starts
    Lieutenant: three hurry-up shots on random majors, replaced as they are collected; five collected pay the Winter
    Super Jackpot (the total the Winter Is Coming hurry-ups fed into got_winter_super) and return to Horde. Not modelled:
    the Horde timer adding shots, Lieutenant timeouts and the frozen left flipper."""

    rng = None

    def mode_start(self, **kwargs):
        import random
        super().mode_start(**kwargs)
        self.rng = self.rng or random.Random()
        self._phase = "horde"
        self._horde = set()
        self._lieutenant = set()
        self._collected = 0
        self._shots = 0

    def _accepts(self, sw):
        self._shots = 0
        shot = SHOT_OF.get(sw)
        if shot is None:
            return False
        if self._phase == "horde":
            if shot in self._horde:
                return False
            self._horde.add(shot)
            if self._horde >= set(WHC_SHOTS):
                self._start_lieutenant()
            return True
        if shot in self._lieutenant:
            self._lieutenant.discard(shot)
            self._collected += 1
            if self._collected >= LIEUTENANT_NEEDED:
                self._pay_super()
            else:
                self._add_lieutenant_shot()
            return True
        return False

    def _start_lieutenant(self):
        self._phase = "lieutenant"
        self._collected = 0
        self._lieutenant = set()
        while len(self._lieutenant) < 3:
            self._add_lieutenant_shot()
        self.machine.events.post("got_winter_has_come_lieutenant")

    def _add_lieutenant_shot(self):
        pool = [s for s in WHC_SHOTS if s not in self._lieutenant]
        self._lieutenant.add(self.rng.choice(pool))

    def _pay_super(self):
        p = self.player
        points = int(p.got_winter_super or 0) * (p.got_multiplier or 1)
        p.score += points
        p.got_winter_super = 0
        self.machine.events.post("got_winter_has_come_super", points=points)
        self._phase, self._horde, self._lieutenant = "horde", set(), set()
        self.machine.events.post("got_winter_has_come_horde")
