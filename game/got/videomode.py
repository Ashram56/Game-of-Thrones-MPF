"""Video mode duel. H (docs/10): timer 41 = 20 s; ends when the player's or the AI's health reaches 0 (win/lose) or at time
out (tie); score = video_mode_score(outcome, n, level), level from adjustment 132 (default 2). CFG (not recovered): health
points, hit damage and the AI's strike interval."""
from mpf.core.mode import Mode

HEALTH = 10
DURATION_S = 20
AI_INTERVAL_S = lambda level: max(0.4, 1.6 - 0.2 * level)


class VideoMode(Mode):
    def mode_start(self, n=1, **kwargs):
        self._n = int(n)
        s = self.machine.settings
        self._level = int(s.get_setting_value("ad_video_mode_difficulty")) if "ad_video_mode_difficulty" in getattr(s, "setting_definitions", {}) else 2
        self._me = self._ai = HEALTH
        self.add_mode_event_handler("s_l_flipper_button_active", self._attack)
        self.add_mode_event_handler("s_r_flipper_button_active", self._attack)
        self.delay.add(DURATION_S * 1000, self._finish, outcome="tie", name="vm_time")
        self.delay.add(int(AI_INTERVAL_S(self._level) * 1000), self._ai_strike, name="vm_ai")
        self._state()

    def _state(self):
        self.machine.events.post("got_video_mode_state", me=self._me, ai=self._ai, n=self._n)

    def _attack(self, **kwargs):
        self._ai -= 1
        self._state()
        if self._ai <= 0:
            self._finish("win")

    def _ai_strike(self, **kwargs):
        self._me -= 1
        self._state()
        if self._me <= 0:
            self._finish("loss")
        else:
            self.delay.add(int(AI_INTERVAL_S(self._level) * 1000), self._ai_strike, name="vm_ai")

    def _finish(self, outcome, **kwargs):
        self.delay.remove("vm_time")
        self.delay.remove("vm_ai")
        self.machine.events.post("got_video_mode_result", outcome=outcome, n=self._n, level=self._level)
        self.machine.events.post("got_video_mode_finished")
