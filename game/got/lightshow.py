"""Lamps that follow the rules (CFG: the ROM's lamp effects are not decoded for Spike 1; which lamp means what is from the
lamp names): Start button until ball 2, Shoot Again while a ball save runs, house sigils (running = blinking, complete = solid,
lit by Mystery = dim), Extra Ball, Choose Your Battle."""
from mpf.core.mode import Mode

HOUSES = ("targaryen", "stark", "baratheon", "lannister", "greyjoy", "tyrell", "martell")
COLORS = {"targaryen": "ff1a00", "stark": "bfdfff", "baratheon": "ffd000", "lannister": "ff8c00", "greyjoy": "1a4dff",
          "tyrell": "22dd44", "martell": "ff4000"}
KEY = "rules"
SKEY = "shots"
# playfield shot switch -> the arrow / sigil lamps that mark it
SHOT_LAMPS = {
    "s_left_loop": ("left_loop_arrow",), "s_right_loop": ("right_loop_arrow_top", "right_loop_arrow_mid", "right_loop_arrow_bot"),
    "s_left_ramp_exit": ("left_ramp_arrow_top", "left_ramp_arrow_bot"), "s_right_ramp_exit": ("right_ramp_arrow_top", "right_ramp_arrow_bot"),
    "s_kickback": ("kickback_lane_arrow_top", "kickback_lane_arrow_bot"), "s_battering_ram": ("battering_ram_arrow",),
    "s_3_bank_drop_tgt_top": ("left_3_bank_top",), "s_3_bank_drop_tgt_mid": ("left_3_bank_mid",), "s_3_bank_drop_tgt_btm": ("left_3_bank_bot",),
    "s_throne": ("iron_throne",), "s_right_2_bank_top": ("right_2_bank_top",), "s_right_2_bank_bottom": ("right_2_bank_bot",),
    "s_elevator_popper": ("hand_of_the_king",), "s_left_return_lane": ("left_return_lane",), "s_right_return_lane": ("right_return_lane",),
}


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
        self._poll = self.machine.clock.schedule_interval(self.refresh, 0.25)    # lamp state follows player variables (lane, lock, multiplier)
        self.refresh()

    def mode_stop(self, **kwargs):
        self.machine.clock.unschedule(self._poll)
        for name in ("start_button", "shoot_again", "extra_ball", "iron_throne", "hand_of_the_king") + tuple(h + "_sigil" for h in HOUSES):
            self._set(name, "000000")
        for lamps in SHOT_LAMPS.values():
            for lamp in lamps:
                self.machine.lights["l_" + lamp].remove_from_stack_by_key(SKEY)

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

        self._hand_lamps(prog)
        self._shot_lamps(p)

    def _hand_lamps(self, prog):
        """lef_hand_of_the_king_ready (109) chases while the Hand is ready; lef_post_hand_background (112) keeps the Hand lamp steady once
        it has been played (chand_lamps.csv, H strings)."""
        hand = self.machine.modes["hand_of_the_king"]
        ready = bool(prog and "hand_of_the_king" in prog.ready and "hand_of_the_king" not in prog.started and not hand.active)
        if ready != getattr(self, "_hand_ready", False):
            self._hand_ready = ready
            self.machine.events.post("got_hand_ready_lamps" if ready else "got_hand_ready_lamps_off")
        played = bool(prog and "hand_of_the_king" in prog.started and not hand.active)
        self._set("hand_of_the_king", "ffffff" if played else "000000")

    def _shot_lamps(self, p):
        """Arrows of the shots the running modes still want (white), the lit return lane, the lock and the playfield multiplier."""
        wanted = {}
        for m in self.machine.modes:
            cfg = m.config.get("mode_settings") if m.active else None
            if cfg and "shots" in cfg and m.name not in ("scoring",):
                color = COLORS.get(cfg.get("key"), "ffffff")
                for sw in cfg["shots"]:
                    wanted.setdefault(sw, color)
        if p.got_return_lane:
            wanted[str(p.got_return_lane)] = "ffffff"
        if p.got_lock_lit:
            wanted["s_left_ramp_exit"] = wanted.get("s_left_ramp_exit", "ffffff")
        for sw, lamps in SHOT_LAMPS.items():
            for lamp in lamps:
                light = self.machine.lights["l_" + lamp]
                light.remove_from_stack_by_key(SKEY)
                if sw in wanted:
                    light.color(wanted[sw], key=SKEY, priority=40)
        mult = int(p.got_multiplier or 1)
        for n in (2, 3, 4, 5):
            light = self.machine.lights["l_%dx" % n]
            light.remove_from_stack_by_key(SKEY)
            if mult == n:
                light.color("ffffff", key=SKEY, priority=40)
        lock = self.machine.lights["l_left_ramp_lock"]
        lock.remove_from_stack_by_key(SKEY)
        if p.got_lock_lit:
            lock.color("ffffff", key=SKEY, priority=40)
