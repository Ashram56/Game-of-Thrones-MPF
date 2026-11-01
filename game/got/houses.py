"""House modes with their own shot logic. Rules: community rulesheet (pinballrulesheets.com, code rev 1.37) over the ROM
data of Game-of-Thrones docs/03, 06-08; confidence M unless the ROM data says otherwise (award values and timers are ROM)."""
from got.award_mode import AwardMode

RAMPS = ("s_left_ramp_exit", "s_right_ramp_exit")
ORBITS = ("s_left_loop", "s_right_loop")
ORBIT_WINDOW_S = 10                 # rulesheet: three orbit shots within 10 seconds, refreshed after the second


class StarkMode(AwardMode):
    """Ramp shots advance the kill list (each bumps the value); after 3 ramp shots a left or right orbit collects the
    payoff and finishes the mode. Greyjoy's extra requirements are not modelled."""

    RAMPS_NEEDED = 3

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._ramps = 0

    def _accepts(self, sw):
        if sw in RAMPS:
            self._ramps += 1
            self._award.bump()
            setattr(self.player, self._award_key, self._award.value)
            self.machine.events.post("got_stark_kill", count=self._ramps)
            return False
        if sw in ORBITS and self._ramps >= self.RAMPS_NEEDED:
            return True                 # the payoff: normal award path, then the house completes
        return False

    def _shot(self, sw=None, **kwargs):
        self._shots = self._cfg["shots_to_complete"] - 1       # one collected shot completes the house
        super()._shot(sw=sw, **kwargs)


class MartellMode(AwardMode):
    """Three orbit shots within 10 s (the window refreshes after the second) build the hurry-up; either ramp then collects
    it (decaying with the mode timer) and finishes the mode."""

    ORBITS_NEEDED = 3

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._orbits = 0
        self._last = None

    def _accepts(self, sw):
        now = self.machine.clock.get_time()
        if sw in ORBITS:
            if self._last is not None and now - self._last > ORBIT_WINDOW_S and self._orbits < 2:
                self._orbits = 0                                   # window missed: start the count again
            self._orbits += 1
            self._last = now
            self._award.bump()
            setattr(self.player, self._award_key, self._award.value)
            self.machine.events.post("got_martell_orbit", count=self._orbits)
            return False
        return sw in RAMPS and self._orbits >= self.ORBITS_NEEDED

    def _shot(self, sw=None, **kwargs):
        self._shots = self._cfg["shots_to_complete"] - 1
        super()._shot(sw=sw, **kwargs)
