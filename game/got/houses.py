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


MAINS = ("s_left_ramp_exit", "s_right_ramp_exit", "s_left_loop", "s_right_loop")
BANK = ("s_3_bank_drop_tgt_top", "s_3_bank_drop_tgt_mid", "s_3_bank_drop_tgt_btm")


class BaratheonMode(AwardMode):
    """Spinner hits build the value; completing the left 3-bank cashes it in (rulesheet, M). The shield/dragon cue is not shown."""

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._bank = set()

    def _accepts(self, sw):
        if sw == "s_left_spinner":
            self._award.bump()
            setattr(self.player, self._award_key, self._award.value)
            return False
        self._bank.add(sw)
        return self._bank >= set(BANK)

    def _shot(self, sw=None, **kwargs):
        self._shots = self._cfg["shots_to_complete"] - 1
        super()._shot(sw=sw, **kwargs)


class LannisterMode(AwardMode):
    """Gold standups raise the shot value and light a shot; five lit main shots end the mode (rulesheet, M: the target to
    adjacent-shot geometry is simplified to 'a gold target gives credit for one main shot')."""

    SHOTS_NEEDED = 5

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._lit = 0
        self._made = 0

    def _accepts(self, sw):
        if sw.startswith("s_target_"):
            self._lit += 1
            self._award.bump()
            setattr(self.player, self._award_key, self._award.value)
            return False
        if sw in MAINS and self._lit > 0:
            self._lit -= 1
            self._made += 1
            self._shots = self._cfg["shots_to_complete"] - 1 if self._made >= self.SHOTS_NEEDED else 0
            return True
        return False


class GreyjoyMode(AwardMode):
    """All main shots are lit; each is collected once, every completed shot refreshes the 15 s timer; all four complete the
    mode (rulesheet, M)."""

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._done = set()

    def _accepts(self, sw):
        if sw in self._done or sw not in MAINS:
            return False
        self._done.add(sw)
        timer = self.machine.timers["greyjoy_timer"]
        timer.reset()
        timer.start()
        return True

    def _shot(self, sw=None, **kwargs):
        self._shots = 0
        super()._shot(sw=sw, **kwargs)
        if len(self._done) >= len(MAINS) and self.active:
            self.machine.events.post("got_house_complete", house_id=self._cfg["id"], key=self._cfg["key"])
            self.stop()


class TyrellMode(AwardMode):
    """Cycle 1: both ramps; the right 2-bank (lock targets) then lights the ramps again; cycle 2: the right ramp finishes
    (rulesheet, M: the dragon shot and Greyjoy's extra shots are not modelled)."""

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._phase = 0
        self._seen = set()

    def _accepts(self, sw):
        ramps = ("s_left_ramp_exit", "s_right_ramp_exit")
        bank = ("s_right_2_bank_top", "s_right_2_bank_bottom")
        self._shots = 0                       # only the last step completes the house
        if self._phase == 0 and sw in ramps:
            self._seen.add(sw)
            if self._seen >= set(ramps):
                self._phase, self._seen = 1, set()
            return True
        if self._phase == 1 and sw in bank:
            self._seen.add(sw)
            if self._seen >= set(bank):
                self._phase = 2
            return True
        if self._phase == 2 and sw == "s_right_ramp_exit":
            self._shots = self._cfg["shots_to_complete"] - 1
            return True
        return False
