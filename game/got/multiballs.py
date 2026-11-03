"""Multiball phases: shot sets that light a Super Jackpot at the battering ram. Rules: community rulesheet (pinballrulesheets.com
rev 1.37) over the ROM award values; the set/ram structure is M, the Super multiplier is a placeholder (CFG: the ROM's
AwardSuperJackpot formula is not recovered)."""
from got import state
from got.award_mode import AwardMode
from got.combos import jackpot_value
from got.phases import PHASES, RAM


# ciron::GetCastleFromShotID (docs data/ciron_castle_shots.csv, H): the castle whose shot was made -> effect def_award_iron idx
CASTLE_OF = {"s_right_ramp_exit": 0, "s_right_2_bank_top": 1, "s_right_2_bank_bottom": 1, "s_left_loop": 2, "s_right_loop": 4,
             "s_3_bank_drop_tgt_top": 5, "s_3_bank_drop_tgt_mid": 5, "s_3_bank_drop_tgt_btm": 5, "s_kickback": 6, "s_left_ramp_exit": 7}


class SetMultiball(AwardMode):
    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        self._ph = PHASES[self._cfg["key"]]
        self._group = 0
        self._done = set()
        self._set_points = 0
        self._super_until = None
        self._sets = 0
        self._sets_needed = self._ph["sets"]
        if self._cfg["key"] == "hand_of_the_king":      # GetTotalLevelsNeeded: 2 with the Greyjoy bit, else 3 (docs/13)
            prog = self.player.got_progression
            self._sets_needed = 2 if prog and 4 in prog.complete else 3
            done = set(prog.complete) if prog else set()
            self._house_bits = done
            self.machine.events.post("got_hand_started_houses", houses=sorted(done))   # audits 155-161 (ChalkTheStartAudits, inferred per completed house)
            # docs/18 1.6 (H): completed houses change the Hand of the King
            if 0 in done:                                # Targaryen: +500,000 on the shot value
                self._award.value += 500000
            self._super_bonus = (100000000 if 3 in done else 0) + (15000000 if 5 in done else 0)   # Lannister +100M, Tyrell +15M
        else:
            self._super_bonus = 0

    def _group_shots(self):
        groups = self._ph["groups"]
        return groups[self._group % len(groups)]

    def _super_switch(self):
        return self._ph.get("super_switch", RAM)

    def _super_lit(self):
        if self._super_until is None:
            return False
        if self._super_until == 0:
            return True
        return self.machine.clock.get_time() <= self._super_until

    def _accepts(self, sw):
        self._shots = 0
        if sw == self._super_switch() and self._super_lit():
            self._collect_super()
            return False
        if sw in self._group_shots() and sw not in self._done and not self._super_lit():
            self._done.add(sw)
            self._last_sw = sw
            return True
        return False

    def _pay(self):
        super()._pay()
        self._set_points += self._last_points
        castle = CASTLE_OF.get(getattr(self, "_last_sw", None)) if self._cfg["key"] == "iron_throne" else None
        if castle is not None:
            self.machine.events.post("got_def_award_iron_%d" % castle)      # the ROM shows the castle's award with its table layout
        if self._done >= set(self._group_shots()):
            window = self._ph["window"]
            self._super_until = 0 if not window else self.machine.clock.get_time() + window
            self.machine.events.post("got_%s_super_lit" % self._cfg["key"])

    def _collect_super(self):
        points = (int(self._set_points * self._ph["super_mult"]) + self._super_bonus) * (self.player.got_multiplier or 1)
        self.player.score += points
        self.machine.events.post("got_%s_super" % self._cfg["key"], points=points)
        self._sets += 1
        self._done, self._set_points, self._super_until = set(), 0, None
        self._group += 1
        if self._sets_needed and self._sets >= self._sets_needed:
            self.machine.events.post("multiball_%s_ended" % self._cfg["key"])
            self.stop()


BIT_OF = {"s_3_bank_drop_tgt_top": 1, "s_3_bank_drop_tgt_mid": 1, "s_3_bank_drop_tgt_btm": 1, "s_left_loop": 2, "s_kickback": 4,
          "s_left_ramp_exit": 8, "s_right_ramp_exit": 32, "s_right_loop": 64, "s_right_2_bank_top": 128, "s_right_2_bank_bottom": 128}
HORDE_MASK = (1, 2, 4, 8, 32, 64, 128)                                  # 239 (docs/29)
MAIN_MASK = (2, 4, 8, 32, 64)                                           # 110
BOSS_TRIPLES = ((2, 4, 64), (8, 4, 32), (2, 8, 32), (64, 8, 32), (2, 8, 64), (2, 32, 64))   # table 0x28ea68
FROZEN_BIT = 8
LIEUTENANT_NEEDED = 5
HORDE_TIMER_S, BOSS_TIMER_S, FROZEN_TIMER_S = 10, 10, 8


