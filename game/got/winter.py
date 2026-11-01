"""Winter Is Coming (mode 7): lit shots, hurry-up, link to Winter Has Come. Rules: Game-of-Thrones docs/06 (H, static code read).

1. Each accepted lit shot adds 1; the third starts the hurry-up (timer runs).
2. A hurry-up shot gives the decaying award, adds it to the Winter super jackpot and counts a completion.
3. The 4th completion starts Winter Has Come (multiball 6) and resets the counters.
Which switches are the lit shots is PROVISIONAL (docs/06: the shot-to-switch mapping is not recovered).
"""
from mpf.core.mode import Mode

from got.rules_core import Award


class WinterMode(Mode):
    def mode_start(self, **kwargs):
        cfg = self.config["mode_settings"]
        self._cfg = cfg
        self._award = Award(cfg["award"]["start"], cfg["award"].get("bump", 0), cfg["award"].get("cap", 0))
        self._hurry = False
        for sw in cfg["shots"]:
            self.add_mode_event_handler(sw + "_active", self._shot)
        self.add_mode_event_handler("timer_winter_is_coming_timer_complete", self._timeout)

    def _shot(self, **kwargs):
        p = self.player
        if not self._hurry:
            p.got_winter_lit_shots += 1
            if p.got_winter_lit_shots > 2:              # third accepted shot
                p.got_winter_lit_shots = 0
                self._hurry = True
                self.machine.timers["winter_is_coming_timer"].start()
                self.machine.events.post("got_winter_hurry_up_started")
            return
        timer = self.machine.timers["winter_is_coming_timer"]
        points = self._award.hurry_up(timer.ticks, self._cfg["timer_s"]) * (p.got_multiplier or 1)
        p.score += points
        p.got_winter_super += points                    # cmball_winter::AddSuperJackpot
        p.got_winter_completions += 1
        self.machine.events.post("got_winter_is_coming_award", points=points)
        completions = p.got_winter_completions
        self.stop()
        if completions > 3:                             # 4th completion links to Winter Has Come
            p.got_winter_completions = 0
            self.machine.events.post("start_mode_winter_has_come")

    def _timeout(self, **kwargs):
        self.stop()
