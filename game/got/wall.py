"""Battle for the Wall multiball on the ROM's cwall state machine (Game-of-Thrones docs/26, data/cwall_*.csv; H logic).

Phase 0 ramps (left/right ramp exit), phase 1 orbits (left/right loop), each pays a jackpot and counts to 3; then phase 2: the kickback pays the
super jackpot and the mode goes to the phase not visited last (ramps -> orbits -> ramps ...). No timer; it ends when the balls drain."""
from got import state
from got.award_mode import AwardMode

PHASE_SHOTS = {0: ("s_left_ramp_exit", "s_right_ramp_exit"), 1: ("s_left_loop", "s_right_loop"), 2: ("s_kickback",)}
JACKPOTS_PER_PHASE = 3
SUPER_EXTRA = 10000000                         # + 20,000,000 when the house-select instance returns 2 (not modelled)


class WallMode(AwardMode):
    own_args = True
    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        p = self.player
        p.got_award_wall = int(p.got_award_wall or self._cfg["award"]["start"])
        self._phase, self._prev, self._count = 0, 0, 0
        self._publish()
        self.machine.events.post("got_wall_bg_show")

    def _value(self):
        return int(self.player.got_award_wall or self._cfg["award"]["start"])

    def _bump(self):
        a = self._cfg["award"]
        v = self._value() + int(a["bump"])
        self.player.got_award_wall = min(int(a["cap"]), v) if a.get("cap") else v

    def _publish(self, **kwargs):
        v = self.machine.variables
        v.set_machine_var("got_wall_phase", str(self._phase + 1))
        v.set_machine_var("got_arg_shots", str(max(0, JACKPOTS_PER_PHASE - self._count)))
        v.set_machine_var("got_arg_score", "{:,}".format(int(self.player.score)))

    def _shot(self, sw=None, **kwargs):
        if state.fast_loop(self.machine, sw) or sw not in PHASE_SHOTS[self._phase]:
            return
        p = self.player
        if self._phase == 2:                                              # AwardSuperJackpot (static, then BumpAward)
            points = (self._value() + SUPER_EXTRA) * int(p.got_multiplier or 1)
            p.score += points
            self._bump()
            self._count = 0
            self._phase = 1 if self._prev == 0 else 0
            self.machine.events.post("got_wall_super", points=points)
        else:                                                             # AwardJackpot = GiveAward(award 11, combo, 1): pays then bumps
            points = self._value() * int(p.got_combo_mult or 1) * int(p.got_multiplier or 1)
            p.score += points
            self._bump()
            self._count += 1
            self.machine.events.post("got_wall_award", points=points)
            if self._count >= JACKPOTS_PER_PHASE:
                self._prev, self._phase = self._phase, 2
        self._last_points = points
        self._publish()

    def mode_stop(self, **kwargs):
        self.machine.events.post("got_wall_bg_hide")
        super().mode_stop(**kwargs)
        self.player.got_award_wall = int(self._cfg["award"]["start"])      # Stop resets award 11 to its initial values
