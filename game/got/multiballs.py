"""Multiball phases: shot sets that light a Super Jackpot at the battering ram. Rules: community rulesheet (pinballrulesheets.com
rev 1.37) over the ROM award values; the set/ram structure is M, the Super multiplier is a placeholder (CFG: the ROM's
AwardSuperJackpot formula is not recovered)."""
from got import state
from got.award_mode import AwardMode
from got.combos import jackpot_value
from got.phases import PHASES, RAM


# ciron::GetCastleFromShotID (docs data/ciron_castle_shots.csv, H): the castle whose shot was made -> effect def_award_iron idx
CASTLE_OF = {"s_right_ramp_exit": 0, "s_right_2_bank_top": 1, "s_right_2_bank_bottom": 1, "s_left_loop": 2, "s_right_loop": 4,
             "s_3_bank_drop_tgt_top": 5, "s_3_bank_drop_tgt_mid": 5, "s_3_bank_drop_tgt_btm": 5, "s_kickback": 6, "s_left_ramp_exit": 7}


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
            done = set(prog.complete) if prog else set()
            self._house_bits = done
            self.machine.events.post("got_hand_started_houses", houses=sorted(done))   # audits 155-161 (ChalkTheStartAudits, inferred per completed house)
            # docs/18 1.6 (H): completed houses change the Hand of the King
            if 0 in done:                                # Targaryen: +500,000 on the shot value
                self._award.value += 500000
            self._super_bonus = (100000000 if 3 in done else 0) + (15000000 if 5 in done else 0)   # Lannister +100M, Tyrell +15M
        else:
            self._super_bonus = 0

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
            self._last_sw = sw
            return True
        return False

    def _pay(self):
        super()._pay()
        self._set_points += self._last_points
        castle = CASTLE_OF.get(getattr(self, "_last_sw", None)) if self._cfg["key"] == "iron_throne" else None
        if castle is not None:
            self.machine.events.post("got_def_award_iron_%d" % castle)      # the ROM shows the castle's award with its table layout
        if self._done >= set(self._group_shots()):
            window = self._ph["window"]
            self._super_until = 0 if not window else self.machine.clock.get_time() + window
            self.machine.events.post("got_%s_super_lit" % self._cfg["key"])

    def _collect_super(self):
        points = (int(self._set_points * self._ph["super_mult"]) + self._super_bonus) * (self.player.got_multiplier or 1)
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

    @property
    def shots_left(self):
        if self._phase == "horde":
            return len(WHC_SHOTS) - len(self._horde)
        return max(0, LIEUTENANT_NEEDED - self._collected)

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


UPPER_ALL = ("s_u_p_left_target", "s_u_p_center_target", "s_u_p_right_target", "s_u_p_left_rollover", "s_u_p_right_rollover")
UPPER_STATES = (("s_u_p_left_target", "s_u_p_center_target", "s_u_p_right_target"), ("s_u_p_left_target", "s_u_p_right_target"),
                ("s_u_p_center_target",), ("s_u_p_left_rollover", "s_u_p_right_rollover"))      # masks 0x700000 / 0x500000 / 0x200000 / 0x1800000


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
        self._upper = 0
        for sw in UPPER_ALL:
            self.add_mode_event_handler(sw + "_active", self._upper_shot, sw=sw)
        self._arm()

    def _upper_shot(self, sw, **kwargs):
        if state.fast_loop(self.machine, sw):
            return
        """DoUpperPlayfieldWork (docs/14, H masks/order): any standup -> left or right standup -> centre standup -> an upper
        rollover. Steps 0-2 pay a jackpot, step 3 the Super Jackpot (upper multiplier 1: M)."""
        p = self.player
        if sw not in UPPER_STATES[self._upper]:
            return
        v = int(p.got_bw_jackpot)
        if self._upper < 3:
            points = v * self._round * (p.got_multiplier or 1)
            self._upper += 1
        else:
            points = (v * 6 + 10000000) * (p.got_multiplier or 1)
            self._upper = 0
            self.machine.events.post("got_blackwater_super", points=points, level=1)
        p.score += points

    def _arm(self):
        self._left = {sw: self._round for sw in self.SHOTS}
        self._super = 0
        self.machine.events.post("got_blackwater_round", round=self._round)

    def _shot(self, sw=None, **kwargs):
        if state.fast_loop(self.machine, sw):
            return
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
