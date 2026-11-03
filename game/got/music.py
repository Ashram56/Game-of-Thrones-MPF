"""Background music by game state (data/music_stack.csv, ROM udmo objects: highest stack priority whose condition holds wins).
Each tune loops on the solo music bus; a new tune replaces the previous one. Ready states (hand, wall, iron throne) included; the *_spacer variants are not wired yet."""
from mpf.core.mode import Mode

from got import state

# MPF mode -> (ROM stack priority, tune). Source rows: music_stack.csv (default_music column); houses are the mode tunes of se_tune_<house>.
STACK = {
    "tilt": (243, "quiet_track_0"),
    "videomode": (176, "tune_video_mode"),
    "winter_is_coming": (144, "tune_winter_is_coming"),
    "midnight_madness": (137, "tune_castle_multiball"),
    "blackwater": (136, "tune_blackwater"),
    "castle": (136, "tune_castle_multiball"),
    "hand_of_the_king": (136, "tune_hand"),
    "iron_throne": (136, "tune_iron_throne"),
    "wall": (136, "tune_wall_multiball"),
    "winter_has_come": (136, "tune_winter_has_come"),
    "stark": (131, "tune_stark"),
    "lannister": (131, "tune_lannister"),
    "baratheon": (131, "tune_baratheon"),
    "greyjoy": (131, "tune_greyjoy"),
    "martell": (131, "tune_martell"),
    "tyrell": (131, "tune_tyrell"),
    "targaryen": (131, "tune_targaryen_one"),
}
MAIN = {1: "tune_main_play", 2: "tune_main_play_ball_2", 3: "tune_main_play_ball_3"}


class Music(Mode):
    def mode_start(self, **kwargs):
        self._active = set()
        self._ball = 1
        self._now = None
        for m in STACK:
            self.add_mode_event_handler("mode_%s_started" % m, self._on, which=m)
            self.add_mode_event_handler("mode_%s_stopped" % m, self._off, which=m)
        for ev in ("got_wall_lit", "got_house_complete", "got_house_confirmed"):
            self.add_mode_event_handler(ev, self._refresh)
        self.add_mode_event_handler("ball_started", self._ball_started)
        self.add_mode_event_handler("game_ended", self._reset)

    def _on(self, which, **kwargs):
        self._active.add(which)
        self._update()

    def _off(self, which, **kwargs):
        self._active.discard(which)
        self._update()

    def _ball_started(self, ball=1, **kwargs):
        self._ball = int(ball)
        self._active = {m for m in self._active if m in self.machine.modes and self.machine.modes[m].active}
        self._update()

    def _refresh(self, **kwargs):
        self.delay.add(50, self._update, name="refresh")

    def _ready(self):
        """The 'ready' backgrounds (ROM music_stack, priority 136): the multiball is lit and waits to be started."""
        p = self.machine.game.player if self.machine.game else None
        if not p:
            return []
        out = []
        if p.got_wall_lit:
            out.append((136, "tune_wall_multiball_ready"))
        if state.hand_startable(self.machine, p):
            out.append((136, "tune_hand_ready"))
        if state.iron_startable(self.machine, p):
            out.append((136, "tune_iron_throne_ready"))
        return out

    def _reset(self, **kwargs):
        self._active.clear()
        self._now = None

    def _update(self):
        if not self.machine.game:
            return
        tune = MAIN.get(self._ball, MAIN[3])
        cands = [STACK[m] for m in self._active] + self._ready()
        if cands:
            tune = max(cands, key=lambda x: x[0])[1]
        if tune != self._now:
            self._now = tune
            self.machine.events.post("got_se_" + tune)
