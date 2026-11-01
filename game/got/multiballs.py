"""Multiball phases: shot sets that light a Super Jackpot at the battering ram. Rules: community rulesheet (pinballrulesheets.com
rev 1.37) over the ROM award values; the set/ram structure is M, the Super multiplier is a placeholder (CFG: the ROM's
AwardSuperJackpot formula is not recovered)."""
from got.award_mode import AwardMode
from got.combos import jackpot_value
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
        self._sets_needed = self._ph["sets"]
        if self._cfg["key"] == "hand_of_the_king":      # GetTotalLevelsNeeded: 2 with the Greyjoy bit, else 3 (docs/13)
            prog = self.player.got_progression
            self._sets_needed = 2 if prog and 4 in prog.complete else 3

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
        if self._sets_needed and self._sets >= self._sets_needed:
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


class BlackwaterMode(AwardMode):
    """docs/13 (H): rounds R = 1, 2, 3 (then 3 again). Every round arms the five mask-0x6e shots R times each (5, 10, 15 hits);
    a hit pays V x combo x R (V does not rise); the last hit of the round lights the Super Jackpot (level R) for 20 s + 1.4 s
    grace; a ram shot collects V x 6 x R + 10M, otherwise the window expires; then the next round starts. V =
    CalcJackpotValue(wildfire points) is set at the start (cblackwater::Start)."""

    SHOTS = ("s_left_loop", "s_kickback", "s_left_ramp_exit", "s_right_ramp_exit", "s_right_loop")
    SUPER_S = 20 + 93 / 66.0

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        p = self.player
        p.got_bw_jackpot = jackpot_value(int(p.got_wildfire or 0))
        self._round = 1
        self._arm()

    def _arm(self):
        self._left = {sw: self._round for sw in self.SHOTS}
        self._super = 0
        self.machine.events.post("got_blackwater_round", round=self._round)

    def _shot(self, sw=None, **kwargs):
        p = self.player
        if sw == RAM and self._super:
            level = self._super
            self.delay.remove("bw_super")
            points = (int(p.got_bw_jackpot) * 6 * level + 10000000) * (p.got_multiplier or 1)
            p.score += points
            self.machine.events.post("got_blackwater_super", points=points, level=level)
            self._next_round()
            return
        if self._super or self._left.get(sw, 0) <= 0:
            return
        self._left[sw] -= 1
        points = int(p.got_bw_jackpot) * (p.got_combo_mult or 1) * self._round * (p.got_multiplier or 1)
        p.score += points
        self.machine.events.post("got_blackwater_jackpot", points=points, round=self._round)
        if not any(self._left.values()):
            self._super = self._round
            self.delay.add(int(self.SUPER_S * 1000), self._super_expired, name="bw_super")
            self.machine.events.post("got_blackwater_super_lit", level=self._super)

    def _super_expired(self, **kwargs):
        self._next_round()

    def _next_round(self):
        self._round = min(self._round + 1, 3)
        self._arm()
