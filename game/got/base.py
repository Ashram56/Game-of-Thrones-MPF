"""MPF glue: base game mode. Wizard progression and starting the next ready mode."""
import time

from mpf.core.mode import Mode

from got import casual
from got import powers, state
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
        # House choice (rulesheet): on the first ball the flippers cycle the houses until the ball leaves the shooter lane.
        # The house id is the ROM's (0 Targaryen .. 6 Martell); casual mode is not modelled (Stark is the default).
        self.add_mode_event_handler("s_l_flipper_button_active", self._choose, step=-1)
        self.add_mode_event_handler("s_r_flipper_button_active", self._choose, step=1)
        self.add_mode_event_handler("s_shooter_lane_inactive", self._house_confirmed)
        self.add_mode_event_handler(powers.ACTION_SWITCH + "_active", self._action)
        self._bank_hit = set()
        for sw in pr["wall_bank_switches"]:
            self.add_mode_event_handler(sw + "_active", self._bank_switch, sw=sw)
        for sw in pr["wall_advance_switches"]:
            self.add_mode_event_handler(sw + "_active", self._wall_advance)
        self.add_mode_event_handler("s_elevator_popper_active", self._wall_start)
        # Launch windows (docs/22 1c, H): ball leaves the shooter lane -> proc 73 (1.45 s) and proc 74 (3.2 s)
        self.fast_loop_window = False                   # a right loop inside it is a throne/elevator entry, not a normal shot
        self.elevator_window = False                    # ok_to_enter_elevator is true while it runs
        self.add_mode_event_handler("s_shooter_lane_inactive", self._launch_windows)
        self.add_mode_event_handler("s_right_loop_active", self._right_loop_window)
        # Midnight Madness: real-time clock at 00:00, waits up to 10 min for a ball on the playfield (docs/06, H)
        self._madness_day = None
        self.delay.add_if_doesnt_exist(1000, self._madness_check, "madness_check")

    def _launch_windows(self, **kwargs):
        self.fast_loop_window = self.elevator_window = self.machine.got_fast_loop = True
        self.delay.add(1450, self._end_fast_window, "fast_loop_window")
        self.delay.add(3200, self._end_elevator_window, "elevator_window")

    def _end_fast_window(self, **kwargs):
        self.fast_loop_window = self.machine.got_fast_loop = False

    def _end_elevator_window(self, **kwargs):
        self.elevator_window = False

    def _right_loop_window(self, **kwargs):
        """swdf_right_loop (0x4c49c): inside proc 73 the loop is routed to the elevator (event for the lights/sound); the window is then
        killed. The normal right-loop shot award is not suppressed in every mode (modes read the switch themselves)."""
        if self.fast_loop_window:
            self.delay.remove("fast_loop_window")
            self.delay.add(0, self._end_fast_window, "fast_loop_window")     # after every shot handler of this switch event has run
            self.machine.events.post("got_right_loop_fast")

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
        # Lit houses open Choose Your Battle (got.combos); with none lit the throne still starts the next house (departure,
        # docs/rom_differences.md).
        prog = self._progression()
        lit = [x for x in (self.player.got_lit_houses or "").split(",") if x]
        cyb = self.machine.modes["combos"]
        if cyb.cyb_open_menu(prog):                     # Choose Your Battle over the lit houses (docs/14)
            return
        if cyb.cyb:
            return
        order = sorted(self._rules["houses"], key=lambda h: h["key"] not in lit)       # Mystery "Light <house>" goes first
        for h in order:
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
        """cblackwater::AwardLock / DoAwardLock (docs/12, H): CanWeLockNow needs the lock lit (flag 36), no multiball and Iron
        not startable. Each lock: count + 1, gold +75 (+250 while Lannister ticks, M), +5 Wildfire, flag 36 cleared (it must
        be relit); the 3rd lock starts Blackwater."""
        p = self.player
        if not p.got_lock_lit or self._multiball_running():
            return
        p.got_lock_lit = 0
        p.got_locked_balls += 1
        p.got_gold += 250 if self.machine.modes["lannister"].active else 75
        self.machine.events.post("got_wildfire_bump", n=5)
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
            self.machine.events.post("got_bank_complete")
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

    # --- House choice and powers
    def _choosing(self):
        p = self.player
        return not p.got_house_confirmed and self.machine.game.player.ball == 1

    def _choose(self, step, **kwargs):
        if not self._choosing() or casual.is_casual(self.machine):        # casual mode skips the house choice (docs/14)
            return
        p = self.player
        p.got_house_index = (int(p.got_house_index or 1) + step) % len(powers.HOUSES)     # default Stark (1)
        p.got_house_picked = 1
        self.machine.events.post("got_house_chosen", house=powers.HOUSES[p.got_house_index])

    def _house_confirmed(self, **kwargs):
        p = self.player
        if p.got_house_confirmed or self.machine.game.player.ball != 1:
            return
        p.got_house_confirmed = 1
        idx = int(p.got_house_index) if p.got_house_picked else 1
        p.got_house_index = idx
        p.got_house = powers.HOUSES[idx]
        prog = self._progression()
        kills = 2
        if idx == 0:                                   # adjustment 118: 0 = one dragon killed, 1 = two, 2 (default) = house complete
            kills = int(self.machine.settings.get_setting_value("ad_targaryen_house_select")) if "ad_targaryen_house_select" in self.machine.settings._settings else 2
        if idx == 0 and kills < 2:
            p.got_dragon_stage = kills + 1
            p.score += 30000000 * (kills + 1)          # StarkKill(false) = 30M per dragon (docs/18, M)
        elif idx in (0, 4):                            # Targaryen / Greyjoy start with their house complete
            self.machine.events.post("got_house_complete", house_id=idx, key=p.got_house)
        if p.got_house == "baratheon":
            p.got_wall_advances += powers.BARATHEON_WALL_ADVANCES
        self._house_start_award(idx)
        self.machine.events.post("got_house_confirmed", house=p.got_house)

    def _house_start_award(self, idx):
        """Once per player, on ball 1, when the house is confirmed (docs/18, data/house_start_awards.csv): voice 433 (one variant per house)
        and the house's start award. Targaryen/Greyjoy complete at once (above); Martell has no award; Tyrell's extra return lane is not modelled."""
        p = self.player
        house = powers.HOUSES[idx]
        self.machine.events.post("got_se_vo_fn_house_selected_v%d" % (idx + 1))
        if house == "stark":                           # GiveAwardStark: Winter Is Coming value raised 5 steps (+75,000)
            p.got_winter_award = int(p.got_winter_award or 4000000) + 5 * 75000
        elif house == "baratheon":                     # Wall jackpot (award #11) starts at 5,000,000 instead of 3,250,000
            p.got_award_wall = max(int(p.got_award_wall or 0), 5000000)
        elif house == "tyrell":                        # GiveReturnLane: flag 49 (left return lane lit), lasts the ball (M)
            self.machine.events.post("got_give_return_lane")
        elif house == "lannister":                     # AddGold(750)
            p.got_gold = int(p.got_gold or 0) + 750
        self.machine.events.post("got_def_give_house_" + house)

    def _ability(self):
        """Mystery button abilities (docs/11 section 4): 3 Baratheon = Lord of Light, 4 Lannister = buy a playfield
        multiplier with gold, 6 Martell = add a ball in multiball."""
        p = self.player
        ab = int(p.got_button_ability or 0)
        if ab == 5 and self.machine.modes["combos"].iron_bank():
            return True
        if ab == 3:
            p.got_button_ability = 0
            self.machine.events.post("got_light_lord_of_light")
            return True
        if ab == 4 and int(p.got_ability_uses or 0) > 0:
            cost = {1: 1200, 2: 1800, 3: 2400, 4: 3000}.get(int(p.got_multiplier or 1))
            if cost and p.got_gold >= cost:
                p.got_gold -= cost
                p.got_multiplier = int(p.got_multiplier or 1) + 1
                p.got_ability_uses -= 1
                self.machine.events.post("got_pfx", value=p.got_multiplier)
                return True
        if ab == 6 and self._multiball_running():
            self.machine.playfield.add_ball(1)
            self.machine.events.post("got_add_a_ball")
            return True
        return False

    def _action(self, **kwargs):
        """Action button: once per ball (rulesheet)."""
        p = self.player
        if self.machine.modes["extras"].mystery.menu:           # the button confirms the Mystery menu instead
            return
        if self._ability():
            return
        house = p.got_house
        if not house or p.got_action_used_ball == self.machine.game.player.ball:
            return
        if house == "stark":
            for m in self.machine.modes:
                cfg = m.config.get("mode_settings", {})
                if m.active and cfg.get("kind") == "house" and cfg["id"] != 7:
                    p.got_action_used_ball = self.machine.game.player.ball
                    p.score += powers.DIREWOLF_AWARD
                    self.machine.events.post("got_house_complete", house_id=cfg["id"], key=cfg["key"])
                    m.stop()
                    return
        elif house == "targaryen":
            p.got_action_used_ball = self.machine.game.player.ball
            for t in self.machine.timers.values():
                if t.running:
                    t.pause()
                    self.delay.add(powers.FREEZE_S * 1000, t.start, "unfreeze_" + t.name)
        elif house == "martell" and self._multiball_running():
            p.got_action_used_ball = self.machine.game.player.ball
            self.machine.playfield.add_ball(1)
            self.machine.events.post("got_add_a_ball")
