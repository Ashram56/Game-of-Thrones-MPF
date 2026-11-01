"""MPF glue: base game mode. Wizard progression and starting the next ready mode. UNVERIFIED against MPF."""
from mpf.core.mode import Mode

from got.rules_core import Progression, load_rules


class GotBase(Mode):
    def mode_start(self, **kwargs):
        self._rules = load_rules()
        self.add_mode_event_handler("got_house_complete", self._house_complete)
        self.add_mode_event_handler("s_throne_active", self._start_next_house)
        self.add_mode_event_handler("balldevice_bd_lock_ball_enter", self._lock_entered)

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
