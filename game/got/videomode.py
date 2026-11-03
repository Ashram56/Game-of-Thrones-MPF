"""Video mode duel. H (docs/10): timer 41 = 20 s; ends when the player's or the AI's health reaches 0 (win/lose) or at time
out (tie); score = video_mode_score(outcome, n, level), level from adjustment 132 (default 2). H (docs/14): player health 3, AI health 3-7 by level, damage 1 (2 for a heavy hit). CFG: the AI's strike interval and heavy share (the ROM uses random(6 - level) tick sleeps and weighted actions, M)."""
from mpf.core.mode import Mode

PLAYER_HEALTH = 3                      # H: cplayer::Initialize
AI_HEALTH = (3, 4, 5, 6, 7)            # H: by level 0..4 (videomode+0x80)
HEAVY_CHANCE = 0.3                     # CFG: share of AI strikes that are heavy hits (2 damage)
DURATION_S = 20
AI_INTERVAL_S = lambda level: max(0.4, 1.6 - 0.2 * level)


class VideoMode(Mode):
    def mode_start(self, n=1, **kwargs):
        self._n = int(n)
        s = self.machine.settings
        self._level = int(s.get_setting_value("ad_video_mode_difficulty")) if "ad_video_mode_difficulty" in s._settings else 2
        self._me = PLAYER_HEALTH
        self._ai = AI_HEALTH[min(4, max(0, self._level))]
        self.rng = __import__("random").Random()
        self.add_mode_event_handler("s_l_flipper_button_active", self._attack)
        self.add_mode_event_handler("s_r_flipper_button_active", self._attack)
        self.delay.add(DURATION_S * 1000, self._finish, outcome="tie", name="vm_time")
        self.delay.add(int(AI_INTERVAL_S(self._level) * 1000), self._ai_strike, name="vm_ai")
        self._state()
        self._sound("start")

    def _sound(self, name):
        """ROM duel sounds (se_fx_video_mode_*, triggers_sound_video.csv: cplayer::SetSoundFromState jump table)."""
        self.machine.events.post("got_se_fx_video_mode_" + name)

    def _state(self):
        v = self.machine.variables.set_machine_var
        v("got_vm_me", self._me)
        v("got_vm_ai", self._ai)
        v("got_vm_ai_max", AI_HEALTH[min(4, max(0, self._level))])
        self.machine.events.post("got_video_mode_state", me=self._me, ai=self._ai, n=self._n)

    def _attack(self, **kwargs):
        self._sound("player_attack")
        self._sound("hit")
        self._ai -= 1
        self._state()
        if self._ai <= 0:
            self._finish("win")

    def _ai_strike(self, **kwargs):
        heavy = self.rng.random() < HEAVY_CHANCE
        self._sound("ai_strong_attack" if heavy else "ai_attack")
        self._sound("big_hit" if heavy else "hit")
        self._me -= 2 if heavy else 1
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
