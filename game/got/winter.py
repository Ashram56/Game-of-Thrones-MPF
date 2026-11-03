"""Winter Is Coming (mode 7): lit shots, hurry-up, link to Winter Has Come. Rules: Game-of-Thrones docs/06 (H, static code read).

1. Each accepted lit shot adds 1; the third starts the hurry-up (timer runs).
2. A hurry-up shot gives the decaying award, adds it to the Winter super jackpot and counts a completion.
3. The 4th completion starts Winter Has Come (multiball 6) and resets the counters.
Which switches are the lit shots is PROVISIONAL (docs/06: the shot-to-switch mapping is not recovered).
"""
from mpf.core.mode import Mode

from got import powers, state
from got.rules_core import Award


class WinterMode(Mode):
    def mode_start(self, **kwargs):
        cfg = self.config["mode_settings"]
        self._cfg = cfg
        self._award = Award(cfg["award"]["start"], cfg["award"].get("bump", 0), cfg["award"].get("cap", 0))
        if self.player.got_winter_award:               # the award grows by BumpAward per completion, kept per player
            self._award.value = self.player.got_winter_award
        self._hurry = False
        if self.player.got_house == "stark" and not self.player.got_winter_award:        # Stark persistent (rulesheet)
            self._award.value += powers.STARK_WINTER_BONUS
        for sw in cfg["shots"]:
            self.add_mode_event_handler(sw + "_active", self._shot)
        self.add_mode_event_handler("timer_winter_is_coming_timer_complete", self._timeout)

    def _shot(self, **kwargs):
        p = self.player
        # cmode_manager::ShotMade suppress rule (docs/06): no lit shots while a house mode or multiball runs or Hand is startable
        if not self._hurry and (state.house_running(self.machine) or state.multiball_running(self.machine)
                                or state.hand_startable(self.machine, p)):
            return
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
        p.got_best_winter_is_coming = max(int(p.got_best_winter_is_coming or 0), points)     # Winter Is Coming champion table (best hurry-up)
        p.got_winter_super += points                    # cmball_winter::AddSuperJackpot
        p.got_winter_completions += 1
        self.machine.events.post("got_winter_is_coming_award", points=points)
        self._award.bump()
        p.got_winter_award = self._award.value
        completions = p.got_winter_completions
        self.stop()
        if completions > 3:                             # 4th completion links to Winter Has Come
            p.got_winter_completions = 0
            self.machine.events.post("start_mode_winter_has_come")

    def _timeout(self, **kwargs):
        self.stop()
