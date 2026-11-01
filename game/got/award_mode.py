"""MPF glue: one generic mode class for the 8 houses and 7 multiballs, driven by `mode_settings` that
scripts/gen_config.py writes from rules.yaml. UNVERIFIED against a running MPF (not installable offline):
API names follow MPF 0.80 (Mode.add_mode_event_handler, Mode.player, <switch>_active events)."""
from mpf.core.mode import Mode

from got.rules_core import Award


class AwardMode(Mode):
    def mode_start(self, **kwargs):
        cfg = self.config.get("mode_settings", {})
        self._cfg = cfg
        self._award_key = "got_award_" + cfg["key"]
        player = self.player
        if player is not None and not getattr(player, self._award_key):    # per-player value, kept between ball
            setattr(player, self._award_key, cfg["award"]["start"])
        self._award = Award(cfg["award"]["start"], cfg["award"].get("bump", 0), cfg["award"].get("cap", 0))
        if player is not None and getattr(player, self._award_key):
            self._award.value = getattr(player, self._award_key)
        self._shots = 0
        for sw in cfg["shots"]:
            self.add_mode_event_handler(sw + "_active", self._shot, sw=sw)
        self.add_mode_event_handler("timer_%s_timer_complete" % cfg["key"], self._timeout)

    def _shot(self, sw=None, **kwargs):
        if not self._accepts(sw):
            return
        self._pay()

    def _pay(self):
        cfg = self._cfg
        points = self._award.give(global_mult=self.player.got_multiplier or 1)
        if cfg.get("hurry_up"):
            # CFG/provisional: the ROM's hurry-up decay amounts are not recovered; linear decay over the mode timer.
            timer = self.machine.timers[cfg["key"] + "_timer"]
            points = self._award.hurry_up(timer.ticks, cfg["timer_s"]) * (self.player.got_multiplier or 1)
        self.player.score += points
        self._last_points = points
        self._award.bump()
        setattr(self.player, self._award_key, self._award.value)
        self._shots += 1
        self.machine.events.post("got_%s_award" % cfg["key"], points=points)
        if self._shots >= cfg.get("shots_to_complete", 0) > 0 and cfg["kind"] == "house":
            self.machine.events.post("got_house_complete", house_id=cfg["id"], key=cfg["key"])
            self.stop()

    def _accepts(self, sw):
        """Hook for houses with their own shot logic (got.houses)."""
        return True

    def _timeout(self, **kwargs):
        self.stop()
