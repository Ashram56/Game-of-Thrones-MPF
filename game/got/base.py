"""MPF glue: base game mode. Wizard progression and starting the next ready mode. UNVERIFIED against MPF."""
import time

from mpf.core.mode import Mode

from got import state
from got.rules_core import Progression, load_rules


def _now():
    """Local time; the tests replace it. The ROM reads the RTC (sys_rtc_get_current_time)."""
    return time.localtime()


class GotBase(Mode):
    def mode_start(self, **kwargs):
        self._rules = load_rules()
        self.add_mode_event_handler("got_house_complete", self._house_complete)
        self.add_mode_event_handler("s_throne_active", self._start_next_house)
        self.add_mode_event_handler("s_left_ramp_exit_active", self._left_ramp_exit_work)
        for sw in ("s_lock_1", "s_lock_2", "s_lock_3"):          # lock_event_handler event 2: a ball arrives in the lock
            self.add_mode_event_handler(sw + "_active", self._left_ramp_exit_work, lock_entry=True)
        pr = self._rules["progression"]
        # Castle: the three upper standups advance the upper-playfield level; level 4 starts Castle (docs/06, H/M)
        self._standups_hit = set()
        for sw in pr["castle_standups"]:
            self.add_mode_event_handler(sw + "_active", self._standup, sw=sw)
        # Wall: advances counter, lit at min(11, 6 + 5 x advances awarded) (docs/06, H); starts from the elevator kick
        self._bank_hit = set()
        for sw in pr["wall_bank_switches"]:
            self.add_mode_event_handler(sw + "_active", self._bank_switch, sw=sw)
        for sw in pr["wall_advance_switches"]:
            self.add_mode_event_handler(sw + "_active", self._wall_advance)
        self.add_mode_event_handler("s_elevator_popper_active", self._wall_start)
        # Midnight Madness: real-time clock at 00:00, waits up to 10 min for a ball on the playfield (docs/06, H)
        self._madness_day = None
        self.delay.add_if_doesnt_exist(1000, self._madness_check, "madness_check")

    def _progression(self):
        p = self.player
        if not p.got_progression:               # MPF player variables default to 0
            p.got_progression = Progression(
                self._rules, extra_ball_after=int(self.machine.settings.get_setting_value("ad_house_complete_extra_ball")))   # service menu
        return p.got_progression

    def _house_complete(self, house_id, **kwargs):
        for ev in self._progression().house_complete(house_id):
            self.machine.events.post("got_" + ev)

    def _start_next_house(self, **kwargs):
        # Departure (docs/rom_differences.md): the ROM's Choose Your Battle is replaced by "throne starts the next house".
        prog = self._progression()
        for h in self._rules["houses"]:
            if h["id"] not in prog.complete and not self._house_running():
                self.machine.events.post("start_mode_" + h["key"])
                # Winter Is Coming is offered with it when completed + running houses <= 6 (docs/06, SelectModesToStart; H)
                if len(prog.complete & prog.houses) + 1 <= 6 and not self.machine.modes["winter_has_come"].active:
                    self.machine.events.post("start_mode_winter_is_coming")
                return

    def _left_ramp_exit_work(self, lock_entry=False, **kwargs):
        """do_left_ramp_exit_work (0x4ba30, H): Iron Throne is checked first, then Hand of the King, then the Blackwater lock.
        Also run when a ball enters the lock (lock_event_handler event 2)."""
        prog = self._progression()
        if state.iron_startable(self.machine, self.player):
            prog.started.add("iron_throne")
            self.machine.events.post("start_mode_iron_throne")
        elif state.hand_startable(self.machine, self.player):
            prog.started.add("hand_of_the_king")
            self.machine.events.post("start_mode_hand_of_the_king")
        elif lock_entry and not state.multiball_running(self.machine):
            # ROM: Blackwater AwardLock also runs at the ramp exit when the lock is lit; the lit-lock logic (flag 36) is not
            # recovered, so only a ball that physically enters the lock locks here (M).
            self._blackwater_lock()

    def _blackwater_lock(self):
        """cblackwater::AwardLock (H): needs the lock lit, no multiball and Iron not startable; when the player's locked count
        reaches the requirement Blackwater starts. The requirement (3) and the lit-lock logic are M."""
        p = self.player
        p.got_locked_balls += 1
        if p.got_locked_balls >= 3:
            p.got_locked_balls = 0
            self.machine.events.post("start_mode_blackwater")

    def _house_running(self):
        return state.house_running(self.machine)

    def _multiball_running(self):
        return state.multiball_running(self.machine)

    # --- Castle
    def _standup(self, sw, **kwargs):
        pr = self._rules["progression"]
        self._standups_hit.add(sw)
        if self._standups_hit >= set(pr["castle_standups"]):
            self._standups_hit = set()
            p = self.player
            p.got_upper_level += 1
            if p.got_upper_level < pr["castle_start_level"]:
                a = pr["castle_level_award"]          # award #19: 5M, +2.5M per level to 15M (docs/07; bump per level is M)
                level_award = min(a["cap"], a["start"] + a["bump"] * (p.got_upper_level - 1))
                p.score += level_award * (p.got_multiplier or 1)
                self.machine.events.post("got_castle_level_award", level=p.got_upper_level)
            elif not self._multiball_running():
                p.got_upper_level = 0
                self.machine.events.post("start_mode_castle")

    # --- Battle for the Wall
    def _wall_needed(self):
        pr = self._rules["progression"]
        return min(pr["wall_advances_max"], pr["wall_advances_first"] + pr["wall_advances_step"] * self.player.got_wall_awarded)

    def _bank_switch(self, sw, **kwargs):
        # LeftDropTargetBank::bank_complete advances the Wall for Baratheon (docs/06, H; the house condition is M)
        self._bank_hit.add(sw)
        if self._bank_hit >= set(self._rules["progression"]["wall_bank_switches"]):
            self._bank_hit = set()
            self._wall_advance()

    def _wall_advance(self, **kwargs):
        p = self.player
        if p.got_wall_lit or self._multiball_running():            # OkToAdvance: no multiball, flag 34 not set
            return
        p.got_wall_advances += 1
        if p.got_wall_advances >= self._wall_needed():
            p.got_wall_advances = 0
            p.got_wall_lit = 1                                       # flag 34
            self.machine.events.post("got_wall_lit")

    def _wall_start(self, **kwargs):
        p = self.player
        prog = self._progression()
        if p.got_wall_lit and not self._multiball_running() and not state.iron_startable(self.machine, p):
            p.got_wall_lit = 0
            p.got_wall_awarded += 1
            self.machine.events.post("start_mode_wall")

    # --- Midnight Madness
    def _madness_check(self, **kwargs):
        self.delay.add(1000, self._madness_check, "madness_check")
        t = _now()
        window_min = self._rules["progression"]["madness_window_s"] // 60
        day = (t.tm_year, t.tm_yday)
        if t.tm_hour == 0 and t.tm_min < window_min and self._madness_day != day \
                and not self._multiball_running() and self.machine.game and self.machine.game.balls_in_play:
            self._madness_day = day
            self.machine.events.post("start_mode_midnight_madness")
