"""MPF glue: base game mode. Wizard progression and starting the next ready mode. UNVERIFIED against MPF."""
import time

from mpf.core.mode import Mode

from got.rules_core import Progression, load_rules


def _now():
    """Local time; the tests replace it. The ROM reads the RTC (sys_rtc_get_current_time)."""
    return time.localtime()


class GotBase(Mode):
    def mode_start(self, **kwargs):
        self._rules = load_rules()
        self.add_mode_event_handler("got_house_complete", self._house_complete)
        self.add_mode_event_handler("s_throne_active", self._start_next_house)
        self.add_mode_event_handler("balldevice_bd_lock_ball_enter", self._lock_entered)
        pr = self._rules["progression"]
        # Castle: the three upper standups advance the upper-playfield level; level 4 starts Castle (docs/06, H/M)
        self._standups_hit = set()
        for sw in pr["castle_standups"]:
            self.add_mode_event_handler(sw + "_active", self._standup, sw=sw)
        # Wall: advances counter, lit at min(11, 6 + 5 x advances awarded) (docs/06, H); starts from the elevator kick
        for sw in pr["wall_advance_switches"]:
            self.add_mode_event_handler(sw + "_active", self._wall_advance)
        self.add_mode_event_handler("s_elevator_popper_active", self._wall_start)
        # Midnight Madness: real-time clock at 00:00, waits up to 10 min for a ball on the playfield (docs/06, H)
        self._madness_day = None
        self.delay.add_if_doesnt_exist(1000, self._madness_check, "madness_check")

    def _progression(self):
        p = self.player
        if not p.got_progression:               # MPF player variables default to 0
            p.got_progression = Progression(self._rules)
        return p.got_progression

    def _house_complete(self, house_id, **kwargs):
        for ev in self._progression().house_complete(house_id):
            self.machine.events.post("got_" + ev)

    def _start_next_house(self, **kwargs):
        prog = self._progression()
        # PROVISIONAL (Hand 'StartReady' / Iron Throne 'SetReady' are H in docs/06, but their start shot is M): a multiball that became
        # ready starts on the next throne hit, before the next house.
        for key in sorted(prog.ready):
            if key not in prog.started:
                prog.started.add(key)
                self.machine.events.post("start_mode_" + key)
                return
        # Departure (docs/rom_differences.md): the ROM's Choose Your Battle is replaced by "throne starts the next house".
        for h in self._rules["houses"]:
            if h["id"] not in prog.complete and not self._house_running():
                self.machine.events.post("start_mode_" + h["key"])
                # Winter Is Coming is offered with it when completed + running houses <= 6 (docs/06, SelectModesToStart; H)
                if len(prog.complete & prog.houses) + 1 <= 6 and not self.machine.modes["winter_has_come"].active:
                    self.machine.events.post("start_mode_winter_is_coming")
                return

    def _house_running(self):
        return any(m.active for m in self.machine.modes if m.config.get("mode_settings", {}).get("kind") == "house" and m.config["mode_settings"]["id"] != 7)

    def _lock_entered(self, **kwargs):
        # PROVISIONAL: three balls locked (S lock_1..3) start Blackwater (03 s3: locks 1-3 hold balls for Blackwater).
        if self.machine.ball_devices["bd_lock"].balls >= 3:
            self.machine.events.post("start_mode_blackwater")

    def _multiball_running(self):
        return any(m.active and m.config.get("mode_settings", {}).get("kind") == "multiball" for m in self.machine.modes)

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
        if p.got_wall_lit and not self._multiball_running() and "iron_throne" not in (prog.ready - prog.started):
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
