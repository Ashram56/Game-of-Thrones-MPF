"""MPF glue: base game mode. Wizard progression and starting the next ready mode. UNVERIFIED against MPF."""
from mpf.core.mode import Mode

from got.rules_core import Progression, load_rules


class GotBase(Mode):
    def mode_start(self, **kwargs):
        self._rules = load_rules()
        self.add_mode_event_handler("got_house_complete", self._house_complete)
        self.add_mode_event_handler("s_throne_active", self._start_next_house)

    def _progression(self):
        p = self.player
        if "got_progression" not in p.vars:
            p["got_progression"] = Progression(self._rules)
        return p["got_progression"]

    def _house_complete(self, house_id, **kwargs):
        for ev in self._progression().house_complete(house_id):
            self.machine.events.post("got_" + ev)

    def _start_next_house(self, **kwargs):
        # Departure (docs/rom_differences.md): the ROM's Choose Your Battle is replaced by "throne starts the next house".
        prog = self._progression()
        for h in self._rules["houses"]:
            if h["id"] not in prog.complete:
                self.machine.events.post("start_mode_" + h["key"])
                return
