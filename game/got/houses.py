"""House modes with their own shot logic. Rules: community rulesheet (pinballrulesheets.com, code rev 1.37) over the ROM
data of Game-of-Thrones docs/03, 06-08; confidence M unless the ROM data says otherwise (award values and timers are ROM)."""
from got import state
from got.award_mode import AwardMode

RAMPS = ("s_left_ramp_exit", "s_right_ramp_exit")
ORBITS = ("s_left_loop", "s_right_loop")
ORBIT_WINDOW_S = 10                 # rulesheet: three orbit shots within 10 seconds, refreshed after the second


KICK = "s_kickback"
LOOP_L, LOOP_R = "s_left_loop", "s_right_loop"
RAMP_L, RAMP_R = "s_left_ramp_exit", "s_right_ramp_exit"
BANK = ("s_3_bank_drop_tgt_top", "s_3_bank_drop_tgt_mid", "s_3_bank_drop_tgt_btm")
BANK2 = ("s_right_2_bank_top", "s_right_2_bank_bottom")


class RomHouse(AwardMode):
    """Shared payment of the ROM house classes (docs/30): GiveAward(award, combo, bump) and Complete."""

    def _give(self, bump=True, complete=False, stage=1):
        points = self._award.give(global_mult=self._gm())
        self.player.score += points
        self._last_points = points
        if bump:
            self._award.bump()
        setattr(self.player, self._award_key, self._award.value)
        self.machine.events.post("got_%s_award" % self._cfg["key"], points=points, stage=stage)
        if complete:
            self.machine.events.post("got_house_complete", house_id=self._cfg["id"], key=self._cfg["key"])
            self.stop()
        return points

    def _build(self):
        self._award.bump()
        setattr(self.player, self._award_key, self._award.value)

    def _shot(self, sw=None, **kwargs):
        if state.fast_loop(self.machine, sw):
            return
        self._hit(sw)


class MartellMode(RomHouse):
    """cmartell (docs/30 section 8): orbits build (each restarts the 10 s mini timer and adds 12 s to the 30 s main timer, hits 1 and 2 pay
    nothing); the mini timer running out resets the count and the value; the 3rd orbit pays the value and starts the hurry-up (ramps, 15 s,
    decaying), a ramp pays the decayed value and completes."""

    MINI_S, ADD_S, MAIN_S, HURRY_S = 10, 12, 30, 15

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._orbits, self._hurry = 0, False
        self._start_value = self._award.value

    def _hit(self, sw):
        timer = self.machine.timers["martell_timer"]
        if not self._hurry and sw in ORBITS:
            self._orbits += 1
            self.delay.remove("martell_mini")
            self.delay.add(self.MINI_S * 1000, self._mini_expired, name="martell_mini")
            timer.ticks = min(self.MAIN_S, int(timer.ticks) + self.ADD_S)
            self._award.bump()
            setattr(self.player, self._award_key, self._award.value)
            self.machine.events.post("got_martell_orbit", count=self._orbits)
            if self._orbits >= 3:
                self.delay.remove("martell_mini")
                self._hurry = True
                timer.ticks = self.HURRY_S
                self._give(bump=False)
            return
        if self._hurry and sw in RAMPS:
            points = int(self._award.hurry_up(timer.ticks, self.HURRY_S)) * self._gm()
            self.player.score += points
            self._last_points = points
            self.machine.events.post("got_martell_award", points=points)
            self._award.bump()
            setattr(self.player, self._award_key, self._award.value)
            self.machine.events.post("got_house_complete", house_id=self._cfg["id"], key=self._cfg["key"])
            self.stop()

    def _mini_expired(self, **kwargs):                           # OnGraceMini: the count and the value start again
        self._orbits = 0
        self._award.value = self._start_value
        setattr(self.player, self._award_key, self._award.value)

    def mode_stop(self, **kwargs):
        self.delay.remove("martell_mini")
        super().mode_stop(**kwargs)


GREYJOY_SHOTS = (RAMP_L, RAMP_R, LOOP_L, LOOP_R, KICK)      # H: mask 0x6e (docs/13)
MAINS = (RAMP_L, RAMP_R, LOOP_L, LOOP_R)


class StarkMode(RomHouse):
    """cstark (docs/30 section 3): ramps build (+375,000, the kill list advances), from the 3rd ramp an orbit pays value x combo and completes."""

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._ramps = 0

    def _hit(self, sw):
        if sw in RAMPS:
            self._ramps += 1
            self._build()
            self.machine.events.post("got_stark_kill", count=self._ramps)
            idx = int(getattr(self.machine, "got_stark_kill_idx", 0))       # the ROM's global build_order_kill_list (0x47e6c8), cycled 0..10
            self.machine.got_stark_kill_idx = (idx + 1) % 11
            self.machine.events.post("got_def_build_stark_%d" % idx)
        elif sw in ORBITS and self._ramps >= 3:
            self._give(bump=False, complete=True)


