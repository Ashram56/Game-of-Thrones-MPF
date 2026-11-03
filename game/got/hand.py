"""Hand of the King multiball on the ROM's chand state machine (Game-of-Thrones docs/25 and docs/24, data/chand_*.csv; H logic, M durations).

State 1 single shots (the shots of the completed houses; each group once, twice with the Martell bit), 2 battering-ram super jackpot, 3 bonus round
(Stark bit: 20 s of free shots), then after the sets (3, or 2 with the Greyjoy bit) 4 the super-jackpot hurry-up (16 s), which loops back to state 1.
The mode ends only when the balls drain."""
from got import state
from got.award_mode import AwardMode
from got.rules_core import Award

# house id -> its shot group (GetTickleShots: Targaryen 4, Stark 32, Baratheon 1, Lannister 8, Greyjoy 2, Tyrell 128, Martell 64)
HOUSE_SHOT = {0: "kickback", 1: "right_ramp", 2: "bank3", 3: "left_ramp", 4: "left_loop", 5: "bank2", 6: "right_loop"}
SW_GROUP = {"s_left_loop": "left_loop", "s_kickback": "kickback", "s_left_ramp_exit": "left_ramp", "s_right_ramp_exit": "right_ramp",
            "s_right_loop": "right_loop", "s_right_2_bank_top": "bank2", "s_right_2_bank_bottom": "bank2",
            "s_3_bank_drop_tgt_top": "bank3", "s_3_bank_drop_tgt_mid": "bank3", "s_3_bank_drop_tgt_btm": "bank3", "s_battering_ram": "ram"}
ALL_GROUPS = ("bank3", "left_loop", "kickback", "left_ramp", "right_ramp", "right_loop", "bank2")
TARGARYEN, STARK, BARATHEON, LANNISTER, GREYJOY, TYRELL, MARTELL = range(7)
SINGLE_START, SINGLE_STEP, SINGLE_CAP, TARGARYEN_BONUS = 2500000, 175000, 25000000, 500000
BONUS_STEP, BONUS_CAP = 175000, 5000000
TYRELL_SUPER, LANNISTER_HURRY = 15000000, 100000000
BONUS_ROUND_S, HURRY_UP_S = 20, 16
TIMER_SECOND = 66 / 62.0                                    # a timer second is 66 ticks at 62 Hz (docs/24, M)


class HandMode(AwardMode):
    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        prog = self.player.got_progression
        self._houses = set(prog.complete) if prog else set()
        self.machine.events.post("got_hand_started_houses", houses=sorted(self._houses))      # audits 155-161
        self._super_bonus = (LANNISTER_HURRY if LANNISTER in self._houses else 0) + (TYRELL_SUPER if TYRELL in self._houses else 0)
        self._levels_total = 2 if GREYJOY in self._houses else 3
        self._done_hurry = 0                                  # completed hurry-ups (chand+0x7c)
        self._levels_left = self._levels_total
        self._hurry = 0                                       # accumulated super jackpots (chand+0x60)
        self._start_set()

    # --- states
    def _single_value(self):
        v = SINGLE_START + SINGLE_STEP * self._done_hurry + (TARGARYEN_BONUS if TARGARYEN in self._houses else 0)
        return min(v, SINGLE_CAP)

    def _start_set(self):
        self._state = 1
        self._slots = []
        if not hasattr(self, "_levels_left"):
            self._levels_left = self._levels_total
        groups = set(ALL_GROUPS) if BARATHEON in self._houses else {HOUSE_SHOT[h] for h in self._houses if h in HOUSE_SHOT}
        self._mask = groups
        self._hits = {g: (2 if MARTELL in self._houses else 1) for g in groups}
        self._bonus_value = self._single_value()
        self.machine.events.post("got_hand_state", state=1)

    def _start_state(self, s):
        self._state = s
        self.delay.remove("hand_timer")
        if s == 2:
            self._mask = {"ram"}
        elif s == 3:
            self._mask = set(ALL_GROUPS)
            self._bonus_value = self._single_value()
            self.delay.add(int(BONUS_ROUND_S * TIMER_SECOND * 1000), self._bonus_over, "hand_timer")
        elif s == 4:
            self._mask = {"ram"}
            self._hurry_award = Award(self._hurry + (LANNISTER_HURRY if LANNISTER in self._houses else 0))
            self._hurry_start = self._hurry_award.value
            self._hurry_t0 = self.machine.clock.get_time()
            self.delay.add(int(HURRY_UP_S * TIMER_SECOND * 1000), self._hurry_expired, "hand_timer")
        self.machine.events.post("got_hand_state", state=s)

    def _hurry_value(self):
        elapsed = self.machine.clock.get_time() - self._hurry_t0
        a = self._hurry_award
        a.value = self._hurry_start
        return a.hurry_up(max(0, HURRY_UP_S - elapsed), HURRY_UP_S)

    def _end_level(self):
        self._levels_left -= 1
        self.machine.events.post("got_hand_set_complete")        # audit 162
        if self._levels_left > 0:
            self._start_set()
        else:
            self._start_state(4)

    def _end_hurry_up(self):
        self._done_hurry += 1
        self._hurry = 0
        self._levels_left = self._levels_total
        self._start_set()

    def _bonus_over(self, **kwargs):
        if self._state == 3:
            self._end_level()

    def _hurry_expired(self, **kwargs):
        if self._state == 4:
            self._end_hurry_up()

    # --- payments
    def _pay(self, points):
        self.player.score += points
        self._last_points = points

    def _mult(self):
        return int(self.player.got_combo_mult or 1) * int(self.player.got_multiplier or 1)

    def _shot(self, sw=None, **kwargs):
        if state.fast_loop(self.machine, sw):
            return
        g = SW_GROUP.get(sw)
        if g is None or g not in self._mask:
            return
        s = self._state
        if s == 1:
            self._hits[g] -= 1
            if self._hits[g] > 0:
                return                                           # Martell: the first hit only clears the copy
            self._mask.discard(g)
            points = self._single_value() * self._mult()
            self._pay(points)
            self._slots = sorted(self._slots + [points], reverse=True)[:4]     # AddToSuperJackpot keeps the 4 largest
            self.machine.events.post("got_hand_of_the_king_award", points=points)
            if not self._mask:
                self._start_state(2)
        elif s == 2:
            total = sum(self._slots) + (TYRELL_SUPER if TYRELL in self._houses else 0)
            self._pay(total * int(self.player.got_multiplier or 1))
            self._hurry += total
            self._slots = []
            self.machine.events.post("got_hand_of_the_king_super", points=self._last_points)
            if STARK in self._houses:
                self._start_state(3)
            else:
                self.delay.remove("hand_timer")
                self._end_level()
        elif s == 3:
            points = self._bonus_value * self._mult()
            self._pay(points)
            self._bonus_value = min(self._bonus_value + BONUS_STEP, max(BONUS_CAP, self._bonus_value))
            self.machine.events.post("got_hand_of_the_king_award", points=points)
        elif s == 4:
            self._pay(int(self._hurry_value()) * self._mult())
            self.machine.events.post("got_hand_hurry_up", points=self._last_points)      # audit 163
            self.delay.remove("hand_timer")
            self._end_hurry_up()
