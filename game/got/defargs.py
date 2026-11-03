"""Run-time values for ROM text effects (data/dmd_text_args.csv): before a got_def_* effect is shown, the machine variables
got_arg_score (current player's score) and got_arg_award (the last score increase, inferred: the award just given) are set
got_arg_shots (shots still needed in the running Lannister/Greyjoy mode) and got_arg_timer (seconds left on the running mode timer) for the live text slides (game/scripts/dmd_text_live.gd). The other printf arguments (counters, multipliers) still show 0."""
from mpf.core.mode import Mode


def _fmt(n):
    return "{:,}".format(int(n or 0))


class DefArgs(Mode):
    def mode_start(self, **kwargs):
        self._award = 0
        self._events = set()
        for ev in self.machine.config.get("slide_player", {}):
            if ev.startswith("got_def_"):
                self._events.add(ev)
                self.add_mode_event_handler(ev, self._set, priority=1000, ev=ev)
        self.add_mode_event_handler("player_score", self._score)
        self.add_mode_event_handler("got_tickle_progress", self._tickle)
        self.add_mode_event_handler("got_mode_total", self._mode_total)
        self.add_mode_event_handler("got_blackwater_super_lit", self.level_lit)
        self._tickle_left = 0

    def level_lit(self, level=1, **kwargs):                       # "%dX SUPER JACKPOT / IS LIT" shows the level, not the last payment
        self._award = int(level)
        self._total_until = self.machine.clock.get_time() + 2.0

    def _score(self, change=0, **kwargs):
        if self.machine.clock.get_time() < getattr(self, "_total_until", 0):
            return                                    # a mode total is on its way to the screen: later switch points must not replace it
        if change and int(change) > 0:
            self._award = int(change)

    def _mode_total(self, total=0, **kwargs):
        self._award = int(total)                  # the effect that follows shows the mode total in {award}
        self._total_until = self.machine.clock.get_time() + 3.0

    def _tickle(self, left=0, **kwargs):
        self._tickle_left = int(left)

    def _total_of(self, ev):
        """The mode total the ROM's total screen shows: the score gained since the mode started. The screen is requested by mode_<key>_stopped,
        which runs before the mode's own got_mode_total reaches us, so it is computed here from the mode."""
        from got.award_mode import AwardMode
        name = ev[len("got_def_"):]
        for key, d in AwardMode.TOTAL_DEF.items():
            if d == name:
                m = self.machine.modes.get(key)
                game = self.machine.game
                if m is not None and getattr(m, "_score0", None) is not None and game and game.player:
                    return max(0, int(game.player.score) - m._score0)
        return None

    def _set(self, ev=None, **kwargs):
        if ev and ev.endswith("_total"):
            total = self._total_of(ev)
            if total:
                self._award = total
        game = self.machine.game
        score = game.player.score if game and game.player else 0
        self.machine.variables.set_machine_var("got_arg_score", _fmt(score))
        self.machine.variables.set_machine_var("got_arg_award", _fmt(self._award))
        self.machine.variables.set_machine_var("got_arg_player", str(game.player.number if game and game.player else 1))
        self.machine.variables.set_machine_var("got_arg_ball", str(game.player.ball if game and game.player else 1))
        p = game.player if game else None
        self.machine.variables.set_machine_var("got_arg_tickle", str(self._tickle_left))
        self.machine.variables.set_machine_var("got_arg_gold", _fmt(getattr(p, "got_gold", 0) if p else 0))
        self.machine.variables.set_machine_var("got_arg_wildfire", _fmt(getattr(p, "got_wildfire", 0) if p else 0))
        price = {1: 1200, 2: 1800, 3: 2400, 4: 3000}.get(int(getattr(p, "got_multiplier", 1) or 1), 0) if p else 0
        self.machine.variables.set_machine_var("got_arg_price", _fmt(price))
        shots = [m.shots_left for m in self.machine.modes if m.active and hasattr(m, "shots_left")]
        self.machine.variables.set_machine_var("got_arg_shots", str(shots[0]) if shots else "0")
        left = [int(t.ticks) for t in self.machine.timers.values() if t.running and t.name.endswith("_timer")]
        self.machine.variables.set_machine_var("got_arg_timer", str(max(left) if left else 0))
        for m in list(self.machine.modes):                                  # modes with their own live screen values publish them last
            if m.active and getattr(m, "own_args", False):
                try:
                    m._publish()
                except AttributeError:                       # the mode is still starting
                    pass
