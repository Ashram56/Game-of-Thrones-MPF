"""Run-time values for ROM text effects (data/dmd_text_args.csv): before a got_def_* effect is shown, the machine variables
got_arg_score (current player's score) and got_arg_award (the last score increase, inferred: the award just given) are set
for the live text slides (game/scripts/dmd_text_live.gd). The other printf arguments (timers, counters) still show 0."""
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
                self.add_mode_event_handler(ev, self._set, priority=1000)
        self.add_mode_event_handler("player_score", self._score)

    def _score(self, change=0, **kwargs):
        if change and int(change) > 0:
            self._award = int(change)

    def _set(self, **kwargs):
        game = self.machine.game
        score = game.player.score if game and game.player else 0
        self.machine.variables.set_machine_var("got_arg_score", _fmt(score))
        self.machine.variables.set_machine_var("got_arg_award", _fmt(self._award))
