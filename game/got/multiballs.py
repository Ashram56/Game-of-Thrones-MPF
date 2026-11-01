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