class BaratheonMode(RomHouse):
    """cbaratheon (docs/30 section 4): a ladder. Active at the start: spinner and left loop; each builds and adds the kickback; the kickback
    adds the left ramp; the left ramp adds the left 3-bank; a 3-bank shot pays the value x combo and completes. Earlier shots keep building."""

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._active = {"s_left_spinner", LOOP_L}

    def _hit(self, sw):
        if sw in BANK:
            if sw in self._active:
                self._give(bump=False, complete=True)
            return
        if sw not in self._active:
            return
        self._build()
        if sw in ("s_left_spinner", LOOP_L):
            self._active.add(KICK)
        elif sw == KICK:
            self._active.add(RAMP_L)
        elif sw == RAMP_L:
            self._active.update(BANK)


RED_OF = {"s_target_1": (LOOP_L, KICK), "s_target_2": (KICK, RAMP_L), "s_target_3": (RAMP_L, RAMP_R),
          "s_target_4": (RAMP_L, RAMP_R), "s_target_5": (RAMP_R, LOOP_R)}


class LannisterMode(RomHouse):
    """clannister (docs/30 section 5): five standups; a hit builds (+75,000), removes the target and lights its two neighbouring red shots; a lit
    red shot pays the value x combo (bump); five red shots complete (+200 gold, done by the manager)."""

    SHOTS_NEEDED = 5

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._targets, self._red, self._made = set(RED_OF), set(), 0

    @property
    def shots_left(self):
        return max(0, self.SHOTS_NEEDED - self._made)

    def _hit(self, sw):
        if sw in self._targets:
            self._targets.discard(sw)
            self._build()
            self._red.update(RED_OF[sw])
        elif sw in self._red:
            self._red.discard(sw)
            self._made += 1
            self._give(bump=True, complete=self._made >= self.SHOTS_NEEDED)


class GreyjoyMode(RomHouse):
    """cgreyjoy (docs/30 section 6): five shots in any order, each pays (bump) and adds 10 s to the 15 s timer (cap 15); the fifth pays again and completes."""

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._done = set()

    @property
    def shots_left(self):
        return len(GREYJOY_SHOTS) - len(self._done)

    def _hit(self, sw):
        if sw in self._done or sw not in GREYJOY_SHOTS:
            return
        self._done.add(sw)
        self._give(bump=True)
        timer = self.machine.timers["greyjoy_timer"]
        timer.ticks = min(15, int(timer.ticks) + 10)
        if len(self._done) >= len(GREYJOY_SHOTS):
            self._give(bump=True, complete=True)                  # the last shot pays a second GiveAward


class TyrellMode(RomHouse):
    """ctyrell (docs/30 section 7): run shots 4, 8, 32 (kickback, left and right ramp) pay and make the right 2-bank the target; a 2-bank hit pays,
    counts and re-arms the run shots (8, 32 after hit 1; 32 after hit 2); the 3rd bank hit pays and completes."""

    RUN_AFTER = {0: (KICK, RAMP_L, RAMP_R), 1: (RAMP_L, RAMP_R), 2: (RAMP_R,)}

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._hits = 0
        self._run = set(self.RUN_AFTER[0])
        self._bank = False

    def _hit(self, sw):
        if sw in self._run:
            self._run = set()
            self._bank = True
            self._give(bump=True)
        elif self._bank and sw in BANK2:
            self._hits += 1
            self._bank = False
            if self._hits >= 3:
                self._give(bump=True, complete=True, stage=2)
                return
            self._run = set(self.RUN_AFTER[self._hits])
            self._give(bump=True, stage=2)


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
        self.machine.variables.set_machine_var("got_dragon_page", self._dragon + 1)
        self.machine.events.post("got_targaryen_dragon_started", dragon=self._dragon)      # def_targaryen_start_1/2/3 (effects 92-94)
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
        if state.fast_loop(self.machine, sw):
            return
        if not self._accepts(sw):
            return
        timer = self.machine.timers["targaryen_timer"]
        value = int(self._award.hurry_up(timer.ticks, self._timer_s)) * self._gm()
        self._done.add(sw)
        if self._dragon < 2:
            self.player.score += value
            self.machine.events.post("got_targaryen_award", points=value, dragon=self._dragon)
            self._step += 1
            if self._step >= len(self._values()):
                self._dragon_defeated()
                return
        elif self._step < len(DROGON_VALUES):                         # hurry-up: banked, 10 HP, more time
            self._banked += value
            self._hp -= DROGON_HURRYUP_HP
            self._step += 1
            self.machine.events.post("got_targaryen_award", points=value, dragon=self._dragon)
            timer.ticks = min(self._timer_s, timer.ticks + 10)
        else:                                                         # final shot: the bank is paid, 20 HP
            self.player.score += self._banked
            self.machine.events.post("got_targaryen_award", points=self._banked, dragon=self._dragon)
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
            self.machine.events.post("got_def_targaryen_timer_end")        # ctargaryen::OnDragonLevelThreeEnd (def_callers)
            self._step, self._done = 0, set()
            self._lit = self._lit_shots()
            self._set_value()
            timer = self.machine.timers["targaryen_timer"]
            timer.ticks = self._timer_s
            timer.start()
            return
        self.stop()
