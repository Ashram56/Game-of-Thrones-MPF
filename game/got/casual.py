"""Casual player mode (adjustment 108, default off; docs/14 section 5, H call sites): the right flipper starts a game in attract."""
from mpf.modes.attract.code.attract import Attract as MpfAttract


def is_casual(machine):
    s = machine.settings
    return "ad_casual_mode" in s._settings and int(s.get_setting_value("ad_casual_mode") or 0) == 1


class Attract(MpfAttract):
    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self.add_mode_event_handler("s_r_flipper_button_active", self._right_flipper)

    def _right_flipper(self, **kwargs):
        if is_casual(self.machine):
            self.start_buttons_held = []
            self.start_hold_time = 0
            self.machine.events.post_boolean("request_to_start_game", callback=self.result_of_start_request)
