"""Winter Is Coming (mode 7): lit shots, hurry-up, link to Winter Has Come. Rules: Game-of-Thrones docs/06 (H, static code read).

1. Each accepted lit shot adds 1; the third starts the hurry-up (timer runs).
2. A hurry-up shot gives the decaying award, adds it to the Winter super jackpot and counts a completion.
3. The 4th completion starts Winter Has Come (multiball 6) and resets the counters.
Which switches are the lit shots is PROVISIONAL (docs/06: the shot-to-switch mapping is not recovered).
"""
from mpf.core.mode import Mode

from got import powers, state
from got.rules_core import Award


BANK = ("s_3_bank_drop_tgt_top", "s_3_bank_drop_tgt_mid", "s_3_bank_drop_tgt_btm")
BANK2 = ("s_right_2_bank_top", "s_right_2_bank_bottom")


def shot_group(sw):
    """cwinter shot bits: the 3-bank is one shot (0xe001), the right 2-bank one shot (0x30080)."""
    return "bank" if sw in BANK else "bank2" if sw in BANK2 else sw


class WinterMode(Mode):
    """cwinter (docs/29 A, H): every counted lit shot grows award 17 by 75,000 (effect 133); the third starts the 16 s hurry-up on the shot just hit
    (only that shot pays, unbumped, decaying); completing or losing it resets the value to 4,000,000 (the Stark ability adds four bumps);
    the 4th completed hurry-up starts Winter Has Come. M: which counted shots are frozen (a lit house's tickle shot) is not enforced."""

    def mode_start(self, **kwargs):
        cfg = self.config["mode_settings"]
        self._cfg = cfg
        self._award = Award(cfg["award"]["start"], cfg["award"].get("bump", 0), cfg["award"].get("cap", 0))
        self._award.value = int(self.player.got_winter_award or self._reset_value())
        self._hurry, self._active_shot = False, None
        for sw in cfg["shots"]:
            self.add_mode_event_handler(sw + "_active", self._shot, sw=sw)
        self.add_mode_event_handler("timer_winter_is_coming_timer_complete", self._timeout)

    def _reset_value(self):
        extra = 4 if self.player.got_house == "stark" else 0                   # ResetHurryUpValues: Stark flag = four extra bumps
        return int(self._cfg["award"]["start"]) + extra * int(self._cfg["award"].get("bump") or 75000)

    def _shot(self, sw=None, **kwargs):
        p = self.player
        group = shot_group(sw)
        # cmode_manager::ShotMade suppress rule (docs/06): no lit shots while a house mode or multiball runs or Hand is startable
        if not self._hurry and (state.house_running(self.machine) or state.multiball_running(self.machine)
                                or state.hand_startable(self.machine, p)):
            return
        if not self._hurry:
            p.got_winter_lit_shots += 1
            self._award.bump(75000)                                           # BumpAwardValue(true), effect 133
            p.got_winter_award = self._award.value
            self.machine.events.post("got_winter_grows", left=max(0, 3 - int(p.got_winter_lit_shots)))
            if p.got_winter_lit_shots > 2:              # third counted shot
                p.got_winter_lit_shots = 0
                self._hurry, self._active_shot = True, group
                self.machine.timers["winter_is_coming_timer"].start()
                self.machine.events.post("got_winter_hurry_up_started")
            return
        if group != self._active_shot:
            return
        timer = self.machine.timers["winter_is_coming_timer"]
        points = int(self._award.hurry_up(timer.ticks, self._cfg["timer_s"])) * (p.got_multiplier or 1) * int(p.got_combo_mult or 1)
        p.score += points
        p.got_best_winter_is_coming = max(int(p.got_best_winter_is_coming or 0), points)     # Winter Is Coming champion table (best hurry-up)
        p.got_winter_super += points                    # cmball_winter::AddSuperJackpot
        p.got_winter_completions += 1
        self.machine.events.post("got_winter_is_coming_award", points=points)
        p.got_winter_award = self._reset_value()        # ResetHurryUpValues
        completions = p.got_winter_completions
        self.stop()
        if completions > 3:                             # 4th completion links to Winter Has Come
            p.got_winter_completions = 0
            self.machine.events.post("start_mode_winter_has_come")

    def _timeout(self, **kwargs):
        self.player.got_winter_award = self._reset_value()                    # OnEnd: ResetHurryUpValues
        self.stop()