class WinterHasComeMode(AwardMode):
    """Winter Has Come on the ROM's cmball_winter state machine (docs/29, data/cmball_winter_*.csv; H logic).
    Phase 0 horde: the seven shots (mask 239) each pay award 18 once; timer 29 (10 s, restarted by every hit) lights one removed shot again.
    Phase 1: three boss shots from a random triple, 5 hits; a hit pays award 18 x (combo + 2) and the shot jumps; every boss shot has its own 10 s timer
    that removes it; the 5th hit pays (3 V + 30M) x combo and returns to phase 0; if all three dried up: frozen.
    Phase 2: left ramp exit only (8 s) adds a ball; the ramp thaws (new triple), the timer returns to the horde."""

    rng = None

    def mode_start(self, **kwargs):
        import random
        super().mode_start(**kwargs)
        self.rng = self.rng or random.Random()
        self._horde_start()

    @property
    def _phase_name(self):
        return ("horde", "lieutenant", "frozen")[self._ph_idx]

    @property
    def _phase(self):                                          # compatibility name used by the tests / display
        return {0: "horde", 1: "lieutenant", 2: "frozen"}[self._ph_idx]

    @property
    def _lieutenant(self):
        return set(self._boss)

    @property
    def shots_left(self):
        if self._ph_idx == 0:
            return len(self._mask)
        return max(0, self._need)

    def _value(self):
        return int(self._award.value)

    def _combo(self):
        return int(self.player.got_combo_mult or 1)

    def _gm(self):
        return int(self.player.got_multiplier or 1)

    def _bump(self):
        self._award.bump()
        setattr(self.player, self._award_key, self._award.value)

    def _cancel(self):
        for n in ("whc_horde", "whc_frozen", "whc_boss_2", "whc_boss_4", "whc_boss_8", "whc_boss_32", "whc_boss_64"):
            self.delay.remove(n)

    # --- phase 0
    def _horde_start(self):
        self._cancel()
        self._ph_idx, self._mask, self._boss, self._need = 0, set(HORDE_MASK), {}, 0
        self._removed = []
        self.delay.add(HORDE_TIMER_S * 1000, self._horde_timer, name="whc_horde")

    def _horde_timer(self, **kwargs):                           # AddBackHordeShot: one removed shot is lit again (sound 188)
        if self._removed:
            bit = self.rng.choice(self._removed)
            self._removed.remove(bit)
            self._mask.add(bit)
        self.delay.add(HORDE_TIMER_S * 1000, self._horde_timer, name="whc_horde")

    # --- phase 1
    def _boss_start(self):
        self._cancel()
        self._ph_idx, self._need = 1, LIEUTENANT_NEEDED
        self._boss = {b: True for b in self.rng.choice(BOSS_TRIPLES)}
        for b in self._boss:
            self.delay.add(BOSS_TIMER_S * 1000, self._boss_timer, name="whc_boss_%d" % b, bit=b)

    def _boss_timer(self, bit, **kwargs):                       # a dried up boss shot (sound 189)
        self._boss.pop(bit, None)
        if not self._boss:
            self._frozen_start()

    # --- phase 2
    def _frozen_start(self):
        self._cancel()
        self._ph_idx, self._boss = 2, {}
        self.delay.add(FROZEN_TIMER_S * 1000, self._frozen_timer, name="whc_frozen")
        self.machine.events.post("got_winter_has_come_frozen")
        try:
            self.machine.multiballs["mb_winter_has_come"].add_a_ball()
        except Exception:
            self.machine.playfield.add_ball(1)
            self.machine.events.post("got_add_a_ball")

    def _frozen_timer(self, **kwargs):
        self._horde_start()

    def _shot(self, sw=None, **kwargs):
        if state.fast_loop(self.machine, sw):
            return
        bit = BIT_OF.get(sw)
        p = self.player
        if bit is None:
            return
        if self._ph_idx == 0:
            if bit not in self._mask:
                return
            self._mask.discard(bit)
            self._removed.append(bit)
            points = self._value() * self._combo() * self._gm()
            p.score += points
            self._bump()
            self.machine.events.post("got_winter_has_come_horde", points=points)
            self.delay.remove("whc_horde")
            if self._mask:
                self.delay.add(HORDE_TIMER_S * 1000, self._horde_timer, name="whc_horde")
            else:
                self._boss_start()
        elif self._ph_idx == 1:
            if bit not in self._boss:
                return
            self.delay.remove("whc_boss_%d" % bit)
            del self._boss[bit]
            self._need -= 1
            if self._need <= 0:                                  # DoFinalBossAward: static (3 V + 30M) x combo, then bump
                points = (3 * self._value() + 30000000) * self._combo() * self._gm()
                p.score += points
                self._bump()
                self.machine.events.post("got_winter_has_come_super", points=points)
                self._horde_start()
                return
            points = self._value() * (self._combo() + 2) * self._gm()
            p.score += points
            self._bump()
            self.machine.events.post("got_winter_has_come_lieutenant", points=points)
            free = [b for b in MAIN_MASK if b not in self._boss and b != bit]
            new = self.rng.choice(free)
            self._boss[new] = True
            self.delay.add(BOSS_TIMER_S * 1000, self._boss_timer, name="whc_boss_%d" % new, bit=new)
        elif bit == FROZEN_BIT:                                  # thawed
            self.delay.remove("whc_frozen")
            self.machine.events.post("got_winter_has_come_thawed")
            self._boss_start()

    def mode_stop(self, **kwargs):
        self._cancel()
        super().mode_stop(**kwargs)


