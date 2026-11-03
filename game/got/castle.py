"""Castle multiball on the ROM's cmball_castle state machine (Game-of-Thrones docs/28, data/cmball_castle_*.csv; H logic).

Three kinds of shot (cmball_castle::ShotMade): a main shot (mask 110) pays award 12 x combo; a standup (0x700000) pays award 12 x upper multiplier;
once the standups are done the two upper rollovers pay the super jackpot (award 13), the first one also adds a ball, and the standups re-arm.
Every award 12 payment bumps it by 250,000 (cap 10M) and bumps the super jackpot by 750,000 (cap 50M). No timer; ends when the balls drain."""
from got import state
from got.award_mode import AwardMode

MAIN = ("s_left_loop", "s_kickback", "s_left_ramp_exit", "s_right_ramp_exit", "s_right_loop")          # mask 110
STANDUPS = ("s_u_p_left_target", "s_u_p_center_target", "s_u_p_right_target")                           # 0x700000
ROLLOVERS = ("s_u_p_left_rollover", "s_u_p_right_rollover")                                             # 0x1800000
AWARD, AWARD_BUMP, AWARD_CAP = 5000000, 250000, 10000000                                                # award 12 (ResetAwards)
SUPER, SUPER_BUMP, SUPER_CAP, DRAGON_SUPER_BUMP = 20000000, 10000000, 50000000, 750000                  # award 13
UPPER_MULT = 1                                                                                          # get_upper_playfiled_multiplier (M)


class CastleMode(AwardMode):
    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._v12, self._v13 = AWARD, SUPER                                  # ResetAwards at every Start
        self._main, self._standups, self._rollovers = set(MAIN), set(STANDUPS), set()
        self._ball_added = False
        self._publish()
        self.machine.events.post("got_castle_bg_show")

    def _publish(self):
        v = self.machine.variables
        v.set_machine_var("got_arg_score", "{:,}".format(int(self.player.score)))
        v.set_machine_var("got_arg_award", "{:,}".format(self._v13))

    def _dragon(self, mult):
        p = self.player
        points = self._v12 * mult * int(p.got_multiplier or 1)
        p.score += points
        self._v12 = min(AWARD_CAP, self._v12 + AWARD_BUMP)
        self._v13 = min(SUPER_CAP, self._v13 + DRAGON_SUPER_BUMP)
        self.machine.events.post("got_castle_award", points=points)

    def _shot(self, sw=None, **kwargs):
        if state.fast_loop(self.machine, sw):
            return
        p = self.player
        if sw in self._rollovers:                                            # AwardSuperJackpot(upper multiplier)
            points = self._v13 * UPPER_MULT * int(p.got_multiplier or 1)
            p.score += points
            self._v13 = min(SUPER_CAP, self._v13 + SUPER_BUMP)
            self.machine.events.post("got_castle_super", points=points)
            if not self._ball_added:                                         # first super jackpot of the multiball: BALL ADDED
                self._ball_added = True
                self._add_ball()
            self._rollovers, self._standups = set(), set(STANDUPS)
        elif sw in self._standups:
            self._standups.discard(sw)
            self._dragon(UPPER_MULT)
            if not self._standups:
                self._rollovers = set(ROLLOVERS)
        elif sw in self._main:
            self._main.discard(sw)
            self._dragon(int(p.got_combo_mult or 1))
            if not self._main:
                self._main = set(MAIN)
        else:
            return
        self._publish()

    def _add_ball(self):
        try:
            self.machine.multiballs["mb_castle"].add_a_ball()
        except Exception:
            self.machine.playfield.add_ball(1)
        self.machine.events.post("got_add_a_ball")

    def mode_stop(self, **kwargs):
        self.machine.events.post("got_castle_bg_hide")
        super().mode_stop(**kwargs)
