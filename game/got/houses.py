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


GREYJOY_SHOTS = ("s_left_ramp_exit", "s_right_ramp_exit", "s_left_loop", "s_right_loop", "s_kickback")      # H: mask 0x6e (docs/13)
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

    @property
    def shots_left(self):
        return max(0, self.SHOTS_NEEDED - self._made)

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
    """All main shots are lit; each is collected once, every completed shot refreshes the 15 s timer; all five complete (ELF mask 0x6e) the
    mode (rulesheet, M)."""

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._done = set()

    @property
    def shots_left(self):
        return len(GREYJOY_SHOTS) - len(self._done)

    def _accepts(self, sw):
        if sw in self._done or sw not in GREYJOY_SHOTS:
            return False
        self._done.add(sw)
        timer = self.machine.timers["greyjoy_timer"]
        timer.reset()
        timer.start()
        return True

    def _shot(self, sw=None, **kwargs):
        self._shots = 0
        super()._shot(sw=sw, **kwargs)
        if len(self._done) >= len(GREYJOY_SHOTS) and self.active:
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


VISERION_VALUES = (8000000, 10000000, 12000000)               # H (docs/18 2.2): SetHurryUpAwardValue per step, 3 hurry-ups
RHAEGAL_VALUES = (8000000, 10000000, 12000000, 15000000, 25000000)     # 5 hurry-ups
DROGON_VALUES = (10000000, 12000000, 15000000)                 # 3 hurry-ups per wave, then the kickback final shot
DRAGON_SHOT = "s_kickback"                                   # H: ELF shot bit 4 (docs/06); the VPX table uses the castle/wall kicker
DROGON_HP, DROGON_HP_GREYJOY = 150, 180                      # H/M (docs/18 2.3)
DROGON_HURRYUP_HP, DROGON_FINAL_HP = 10, 20
RAMPS = ("s_left_ramp_exit", "s_right_ramp_exit")
LOOPS = ("s_left_loop", "s_right_loop")


class TargaryenMode(AwardMode):
    """Three dragon fights in sequence per player (docs/18 section 2, H unless noted): Viserion (3 hurry-ups: ramps, loops, kickback),
    Rhaegal (5 hurry-ups ending on the kickback), Drogon (150 HP, 180 with Greyjoy: waves of 3 hurry-ups that are banked, 10 HP each,
    then the kickback pays the bank and deals 20 HP; the timer running out cuts the bank by 25% and restarts). Beating Drogon completes
    the house and the cycle restarts. M: which shots are lit after step 2 (any main shot not yet hit), Drogon's random wave masks
    (a random main shot per hurry-up) and the 10 s time extension are simplified; the hurry-up decays over the mode timer."""

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        p = self.player
        self._dragon = min(2, int(p.got_dragon_stage or 0))
        self._step = 0
        self._done = set()
        self._banked = 0
        self._hp = DROGON_HP_GREYJOY if p.got_house == "greyjoy" else DROGON_HP
        self.rng = __import__("random").Random()
        self._timer_s = 20 if self._dragon == 2 else 16
        timer = self.machine.timers["targaryen_timer"]
        timer.stop()
        timer.ticks = self._timer_s
        timer.start()
        self._lit = self._lit_shots()
        self._set_value()

    def _values(self):
        return (VISERION_VALUES, RHAEGAL_VALUES, DROGON_VALUES)[self._dragon]

    def _lit_shots(self):
        n = self._step
        if self._dragon == 2:
            if n >= len(DROGON_VALUES):
                return {DRAGON_SHOT}
            return {self.rng.choice([m for m in MAINS if m != DRAGON_SHOT])}
        if n == len(self._values()) - 1:
            return {DRAGON_SHOT}
        if n == 0:
            return set(RAMPS)
        if n == 1:
            return set(LOOPS)
        return {m for m in MAINS if m not in self._done and m != DRAGON_SHOT}

    def _set_value(self):
        vals = self._values()
        self._award.value = vals[min(self._step, len(vals) - 1)]

    def _accepts(self, sw):
        self._shots = 0
        return sw in self._lit

    def _shot(self, sw=None, **kwargs):
        if not self._accepts(sw):
            return
        timer = self.machine.timers["targaryen_timer"]
        value = int(self._award.hurry_up(timer.ticks, self._timer_s)) * self._gm()
        self._done.add(sw)
        if self._dragon < 2:
            self.player.score += value
            self.machine.events.post("got_targaryen_award", points=value)
            self._step += 1
            if self._step >= len(self._values()):
                self._dragon_defeated()
                return
        elif self._step < len(DROGON_VALUES):                         # hurry-up: banked, 10 HP, more time
            self._banked += value
            self._hp -= DROGON_HURRYUP_HP
            self._step += 1
            self.machine.events.post("got_targaryen_award", points=value)
            timer.ticks = min(self._timer_s, timer.ticks + 10)
        else:                                                         # final shot: the bank is paid, 20 HP
            self.player.score += self._banked
            self.machine.events.post("got_targaryen_award", points=self._banked)
            self._banked = 0
            self._hp -= DROGON_FINAL_HP
            if self._hp <= 0:
                self._dragon_defeated()
                return
            self._step, self._done = 0, set()
        self._lit = self._lit_shots()
        self._set_value()
        self.machine.events.post("got_targaryen_dragon_lit")

    def _dragon_defeated(self):
        if self._dragon < 2:
            self.player.got_dragon_stage = self._dragon + 1
        else:
            self.player.got_dragon_stage = 0
            self.machine.events.post("got_house_complete", house_id=self._cfg["id"], key=self._cfg["key"])
        self.stop()

    def _timeout(self, **kwargs):
        if self._dragon == 2 and self.active:                         # DRAGON FIRE: the bank loses 25%, the wave restarts
            self._banked -= int(self._banked / 4 / 10) * 10
            self._step, self._done = 0, set()
            self._lit = self._lit_shots()
            self._set_value()
            timer = self.machine.timers["targaryen_timer"]
            timer.ticks = self._timer_s
            timer.start()
            return
        self.stop()
