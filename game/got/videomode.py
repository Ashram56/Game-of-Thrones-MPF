"""Video mode duel on the ROM's cvideomode / cplayer / cvideomode_ai rules (Game-of-Thrones docs/33, data/videomode_*.csv; H numbers).

Level = adjustment 132 (default 2) + the player's win count, capped at 4; player 3 HP, AI HP 3/4/5/6/7 by level; the left flipper parries, the right
flipper attacks, the action button strikes strong (idle only); a 125-tick countdown precedes the duel, timer 41 = 20 s (expiry = tie). The duelists
walk at the ROM's per-state speeds (px per update, an update every 3 ticks) and collide on a sprite overlap with a 15-tick lockout; the collision matrix
is data/videomode_collision.csv. M (not recovered): sprite width, how long an attack/parry lasts, the AI's idle thresholds."""
from mpf.core.mode import Mode

PLAYER_HEALTH = 3
AI_HEALTH = (3, 4, 5, 6, 7)
DURATION_S = 20
COUNTDOWN_S = 125 / 66.0
UPDATE_S = 3 / 66.0
LOCKOUT_UPDATES = 5                         # 15 ticks (timer 6)
WIDTH = 16                                  # M: sprite width used by the overlap test
ACTION_UPDATES = 40                         # M: an attack / strong attack / parry ends after this many updates
KNOCKBACK_UPDATES = 6                       # M
IDLE, ATTACK, PARRY, STRONG, KNOCK, LOOP, HIT, DEAD = range(8)
P_SPEED = (0, 2, -1, 1, -1, 0, -1, 0)
A_SPEED = (0, -2, 1, -1, 1, 0, 1, 0)
P_START, A_START, X_MAX = 5, 117, 133


class Duelist:
    def __init__(self, hp, x, speeds):
        self.hp, self.x0, self.x, self.speeds = hp, x, x, speeds
        self.state, self.age, self.loop = IDLE, 0, 0

    def set(self, state):
        self.state, self.age = state, 0
        if state == LOOP:
            self.loop = 5
        if state == IDLE:
            self.x = self.x0


