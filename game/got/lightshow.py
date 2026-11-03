"""Lamps that follow the rules (CFG: the ROM's lamp effects are not decoded for Spike 1; which lamp means what is from the
lamp names): Start button until ball 2, Shoot Again while a ball save runs, house sigils (running = blinking, complete = solid,
lit by Mystery = dim), Extra Ball, Choose Your Battle."""
from mpf.core.mode import Mode

HOUSES = ("targaryen", "stark", "baratheon", "lannister", "greyjoy", "tyrell", "martell")
COLORS = {"targaryen": "ff1a00", "stark": "bfdfff", "baratheon": "ffd000", "lannister": "ff8c00", "greyjoy": "1a4dff",
          "tyrell": "22dd44", "martell": "ff4000"}
KEY = "rules"


class LightMode(Mode):
    def mode_start(self, **kwargs):
        for h in HOUSES:
            self.add_mode_event_handler("mode_%s_started" % h, self.refresh)
            self.add_mode_event_handler("mode_%s_stopped" % h, self.refresh)
        for ev in ("got_house_complete", "ball_started", "got_light_extra_ball", "got_award_extra_ball", "got_cyb_menu",
                   "got_cyb_done", "got_lit_house"):
            self.add_mode_event_handler(ev, self.refresh)
        self.add_mode_event_handler("ball_save_default_timer_start", self._shoot_again, on=True)
        for ev in ("ball_save_default_disabled", "ball_save_default_timer_expired", "ball_save_default_saving_ball"):
            self.add_mode_event_handler(ev, self._shoot_again, on=False)
        self.refresh()

    def mode_stop(self, **kwargs):
        for name in ("start_button", "shoot_again", "extra_ball", "iron_throne") + tuple(h + "_sigil" for h in HOUSES):
            self._set(name, "000000")

    def _set(self, name, color):
        light = self.machine.lights["l_" + name]
        light.remove_from_stack_by_key(KEY)
        if color != "000000":
            light.color(color, key=KEY, priority=50)

    def _shoot_again(self, on, **kwargs):
        self._set("shoot_again", "ffffff" if on else "000000")

    def refresh(self, **kwargs):
        p = self.player
        if p is None:
            return
        self._set("start_button", "ffffff" if p.ball <= 1 and self.machine.game.num_players < 4 else "000000")
        prog = p.got_progression
        done = set(prog.complete) if prog else set()
        lit = {x for x in (p.got_lit_houses or "").split(",") if x}
        for i, h in enumerate(HOUSES):
            mode = self.machine.modes.get(h)
            running = bool(mode and mode.active)
            if running:
                self._set(h + "_sigil", COLORS[h])
            elif i in done:
                self._set(h + "_sigil", COLORS[h])
            elif h in lit:
                self._set(h + "_sigil", "404040")
            else:
                self._set(h + "_sigil", "000000")
        self._set("extra_ball", "ffffff" if p.got_extra_ball_lit else "000000")
        self._set("iron_throne", "ffffff" if getattr(self.machine.modes["combos"], "cyb", None) else "000000")
