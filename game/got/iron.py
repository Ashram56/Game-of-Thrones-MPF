"""Iron Throne multiball on the ROM's ciron state machine (Game-of-Thrones docs/23, data/ciron_*.csv; H states and transitions, M multipliers).

State 0 choose a castle (any shot of the per-player remaining-castle mask), 1 defeat it (all 7 shot groups once), 2 battering-ram super jackpot
(+1 ball), 3 King's Landing final ram, 4 the tour (random 3-group masks, 22 castles, until the balls drain)."""
import random

from got import state
from got.award_mode import AwardMode
from got.rules_core import Award

SW_GROUP = {"s_left_loop": "left_loop", "s_kickback": "kickback", "s_left_ramp_exit": "left_ramp", "s_right_ramp_exit": "right_ramp",
            "s_right_loop": "right_loop", "s_right_2_bank_top": "bank2", "s_right_2_bank_bottom": "bank2",
            "s_3_bank_drop_tgt_top": "bank3", "s_3_bank_drop_tgt_mid": "bank3", "s_3_bank_drop_tgt_btm": "bank3",
            "s_battering_ram": "ram"}
SHOT_GROUPS = ("bank3", "left_loop", "kickback", "left_ramp", "right_ramp", "right_loop", "bank2")      # mask 0x3e0ef
CASTLE = {"right_ramp": 0, "bank2": 1, "left_loop": 2, "right_loop": 4, "bank3": 5, "kickback": 6, "left_ramp": 7}   # GetCastleFromShotID
KINGS_LANDING = 3
TOUR_LAST = 21
# data/ciron_tour_masks.csv (0x28e4a0), picked with sys_random_bounded(20)
TOUR_MASKS = (("bank3", "left_loop", "left_ramp"), ("bank3", "left_loop", "right_ramp"), ("bank3", "left_loop", "right_loop"),
              ("bank3", "left_loop", "bank2"), ("bank3", "left_ramp", "right_ramp"), ("bank3", "left_ramp", "right_loop"),
              ("bank3", "left_ramp", "bank2"), ("bank3", "right_ramp", "right_loop"), ("bank3", "right_ramp", "bank2"),
              ("bank3", "right_loop", "bank2"), ("left_loop", "left_ramp", "right_ramp"), ("left_loop", "left_ramp", "right_loop"),
              ("left_loop", "left_ramp", "bank2"), ("left_loop", "right_ramp", "right_loop"), ("left_loop", "right_ramp", "bank2"),
              ("left_loop", "right_loop", "bank2"), ("left_ramp", "right_ramp", "right_loop"), ("left_ramp", "right_ramp", "bank2"),
              ("left_ramp", "right_loop", "bank2"), ("right_ramp", "right_loop", "bank2"))


class IronThroneMode(AwardMode):
    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        p = self.player
        self._sj = Award(10000000, 1250000, 50000000)                    # award 16 (super), 15 is self._award
        self._lowwater = 5000000                                          # GiveLowWaterMarkAward(15): the start value
        saved = p.got_iron_remaining
        remaining = [g for g in (saved if isinstance(saved, str) else "").split(",") if g and g != "-"]
        if not isinstance(saved, str):
            remaining = list(SHOT_GROUPS)
        if not remaining and int(p.got_iron_state or 0) in (0, 1, 2):
            remaining = list(SHOT_GROUPS)                                 # a new run after all castles were taken (inferred)
        self._remaining = set(remaining)
        self._state = int(p.got_iron_state or 0)
        self._picked = None
        self._tour = 0                                                    # ResetTourIndex at Start
        self._set_mask()

    def _set_mask(self):
        s = self._state
        if s == 0:
            self._mask = set(self._remaining)
        elif s == 1:
            self._mask = set(SHOT_GROUPS)
        elif s in (2, 3):
            self._mask = {"ram"}
        else:
            self._mask = set(random.choice(TOUR_MASKS))
        self.player.got_iron_state = self._state
        self.player.got_iron_remaining = ",".join(sorted(self._remaining)) or "-"

    def _mult(self, extra=0):
        balls = int(getattr(self.machine.game, "balls_in_play", 1) or 1) if self.machine.game else 1
        return balls + int(self.player.got_combo_mult or 1) - 1 + extra

    def _pay_award(self, award, mult, bump):
        if bump:
            award.bump()
        points = award.value * mult * int(self.player.got_multiplier or 1)
        self.player.score += points
        self._last_points = points
        return points

    def _castle_effect(self, idx):
        self.machine.events.post("got_def_award_iron_%d" % idx)
        self.machine.events.post("got_iron_award")                     # lamp effect 91 (state 0 pick, each state-1 shot)

    def _shot(self, sw=None, **kwargs):
        if state.fast_loop(self.machine, sw):
            return
        g = SW_GROUP.get(sw)
        if g is None or g not in self._mask:
            return
        s = prev = self._state
        if s == 0:
            self._picked = g
            self._castle = CASTLE[g]
            self._remaining.discard(g)
            points = self._lowwater * self._mult() * int(self.player.got_multiplier or 1)
            self.player.score += points
            self._state = 1
            self._castle_effect(self._castle)
        elif s == 1:
            self._mask.discard(g)
            left = len(self._mask)
            if g == self._picked:
                self._pay_award(self._award, self._mult(6 - left), True)
                self._picked = None
            else:
                self._pay_award(self._award, self._mult(), True)
            self._castle_effect(self._castle)
            if not self._mask:
                self._state = 2
        elif s == 2:
            self._pay_award(self._sj, self._mult(), True)
            self.machine.events.post("got_iron_throne_super", points=self._last_points)
            self.machine.events.post("got_iron_super_lamps")               # lamp effect 92
            self._add_ball()
            if not self._remaining:
                self._state = 3
                self._castle = KINGS_LANDING
                self._castle_effect(KINGS_LANDING)
            else:
                self._state = 0
        elif s == 3:
            self._pay_award(self._sj, self._mult(2), False)
            self.machine.events.post("got_iron_throne_completed")
            self.machine.events.post("got_iron_super_lamps")               # lamp effect 92 (state 3 ram)
            balls = int(getattr(self.machine.game, "balls_in_play", 1) or 1) if self.machine.game else 1
            self._state = 4 if balls > 1 else 0
            if self._state == 0:
                self._remaining = set()
        else:
            self._mask.discard(g)
            self._pay_award(self._award, self._mult(), True)
            if self._mask:
                self.machine.events.post("got_def_iron_tour_award_%d" % self._tour)
                return
            self._tour += 1
            if self._tour > TOUR_LAST:
                self._tour = 0
            self.machine.events.post("got_def_iron_tour_award_%d" % self._tour)
        if self._state != prev or (self._state == 4 and not self._mask):
            self._set_mask()                       # a new state (or the next tour mask) installs its shot mask
        else:
            self._save()

    def _save(self):
        self.player.got_iron_state = self._state
        self.player.got_iron_remaining = ",".join(sorted(self._remaining)) or "-"

    def _add_ball(self):
        try:
            self.machine.multiballs["mb_iron_throne"].add_a_ball()
        except Exception:                                                  # multiball not running (tests)
            self.machine.playfield.add_ball(1)

    def mode_stop(self, **kwargs):
        self.player.got_iron_state = self._state
        super().mode_stop(**kwargs)
