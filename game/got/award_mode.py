"""MPF glue: one generic mode class for the 8 houses and 7 multiballs, driven by `mode_settings` that
scripts/gen_config.py writes from rules.yaml.
API names follow MPF 0.80 (Mode.add_mode_event_handler, Mode.player, <switch>_active events)."""
from got import state
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
        self._score0 = int(player.score) if player is not None else 0
        for sw in cfg["shots"]:
            self.add_mode_event_handler(sw + "_active", self._shot, sw=sw)
        self.add_mode_event_handler("timer_%s_timer_complete" % cfg["key"], self._timeout)

    TOTAL_DEF = {"blackwater": "blackwater_total", "wall": "wall_total", "hand_of_the_king": "hand_total", "iron_throne": "iron_total",
                 "castle": "castle_multiball_total", "winter_has_come": "winter_mball_total", "midnight_madness": "madness_multiball_total",
                 "greyjoy": "greyjoy_total", "lannister": "lannister_total", "martell": "martell_total", "tyrell": "tyrell_total",
                 "targaryen": "targaryen_total"}

    def mode_stop(self, **kwargs):
        """The ROM's TotalChoreo: when the mode ends, the points it earned are shown (the total is inferred as the score gained while it ran)."""
        key = getattr(self, "_cfg", {}).get("key")
        name = self.TOTAL_DEF.get(key)
        player = self.machine.game.player if self.machine.game else None
        if player is not None and getattr(self, "_score0", None) is not None and key:
            best = "got_best_" + key                                  # mode champion tables: the player's best mode score
            setattr(player, best, max(int(getattr(player, best, 0) or 0), int(player.score) - self._score0))
        if name and player is not None and getattr(self, "_score0", None) is not None:
            total = int(player.score) - self._score0
            if total > 0:
                self.machine.events.post("got_mode_total", total=total)    # sets {award}; mode_<key>_stopped then plays got_def_<key>_total
        super().mode_stop(**kwargs)

    def _shot(self, sw=None, **kwargs):
        if state.fast_loop(self.machine, sw):
            return
        if not self._accepts(sw):
            return
        self._pay()

    def _pay(self):
        cfg = self._cfg
        points = self._award.give(global_mult=self._gm())
        if cfg.get("hurry_up"):
            # CFG/provisional: the ROM's hurry-up decay amounts are not recovered; linear decay over the mode timer.
            timer = self.machine.timers[cfg["key"] + "_timer"]
            points = self._award.hurry_up(timer.ticks, cfg["timer_s"]) * self._gm()
        self.player.score += points
        self._last_points = points
        self._award.bump()
        setattr(self.player, self._award_key, self._award.value)
        self._shots += 1
        self.machine.events.post("got_%s_award" % cfg["key"], points=points)
        if self._shots >= cfg.get("shots_to_complete", 0) > 0 and cfg["kind"] == "house":
            self.machine.events.post("got_house_complete", house_id=cfg["id"], key=cfg["key"])
            self.stop()

    def _gm(self):
        """Playfield multiplier x Combo X multiplier of the shot (docs/10: DoShot applies the combo value)."""
        return (self.player.got_multiplier or 1) * (self.player.got_combo_mult or 1)

    def _accepts(self, sw):
        """Hook for houses with their own shot logic (got.houses)."""
        return True

    def _timeout(self, **kwargs):
        self.stop()