UPPER_ALL = ("s_u_p_left_target", "s_u_p_center_target", "s_u_p_right_target", "s_u_p_left_rollover", "s_u_p_right_rollover")
UPPER_STATES = (("s_u_p_left_target", "s_u_p_center_target", "s_u_p_right_target"), ("s_u_p_left_target", "s_u_p_right_target"),
                ("s_u_p_center_target",), ("s_u_p_left_rollover", "s_u_p_right_rollover"))      # masks 0x700000 / 0x500000 / 0x200000 / 0x1800000


class BlackwaterMode(AwardMode):
    """docs/13 (H): rounds R = 1, 2, 3 (then 3 again). Every round arms the five mask-0x6e shots R times each (5, 10, 15 hits);
    a hit pays V x combo x R (V does not rise); the last hit of the round lights the Super Jackpot (level R) for 20 s + 1.4 s
    grace; a ram shot collects V x 6 x R + 10M, otherwise the window expires; then the next round starts. V =
    CalcJackpotValue(wildfire points) is set at the start (cblackwater::Start)."""

    SHOTS = ("s_left_loop", "s_kickback", "s_left_ramp_exit", "s_right_ramp_exit", "s_right_loop")
    SUPER_S = 20 + 93 / 66.0

    def mode_start(self, **kwargs):
        super().mode_start(**kwargs)
        p = self.player
        p.got_bw_jackpot = jackpot_value(int(p.got_wildfire or 0))
        self._round = 1
        self._upper = 0
        for sw in UPPER_ALL:
            self.add_mode_event_handler(sw + "_active", self._upper_shot, sw=sw)
        self._super_t0 = 0
        self._vars_timer = self.machine.clock.schedule_interval(self._publish, 0.2)
        self._arm()
        self.machine.events.post("got_blackwater_bg_show")

    def mode_stop(self, **kwargs):
        self.machine.clock.unschedule(self._vars_timer)
        self.machine.events.post("got_blackwater_bg_hide")
        super().mode_stop(**kwargs)

    def _publish(self, **kwargs):
        """def_blackwater_bg variables (docs/27 section 6): page = round, +3 while the super window runs; seconds left from timer 28."""
        v = self.machine.variables
        left = max(0, int(self.SUPER_S - (self.machine.clock.get_time() - self._super_t0) + 0.999)) if self._super else 0
        v.set_machine_var("got_bw_state", str(self._round + (3 if self._super else 0)))
        v.set_machine_var("got_arg_score", "{:,}".format(int(self.player.score)))
        v.set_machine_var("got_arg_timer", str(min(20, left)))

    def _upper_shot(self, sw, **kwargs):
        if state.fast_loop(self.machine, sw):
            return
        """DoUpperPlayfieldWork (docs/14, H masks/order): any standup -> left or right standup -> centre standup -> an upper
        rollover. Steps 0-2 pay a jackpot, step 3 the Super Jackpot (upper multiplier 1: M)."""
        p = self.player
        if sw not in UPPER_STATES[self._upper]:
            return
        v = int(p.got_bw_jackpot)
        if self._upper < 3:
            points = v * self._round * (p.got_multiplier or 1)
            self._upper += 1
        else:
            points = (v * 6 + 10000000) * (p.got_multiplier or 1)
            self._upper = 0
            self.machine.events.post("got_blackwater_super", points=points, level=1)
        p.score += points

    def _arm(self):
        self._left = {sw: self._round for sw in self.SHOTS}
        self._super = 0
        self.machine.events.post("got_blackwater_round", round=self._round)

    def _shot(self, sw=None, **kwargs):
        if state.fast_loop(self.machine, sw):
            return
        p = self.player
        if sw == RAM and self._super:
            level = self._super
            self.delay.remove("bw_super")
            points = (int(p.got_bw_jackpot) * 6 * level + 10000000) * (p.got_multiplier or 1)
            p.score += points
            self.machine.events.post("got_blackwater_super", points=points, level=level)
            self._next_round()
            return
        if self._super or self._left.get(sw, 0) <= 0:
            return
        self._left[sw] -= 1
        points = int(p.got_bw_jackpot) * (p.got_combo_mult or 1) * self._round * (p.got_multiplier or 1)
        p.score += points
        self.machine.events.post("got_blackwater_jackpot", points=points, round=self._round)
        if not any(self._left.values()):
            self._super = self._round
            self._super_t0 = self.machine.clock.get_time()
            self.delay.add(int(self.SUPER_S * 1000), self._super_expired, name="bw_super")
            self.machine.events.post("got_blackwater_super_lit", level=self._super)

    def _super_expired(self, **kwargs):
        self._next_round()

    def _next_round(self):
        self._round = min(self._round + 1, 3)
        self._arm()