class VideoMode(Mode):
    def mode_start(self, n=1, **kwargs):
        self._n = int(n)
        s = self.machine.settings
        base = int(s.get_setting_value("ad_video_mode_difficulty")) if "ad_video_mode_difficulty" in s._settings else 2
        self._wins = int(self.player.got_video_wins or 0) if self.player is not None else 0
        self._level = min(4, base + self._wins)
        self.rng = __import__("random").Random()
        self.me = Duelist(PLAYER_HEALTH, P_START, P_SPEED)
        self.ai = Duelist(AI_HEALTH[self._level], A_START, A_SPEED)
        self._me, self._ai = self.me.hp, self.ai.hp                     # health, read by the display and the tests
        self._active, self._lock, self._react = False, 0, None
        self.add_mode_event_handler("s_r_flipper_button_active", self._input, move=ATTACK)
        self.add_mode_event_handler("s_l_flipper_button_active", self._input, move=PARRY)
        self.add_mode_event_handler("s_up_right_flipper_button_active", self._input, move=STRONG)
        self.add_mode_event_handler("s_up_left_flipper_button_active", self._input, move=STRONG)
        self.delay.add(int(COUNTDOWN_S * 1000), self._begin, name="vm_count")
        self._state()
        self._sound("start")

    def _begin(self, **kwargs):
        self._active = True
        self.delay.add(DURATION_S * 1000, self._finish, outcome="tie", name="vm_time")
        self.delay.add(int(UPDATE_S * 1000), self._update, name="vm_update")

    def _sound(self, name):
        self.machine.events.post("got_se_fx_video_mode_" + name)

    def _state(self):
        v = self.machine.variables.set_machine_var
        self._me, self._ai = self.me.hp, self.ai.hp
        v("got_vm_me", self.me.hp)
        v("got_vm_ai", self.ai.hp)
        v("got_vm_ai_max", AI_HEALTH[self._level])
        self.machine.events.post("got_video_mode_state", me=self.me.hp, ai=self.ai.hp, n=self._n)

    # --- player input
    def _input(self, move, **kwargs):
        if not self._active:
            return
        me = self.me
        if me.state == LOOP:                                            # knockback_loop: five presses return to idle
            me.loop -= 1
            if me.loop <= 0:
                me.set(IDLE)
        elif me.state == IDLE and (move != STRONG or True):
            me.set(move)
            self._sound({ATTACK: "player_attack", STRONG: "player_strong_attack", PARRY: "parry"}[move])
            self._react = self.rng.randint(0, max(0, 6 - self._level))  # the AI reacts to attack/strong after rand(6-L) updates
            self._react_to = move

    # --- one ROM Update (every 3 ticks)
    def _update(self, **kwargs):
        me, ai = self.me, self.ai
        for d in (me, ai):
            d.age += 1
            d.x = max(d.x0 - 112 if d is ai else 0, min(X_MAX, d.x + d.speeds[d.state]))
            if d.state in (ATTACK, STRONG, PARRY) and d.age >= ACTION_UPDATES:
                d.set(IDLE)
            elif d.state in (KNOCK, HIT) and d.age >= KNOCKBACK_UPDATES:
                d.set(IDLE)
        if ai.state == LOOP and self.rng.randint(0, 9) + self._level > 4:
            ai.loop -= 1
            if ai.loop <= 0:
                ai.set(IDLE)
        if self._lock:
            self._lock -= 1
        elif ai.x - me.x < WIDTH and me.state != DEAD and ai.state != DEAD:
            self._collide()
        self._ai_think()
        self._state()
        if self.ai.hp <= 0:
            self._finish("win")
        elif self.me.hp <= 0:
            self._finish("loss")
        else:
            self.delay.add(int(UPDATE_S * 1000), self._update, name="vm_update")

    def _damage(self, d, opp_state):
        d.hp -= 1 if opp_state == ATTACK else 2
        self._sound("big_hit" if opp_state == STRONG else "hit")
        d.set(DEAD if d.hp <= 0 else HIT)

    def _react_side(self, own, opp, is_ai):
        """cplayer::OnCollision / cvideomode_ai::OnCollision (data/videomode_collision.csv)."""
        if own.state in (IDLE, KNOCK, HIT):
            if opp in (ATTACK, STRONG):
                self._damage(own, opp)
            elif opp != DEAD:
                own.set(KNOCK)
        elif own.state == LOOP:
            if opp in (ATTACK, STRONG):
                self._damage(own, opp)
        elif own.state == ATTACK:
            if opp == ATTACK:
                own.set(KNOCK)
                self._sound("counter")
            elif opp == PARRY:
                own.set(KNOCK if is_ai else LOOP)
        elif own.state == PARRY:
            if opp == ATTACK:
                self._sound("parry_hit")
            elif opp == STRONG:
                own.set(LOOP if is_ai else KNOCK)
        elif own.state == STRONG:
            if opp == ATTACK:
                self._damage(own, ATTACK)                               # a quick attack beats a strong one
            elif opp == STRONG:
                own.set(KNOCK)

    def _collide(self):
        self._lock = LOCKOUT_UPDATES
        ps, as_ = self.me.state, self.ai.state
        self._react_side(self.me, as_, False)
        self._react_side(self.ai, ps, True)

    # --- cvideomode_ai
    def _ai_think(self):
        ai, me = self.ai, self.me
        if ai.state != IDLE or me.state == DEAD:
            return
        L = self._level
        if self._react is not None:
            self._react -= 1
            if self._react <= 0:
                self._react = None
                good = self.rng.randint(0, 9) <= 6 - L
                if getattr(self, "_react_to", None) == ATTACK:
                    ai.set(ATTACK if good else PARRY)
                elif getattr(self, "_react_to", None) == STRONG:
                    ai.set(PARRY if good else ATTACK)
                else:
                    ai.set(STRONG)
                self._sound("ai_attack" if ai.state != PARRY else "ai_parry")
                return
        if self.rng.randint(0, 12 if me.state == LOOP else 25) != 0:
            return
        x = self.rng.randint(0, max(0, L - 1)) + self.rng.randint(0, 2)
        if x < 1:
            ai.set(self.rng.choice((ATTACK, PARRY, STRONG)))           # MakeBadAction
        elif x <= 4:
            ai.set(ATTACK if ai.x - me.x < 2 * WIDTH else self.rng.choice((ATTACK, PARRY)))       # MakeDecentAction
        else:
            ai.set({ATTACK: PARRY, STRONG: ATTACK, PARRY: STRONG}.get(me.state, ATTACK))              # MakeSmartAction
        self._sound("ai_strong_attack" if ai.state == STRONG else "ai_attack")

    def _finish(self, outcome, **kwargs):
        for n in ("vm_time", "vm_update", "vm_count"):
            self.delay.remove(n)
        if outcome == "win" and self.player is not None:
            self.player.got_video_wins = self._wins + 1
        self.machine.events.post("got_video_mode_result", outcome=outcome, n=self._n, level=self._level)
        self.machine.events.post("got_video_mode_finished")
