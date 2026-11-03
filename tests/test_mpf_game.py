"""Headless MPF game test: boots game/ on virtual hardware and plays a short game."""
import os
from mpf.tests.MpfGameTestCase import MpfGameTestCase


class TestGotGame(MpfGameTestCase):
    def get_config_file(self):
        return "config.yaml"

    def get_machine_path(self):
        return os.path.join(os.path.dirname(__file__), "..", "game")

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.machine_config_patches["mpf"]["plugins"] = ["mpf.plugins.auditor.Auditor"]

    def get_enable_plugins(self):
        return True

    def setUp(self):
        super().setUp()
        self.machine.variables.set_machine_var("credits", 20)        # the game needs credits (adjustment 66 = free play off)

    def get_platform(self):
        return "smart_virtual"

    def test_play(self):
        for i in range(1, 7):
            self.hit_switch_and_run("s_trough_%d" % i, 0.1)
        self.advance_time_and_run(3)
        self.assertEqual(6, self.machine.ball_devices["bd_trough"].balls)
        self.assertTrue(self.machine.modes["attract"].active)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(3)
        self.assertIsNotNone(self.machine.game)
        self.assertEqual(1, self.machine.game.player.number)
        self._throne()
        self.advance_time_and_run(1)
        self.assertGreater(self.machine.game.player.score, 0)

    def test_full_game(self):
        for i in range(1, 7):
            self.hit_switch_and_run("s_trough_%d" % i, 0.1)
        self.advance_time_and_run(3)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(3)
        self.post_event("start_mode_targaryen")
        self.advance_time_and_run(1)
        self.assertTrue(self.machine.modes["targaryen"].active)
        before = self.machine.game.player.score
        sw = self.machine.modes["targaryen"].config["mode_settings"]["shots"][0]
        self.hit_and_release_switch(sw[:-7] if sw.endswith("_active") else sw)
        self.advance_time_and_run(1)
        self.assertGreater(self.machine.game.player.score, before)
        for _ in range(8):
            if not self.machine.game:
                break
            self.advance_time_and_run(10)       # let the ball save run out
            if self.machine.ball_devices['bd_plunger'].balls:
                self.release_switch_and_run('s_shooter_lane', 1)     # player plunges the ball
            self.drain_all_balls()
            self.advance_time_and_run(10)
        self.assertIsNone(self.machine.game)

    def test_service_menu(self):
        for i in range(1, 7):
            self.hit_switch_and_run("s_trough_%d" % i, 0.1)
        self.advance_time_and_run(3)
        menu = self.machine.modes["servicemenu"]
        self.hit_and_release_switch("s_service_select")
        self.advance_time_and_run(0.2)
        self.assertEqual("top", menu._level)
        self.assertEqual("SERVICE MENU", menu.lines()[0])
        self.hit_and_release_switch("s_service_plus")                  # ADJUSTMENTS
        self.hit_and_release_switch("s_service_select")
        self.advance_time_and_run(0.2)
        self.assertEqual("adj", menu._level)
        name = menu._entries()[0]
        old = self.machine.settings.get_setting_value(name)
        self.hit_and_release_switch("s_service_select")                # edit
        self.hit_and_release_switch("s_service_plus")
        self.hit_and_release_switch("s_service_select")                # save
        self.advance_time_and_run(0.2)
        self.assertNotEqual(old, self.machine.settings.get_setting_value(name))
        self.hit_and_release_switch("s_service_back")                  # to top
        self.hit_and_release_switch("s_service_minus")                 # AUDITS
        self.hit_and_release_switch("s_service_select")
        self.advance_time_and_run(0.2)
        self.assertEqual("audits", menu._level)
        self.assertTrue(menu.lines()[0].startswith("AUDITS 1/"))
        self.hit_and_release_switch("s_service_back")
        self.hit_and_release_switch("s_service_back")
        self.advance_time_and_run(0.2)
        self.assertIsNone(menu._level)

    def test_settings_drive_game(self):
        self.machine.settings.set_setting_value("ad_balls_per_game", 1)
        for i in range(1, 7):
            self.hit_switch_and_run("s_trough_%d" % i, 0.1)
        self.advance_time_and_run(3)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(3)
        self.assertEqual(1, self.machine.game.balls_per_game if hasattr(self.machine.game, "balls_per_game") else self.machine.game.max_balls)

    def test_audits(self):
        for i in range(1, 7):
            self.hit_switch_and_run("s_trough_%d" % i, 0.1)
        self.advance_time_and_run(3)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(3)
        self._throne()
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.auditor.current_audits["events"]["game_started"])
        self.assertEqual(1, self.machine.auditor.current_audits["switches"]["s_throne"])

    def _throne(self):
        """Throne hit; when Choose Your Battle opens (lit houses) the action button starts the highlighted entry."""
        self.hit_and_release_switch("s_throne")
        if self.machine.modes["combos"].cyb:
            self.hit_and_release_switch("s_lockdown")
        self.advance_time_and_run(0.1)

    def _complete_running_house(self):
        running = [m for m in self.machine.modes if m.active and m.config.get("mode_settings", {}).get("kind") == "house"
                   and m.config["mode_settings"]["id"] != 7][0]
        key = running.config["mode_settings"]["key"]
        if key == "stark":
            seq = ["s_left_ramp_exit"] * 3 + ["s_left_loop"]
        elif key == "martell":
            seq = ["s_left_loop"] * 3 + ["s_left_ramp_exit"]
        elif key == "baratheon":
            seq = ["s_3_bank_drop_tgt_top", "s_3_bank_drop_tgt_mid", "s_3_bank_drop_tgt_btm"]
        elif key == "lannister":
            seq = ["s_target_1", "s_left_loop"] * 5
        elif key == "greyjoy":
            seq = ["s_left_ramp_exit", "s_right_ramp_exit", "s_left_loop", "s_right_loop", "s_kickback"]
        elif key == "tyrell":
            seq = ["s_left_ramp_exit", "s_right_ramp_exit", "s_right_2_bank_top", "s_right_2_bank_bottom", "s_right_ramp_exit"]
        elif key == "targaryen":
            for stage in range(4):                                  # four dragons, one mode start each
                for sw in ("s_left_ramp_exit", "s_left_loop", "s_right_ramp_exit", "s_right_loop", "s_kickback")[:5]:
                    self.hit_and_release_switch(sw)
                    self.advance_time_and_run(0.1)
                if stage < 3:
                    self.post_event("start_mode_targaryen")
                    self.advance_time_and_run(0.2)
            return
        else:
            seq = [running.config["mode_settings"]["shots"][0]] * 3
        for sw in seq:
            self.hit_and_release_switch(sw)
            self.advance_time_and_run(0.2)

    def _start_game(self):
        for i in range(1, 7):
            self.hit_switch_and_run("s_trough_%d" % i, 0.1)
        self.advance_time_and_run(3)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(3)

    def test_houses_ready_and_start_hand_multiball(self):
        self._start_game()
        for house in range(4):
            self._throne()      # throne starts the next house
            self.advance_time_and_run(0.5)
            self._complete_running_house()
            self.advance_time_and_run(0.5)
        self.assertIn("hand_of_the_king", self.machine.game.player.got_progression.ready)
        self.hit_and_release_switch("s_left_ramp_exit")        # do_left_ramp_exit_work starts Hand (docs/06, H)
        self.advance_time_and_run(1)
        self.assertTrue(self.machine.modes["hand_of_the_king"].active)

    def test_hurry_up_decays(self):
        self._start_game()
        self._throne()
        self.advance_time_and_run(0.5)
        self.assertTrue(self.machine.modes["targaryen"].active)
        s0 = self.machine.game.player.score
        self.advance_time_and_run(10)
        self.hit_and_release_switch("s_left_ramp_exit")
        gain = self.machine.game.player.score - s0
        self.assertGreater(gain, 0)
        self.assertLess(gain, 8000000 * 0.6)       # decayed by about half

    def test_winter_chain(self):
        self._start_game()
        self._throne()           # a house and Winter Is Coming start together
        self.advance_time_and_run(0.5)
        self.assertTrue(self.machine.modes["winter_is_coming"].active)
        self.post_event("stop_mode_targaryen")            # lit shots only count with no house mode running (docs/06)
        self.advance_time_and_run(0.2)
        for completion in range(4):
            if not self.machine.modes["winter_is_coming"].active:
                self.post_event("start_mode_winter_is_coming")
                self.advance_time_and_run(0.2)
            sw = "s_left_loop"
            for _ in range(3):                             # 3 lit shots start the hurry-up
                self.hit_and_release_switch(sw)
                self.advance_time_and_run(0.1)
            self.advance_time_and_run(4)
            super_before = self.machine.game.player.got_winter_super
            self.hit_and_release_switch(sw)                # hurry-up shot
            self.advance_time_and_run(0.5)
            self.assertGreater(self.machine.game.player.got_winter_super, super_before)
            self.assertEqual(completion == 3, self.machine.modes["winter_has_come"].active)

    def test_monitor_layout_names_exist(self):
        import yaml
        layout = yaml.safe_load(open(os.path.join(self.get_machine_path(), "monitor", "monitor.yaml")))
        sections = {"switch": self.machine.switches, "light": self.machine.lights, "flasher": getattr(self.machine, "lights", {})}
        missing = []
        for kind, devices in layout.items():
            if not isinstance(devices, dict) or kind not in sections:
                continue
            for name in devices:
                if name not in devices.__class__() and name not in sections[kind]:
                    missing.append((kind, name))
        known_gaps = [m for m in missing if not m[1].startswith(("l_", "f_"))]
        self.assertEqual([], known_gaps)

    def _hit(self, sw, n=1):
        for _ in range(n):
            self.hit_and_release_switch(sw)
            self.advance_time_and_run(0.1)

    def test_castle_levels_then_multiball(self):
        self._start_game()
        for level in range(1, 4):
            before = self.machine.game.player.score
            for sw in ("s_u_p_left_target", "s_u_p_center_target", "s_u_p_right_target"):
                self._hit(sw)
            self.assertEqual(level, self.machine.game.player.got_upper_level)
            self.assertGreaterEqual(self.machine.game.player.score - before, 2500000 + 2500000 * level)   # award #19: 5M, +2.5M per level (docs/07)
            self.assertFalse(self.machine.modes["castle"].active)
        for sw in ("s_u_p_left_target", "s_u_p_center_target", "s_u_p_right_target"):
            self._hit(sw)
        self.assertTrue(self.machine.modes["castle"].active)

    def test_wall_lit_after_six_advances_then_starts_at_elevator(self):
        self._start_game()
        self._hit("s_kickback", 5)
        self.assertFalse(self.machine.game.player.got_wall_lit)
        self._hit("s_kickback")                              # 6th advance lights the Wall (flag 34)
        self.assertTrue(self.machine.game.player.got_wall_lit)
        self.hit_switch_and_run("s_elevator_popper", 0.5)
        self.assertTrue(self.machine.modes["wall"].active)
        self.assertEqual(1, self.machine.game.player.got_wall_awarded)

    def test_wall_second_needs_eleven(self):
        self._start_game()
        self.machine.game.player.got_wall_awarded = 1
        self._hit("s_kickback", 10)
        self.assertFalse(self.machine.game.player.got_wall_lit)
        self._hit("s_kickback")
        self.assertTrue(self.machine.game.player.got_wall_lit)

    def test_midnight_madness_at_midnight_only(self):
        import time
        import got.base as base
        self._start_game()
        self.release_switch_and_run("s_shooter_lane", 1)            # ball in play
        orig = base._now
        try:
            base._now = lambda: time.struct_time((2026, 11, 2, 12, 0, 0, 0, 306, 0))
            self.advance_time_and_run(3)
            self.assertFalse(self.machine.modes["midnight_madness"].active)
            base._now = lambda: time.struct_time((2026, 11, 2, 0, 5, 0, 0, 306, 0))
            self.advance_time_and_run(3)
            self.assertTrue(self.machine.modes["midnight_madness"].active)
            before = self.machine.game.player.score
            self._hit("s_left_pop_bumper")
            self.assertGreaterEqual(self.machine.game.player.score - before, 100000)    # award #10 per switch
        finally:
            base._now = orig

    def test_winter_uses_rom_switches_and_decay(self):
        self._start_game()
        self.post_event("start_mode_winter_is_coming")
        self.advance_time_and_run(0.2)
        for sw in ("s_kickback", "s_right_2_bank_top", "s_3_bank_drop_tgt_mid"):   # ROM lit-shot switches (mask 0xEF)
            self._hit(sw)
        self.assertEqual(0, self.machine.game.player.got_winter_lit_shots)
        s0 = self.machine.game.player.got_winter_super
        self.advance_time_and_run(8)                                                # half the 16 s timer
        self._hit("s_kickback")
        gained = self.machine.game.player.got_winter_super - s0
        self.assertTrue(1500000 < gained < 2600000, gained)                        # ~2.2M of the 4M start

    def test_switch_base_points_from_rom_table(self):
        self._start_game()
        for sw, pts in (("s_left_outlane", 25000), ("s_left_return_lane", 530), ("s_left_pop_bumper", 1170),
                        ("s_kickback", 3330 + 75000), ("s_battering_ram", 2330)):     # the kickback is also the first Targaryen tickle (75,000)
            before = self.machine.game.player.score
            self._hit(sw)
            self.assertEqual(pts, self.machine.game.player.score - before, sw)

    def test_award_tables_from_scoring_csv(self):
        import yaml
        def start(key):
            return yaml.safe_load(open(os.path.join(self.get_machine_path(), "modes", key, "config", key + ".yaml")))["mode_settings"]["award"]
        self.assertEqual(500000, start("stark")["start"])           # docs/07 (H)
        self.assertEqual(100000, start("lannister")["start"])       # ROM wins over the VPX 1,000,000
        self.assertEqual(8250000, start("tyrell")["start"])
        self.assertEqual({"start": 3250000, "bump": 175000, "cap": 25000000}, start("wall"))
        self.assertEqual(1000000, start("winter_has_come")["start"])

    def test_winter_award_grows_per_completion(self):
        self._start_game()
        player = self.machine.game.player
        for _ in range(2):
            self.post_event("start_mode_winter_is_coming")
            self.advance_time_and_run(0.2)
            self._hit("s_kickback", 3)
            self.hit_and_release_switch("s_kickback")
            self.advance_time_and_run(0.3)
        self.assertEqual(4000000 + 2 * 75000, player.got_winter_award)    # BumpAward +75,000 per completion (ROM)

    def test_wall_bank_complete_advances_once(self):
        self._start_game()
        for sw in ("s_3_bank_drop_tgt_top", "s_3_bank_drop_tgt_mid", "s_3_bank_drop_tgt_btm"):
            self._hit(sw)
        self.assertEqual(1, self.machine.game.player.got_wall_advances)

    def test_iron_throne_before_hand_at_lock_entry(self):
        self._start_game()
        from got.rules_core import Progression, load_rules
        prog = Progression(load_rules())
        prog.ready.update({"hand_of_the_king", "iron_throne"})
        self.machine.game.player.got_progression = prog
        self.hit_switch_and_run("s_lock_1", 1)                 # a ball entering the lock = left ramp exit (docs/06, H)
        self.assertTrue(self.machine.modes["iron_throne"].active)
        self.assertFalse(self.machine.modes["hand_of_the_king"].active)

    def test_blackwater_starts_when_third_ball_locked(self):
        self._start_game()
        player = self.machine.game.player
        self.hit_switch_and_run("s_lock_1", 1)                 # lock not lit: the ball is kicked on, nothing locks
        self.assertEqual(0, player.got_locked_balls)
        self.hit_and_release_switch("s_lock_1")
        for i, sw in enumerate(("s_lock_1", "s_lock_2", "s_lock_3")):
            player.got_lock_lit = 1                            # Mystery / two-bank relights it before each lock (flag 36)
            gold = player.got_gold
            self.hit_and_release_switch(sw)
            self.advance_time_and_run(1)
            if i < 2:
                self.assertEqual(gold + 75, player.got_gold)
            self.assertEqual(0, player.got_lock_lit)
        self.assertTrue(self.machine.modes["blackwater"].active)
        self.assertGreaterEqual(player.got_wildfire, 15)

    def test_two_bank_lights_lock_and_ram_super_jackpot(self):
        self._start_game()
        player = self.machine.game.player
        self._hit("s_right_2_bank_top")
        self.assertTrue(player.got_lock_lit)                   # never played Blackwater, difficulty 2: any hit lights it
        player.got_lock_lit = 0
        player.got_bw_played = 1                               # after the first Blackwater only a completed bank does
        self.machine.modes["combos"]._two_bank_hit = set()
        self.hit_and_release_switch("s_right_2_bank_top")
        self.assertFalse(player.got_lock_lit)
        self.hit_and_release_switch("s_right_2_bank_bottom")
        self.assertTrue(player.got_lock_lit)
        from got.combos import jackpot_value
        player.got_wildfire = 10
        player.got_super_lit = 2
        before = player.score
        self._hit("s_battering_ram")
        self.assertEqual(0, player.got_super_lit)
        value = jackpot_value(10) * 6 * 2 + 10000000
        self.assertGreaterEqual(player.score - before, value)
        self.assertLess(player.score - before, value + 100000)   # plus the ram switch's own score

    def test_winter_lit_shots_ignored_while_house_runs(self):
        self._start_game()
        self._throne()                # house + Winter Is Coming
        self.advance_time_and_run(0.5)
        self._hit("s_kickback", 3)
        self.assertEqual(0, self.machine.game.player.got_winter_lit_shots)
        self.assertFalse(self.machine.modes["winter_is_coming"].config and getattr(self.machine.modes["winter_is_coming"], "_hurry", False))

    def test_extra_ball_house_count_follows_setting(self):
        self.machine.settings.set_setting_value("ad_house_complete_extra_ball", 3)
        self._start_game()
        events = []
        self.machine.events.add_handler("got_light_extra_ball", lambda **kwargs: events.append(1))
        for house in range(3):
            self._throne()
            self.advance_time_and_run(0.5)
            self._complete_running_house()
            self.advance_time_and_run(0.5)
        self.assertEqual([1], events)

    def _start_house(self, key):
        self._start_game()
        self.post_event("start_mode_" + key)
        self.advance_time_and_run(0.3)
        self.assertTrue(self.machine.modes[key].active)

    def test_stark_needs_three_ramps_then_an_orbit(self):
        self._start_house("stark")
        self._hit("s_left_loop")                              # orbit before the kill list is done: nothing
        self.assertTrue(self.machine.modes["stark"].active)
        self._hit("s_right_ramp_exit", 2)
        self._hit("s_left_loop")
        self.assertTrue(self.machine.modes["stark"].active)
        self._hit("s_left_ramp_exit")                          # 3rd ramp shot
        before = self.machine.game.player.score
        self._hit("s_right_loop")                              # payoff
        self.assertFalse(self.machine.modes["stark"].active)
        self.assertIn(1, self.machine.game.player.got_progression.complete)
        self.assertGreater(self.machine.game.player.score - before, 500000 + 3 * 375000 - 1)   # bumped value (ROM award)

    def test_martell_orbits_then_ramp(self):
        self._start_house("martell")
        self._hit("s_left_ramp_exit")                          # ramp too early: nothing
        self.assertTrue(self.machine.modes["martell"].active)
        self._hit("s_left_loop", 3)
        self._hit("s_right_ramp_exit")
        self.assertFalse(self.machine.modes["martell"].active)
        self.assertIn(6, self.machine.game.player.got_progression.complete)

    def test_martell_orbit_window(self):
        self._start_house("martell")
        self._hit("s_left_loop")
        self.advance_time_and_run(11)                          # window missed: the count starts again
        self._hit("s_right_loop", 2)
        self._hit("s_left_ramp_exit")
        self.assertTrue(self.machine.modes["martell"].active)

    def test_baratheon_spinner_builds_bank_cashes_in(self):
        self._start_house("baratheon")
        self._hit("s_left_spinner", 2)
        self.assertTrue(self.machine.modes["baratheon"].active)
        self._hit("s_3_bank_drop_tgt_top")
        self._hit("s_3_bank_drop_tgt_mid")
        self.assertTrue(self.machine.modes["baratheon"].active)
        before = self.machine.game.player.score
        self._hit("s_3_bank_drop_tgt_btm")
        self.assertFalse(self.machine.modes["baratheon"].active)
        self.assertGreater(self.machine.game.player.score - before, 13250000 + 2 * 375000 - 1)

    def test_lannister_five_credited_shots(self):
        self._start_house("lannister")
        self._hit("s_left_loop")                              # no gold credit: nothing
        self.assertEqual(0, self.machine.modes["lannister"]._made)
        for i in range(5):
            self._hit("s_target_%d" % (i + 1))
            self.assertTrue(self.machine.modes["lannister"].active)
            self._hit(("s_left_ramp_exit", "s_right_ramp_exit", "s_left_loop", "s_right_loop", "s_left_loop")[i])
        self.assertFalse(self.machine.modes["lannister"].active)
        self.assertIn(3, self.machine.game.player.got_progression.complete)

    def test_greyjoy_each_main_shot_once_and_timer_refresh(self):
        self._start_house("greyjoy")
        self._hit("s_left_loop", 2)                           # a repeated shot does not count
        self.advance_time_and_run(10)
        self._hit("s_right_loop")                             # refreshes the 15 s timer
        self.advance_time_and_run(10)
        self.assertTrue(self.machine.modes["greyjoy"].active)
        self._hit("s_left_ramp_exit")
        self.assertTrue(self.machine.modes["greyjoy"].active)
        self._hit("s_right_ramp_exit")
        self.assertTrue(self.machine.modes["greyjoy"].active)      # docs/13: five shots, the kickback is the fifth
        self._hit("s_kickback")
        self.assertFalse(self.machine.modes["greyjoy"].active)
        self.assertIn(4, self.machine.game.player.got_progression.complete)

    def test_tyrell_ramps_then_bank_then_right_ramp(self):
        self._start_house("tyrell")
        self._hit("s_right_2_bank_top")                       # bank before the ramps: nothing
        self._hit("s_left_ramp_exit")
        self._hit("s_right_ramp_exit")
        self._hit("s_right_2_bank_top")
        self.assertTrue(self.machine.modes["tyrell"].active)
        self._hit("s_right_2_bank_bottom")
        self.assertTrue(self.machine.modes["tyrell"].active)
        self._hit("s_right_ramp_exit")
        self.assertFalse(self.machine.modes["tyrell"].active)
        self.assertIn(5, self.machine.game.player.got_progression.complete)

    def test_targaryen_four_dragons(self):
        self._start_game()
        player = self.machine.game.player
        values = (8000000, 10000000, 12000000, 15000000)
        waves = (["s_left_ramp_exit", "s_left_loop"],
                 ["s_left_ramp_exit", "s_right_ramp_exit", "s_left_loop", "s_right_loop"],
                 ["s_left_ramp_exit", "s_left_loop", "s_right_loop"],
                 ["s_left_ramp_exit", "s_left_loop", "s_right_loop"])
        for stage in range(4):
            self.post_event("start_mode_targaryen")
            self.advance_time_and_run(0.3)
            self.assertTrue(self.machine.modes["targaryen"].active)
            self._hit("s_kickback")                              # dragon before the wave is done: nothing
            self.assertTrue(self.machine.modes["targaryen"].active)
            for sw in waves[stage]:
                self._hit(sw)
            self.machine.modes["combos"]._end()                    # Combo X window lapsed (1x)
            before = player.score
            self._hit("s_kickback")
            gained = player.score - before
            self.assertTrue(values[stage] * 0.9 < gained < values[stage] * 1.05, (stage, gained))
            self.assertFalse(self.machine.modes["targaryen"].active)
        self.assertIn(0, player.got_progression.complete)

    def test_combo_x_chain_and_sword(self):
        self._start_game()
        player = self.machine.game.player
        self._hit("s_left_loop")
        self.assertEqual(1, player.got_combo_mult)               # first shot pays 1x
        self._hit("s_right_loop")                                # follow-up of the left loop (docs/10)
        self.assertEqual(2, player.got_combo_mult)
        self._hit("s_left_ramp_exit")
        self.assertEqual(3, player.got_combo_mult)
        self._hit("s_right_ramp_exit")
        self.assertEqual(3, player.got_combo_mult)               # capped: 3 + swords(0)
        self.advance_time_and_run(10)                            # 7 s window + grace lapse
        self._hit("s_left_loop")
        self.assertEqual(1, player.got_combo_mult)
        self.advance_time_and_run(10)
        self.post_event("got_light_swords")
        self.advance_time_and_run(0.1)
        before = player.score
        self._hit("s_right_ramp_exit")
        self.assertEqual(1, player.got_swords)
        self.assertGreater(player.score - before, 500000)
        self.assertEqual(0, player.got_swords_lit)
        self._hit("s_left_loop")
        self._hit("s_right_loop")
        self._hit("s_left_ramp_exit")
        self._hit("s_right_ramp_exit")
        self.assertEqual(4, player.got_combo_mult)               # the sword raises the ceiling to 4

    def test_wildfire_ram_and_jackpot_value(self):
        from got.combos import jackpot_value
        self.assertEqual(250000, jackpot_value(0))
        self.assertEqual(250000 + 55000 + 54990 + 54960, jackpot_value(3))
        self._start_game()
        player = self.machine.game.player
        self.post_event("got_wildfire_bump", n=5)
        self.advance_time_and_run(0.1)
        self.assertEqual(5, player.got_wildfire)
        player.got_wildfire_lit = 1
        self._hit("s_battering_ram")                             # starts Wildfire
        self._hit("s_battering_ram")                             # +10 while running
        self.assertEqual(15, player.got_wildfire)

    def test_spinner_lord_of_light_video_mode(self):
        from got.combos import video_mode_score
        self.assertEqual(20000000 + 5000000 * 2, video_mode_score("win", 1, 2) // 1)
        self.assertEqual(3 * (2500000 + 3000000), video_mode_score("tie", 3, 2))
        self.assertEqual(1000000, video_mode_score("loss", 1, 2))
        self._start_game()
        player = self.machine.game.player
        combos = self.machine.modes["combos"]
        before = player.score
        self._hit("s_left_spinner")
        self.assertGreaterEqual(player.score - before, 2500)
        self._hit("s_3_bank_drop_tgt_top")
        self.assertEqual(2650, player.got_spinner_v)
        for sw in ("s_3_bank_drop_tgt_top", "s_3_bank_drop_tgt_mid", "s_3_bank_drop_tgt_btm"):
            self._hit(sw)
        self.assertEqual(1, combos._banks)
        self.assertTrue(combos._lol)                        # bank completion lights Lord of Light
        self._hit("s_left_outlane")
        self.assertFalse(combos._lol)
        self.post_event_with_params("got_video_mode_result", outcome="win", n=1, level=2)
        self.advance_time_and_run(0.1)

    def test_mystery_rom_awards(self):
        from got.mystery import Mystery
        self._start_game()
        player = self.machine.game.player
        mys = self.machine.modes["extras"].mystery
        by = {e["name"]: e for e in mys.table}
        self.assertEqual(40, len(mys.table))
        self.assertEqual(4020, by["Award Sword"]["price"])
        for name in ("Light Swords", "+10 Wild Fire", "Golden Hand", "Light Lord of Light", "Light Stark", "Hold Bonus"):
            mys.give(name)
        self.advance_time_and_run(0.1)
        self.assertEqual(1, player.got_swords_lit)
        self.assertEqual(10, player.got_wildfire)
        self.assertEqual(1, player.got_golden_hand)
        self.assertTrue(self.machine.modes["combos"]._lol)
        self.assertEqual("stark", player.got_lit_houses)
        self.assertFalse(mys.go(by["Light Swords"]))             # already lit: no-go
        self.assertFalse(mys.go(by["Golden Hand"]))
        self.assertFalse(mys.go(by["Light Stark"]))
        self.assertTrue(mys.go(by["Light Targaryen"]))
        mys.give("Award Sword")
        self.advance_time_and_run(0.1)
        self.assertEqual(1, player.got_swords)
        mys.give("Charge")
        self.assertEqual(2, player.got_upper_level)
        self.assertFalse(mys.go(by["Arrows"]))
        mys.give("Lannister button ability")
        self.assertEqual(4, player.got_button_ability)

    def _popper(self):
        self.hit_and_release_switch("s_elevator_popper")
        self.advance_time_and_run(0.5)

    def test_mystery_menu_selection_and_payment(self):
        self._start_game()
        player = self.machine.game.player
        mys = self.machine.modes["extras"].mystery
        player.got_mystery_lit = 1
        player.got_gold = 299
        self._popper()
        self.assertTrue(player.got_mystery_lit)                  # < 300 gold: cannot start
        player.got_gold = 2700
        self._popper()
        self.assertFalse(player.got_mystery_lit)
        top = mys.menu["slots"][2]
        self.assertEqual("Bigger Points", top["name"])           # most expensive affordable (2,600)
        mid = mys.menu["slots"][1]
        self.assertNotEqual(top["category"], mid["category"])
        self.assertEqual(2, mys.menu["cursor"])
        self._hit("s_l_flipper_button")                          # cursor 1: the random middle award
        self.assertEqual(1, mys.menu["cursor"])
        self._hit("s_l_flipper_button")                          # cursor 0: keep gold
        before = player.score
        self.advance_time_and_run(11)                            # timer 22 confirms
        self.assertIsNone(mys.menu)
        self.assertEqual(2700, player.got_gold)                  # keep gold pays nothing
        # buy the top award
        player.got_mystery_lit = 1
        self._popper()
        self.hit_and_release_switch("s_lockdown")
        self.advance_time_and_run(0.2)
        self.assertEqual(100, player.got_gold)
        self.assertGreaterEqual(player.score - before, 5000000)

    def test_wall_jackpot_grows_special_and_pop_lock(self):
        self._start_game()
        player = self.machine.game.player
        start = self.machine.modes["wall"].config["mode_settings"]["award"]["start"]
        self.post_event("got_bump_wall_jackpot")
        self.advance_time_and_run(0.1)
        self.assertGreater(player.got_award_wall, start)
        self.post_event("got_special")
        self.advance_time_and_run(0.1)
        self.assertEqual(1, player.got_specials)
        extras = self.machine.modes["extras"]
        extras._pop_names[999] = "Light Lock"
        extras._reels.hit = lambda reel, go: 999
        self.hit_and_release_switch("s_left_pop_bumper")
        self.advance_time_and_run(0.1)
        self.assertTrue(player.got_lock_lit)

    def test_video_mode_win_tie_and_loss(self):
        self._start_game()
        player = self.machine.game.player
        before = player.score
        self.post_event_with_params("got_video_mode_start", n=2)
        self.advance_time_and_run(0.1)
        for _ in range(5):                                              # AI health at level 2
            self.hit_and_release_switch("s_r_flipper_button")
        self.advance_time_and_run(0.1)
        self.assertFalse(self.machine.modes["videomode"].active)
        self.assertGreaterEqual(player.score - before, (5000000 * 2 + 20000000) * 2)   # win, level 2, 2X
        before = player.score
        self.post_event_with_params("got_video_mode_start", n=1)
        self.advance_time_and_run(21)                                   # no presses: the AI wins
        self.assertFalse(self.machine.modes["videomode"].active)
        self.assertEqual(500000 * 2, player.score - before)             # loss
        self.post_event_with_params("got_video_mode_start", n=1)
        self.advance_time_and_run(0.1)
        self.hit_and_release_switch("s_l_flipper_button")
        self.advance_time_and_run(0.1)
        self.assertTrue(self.machine.modes["videomode"].active)

    def test_house_tickle_lights_house_and_ability_on_completion(self):
        self._start_game()
        player = self.machine.game.player
        for i in range(3):
            self._hit("s_left_ramp_exit")                      # Lannister's tickle shot
        self.assertEqual("lannister", player.got_lit_houses)
        self._throne()                # lit houses start first
        self.advance_time_and_run(0.5)
        self.assertTrue(self.machine.modes["lannister"].active)
        gold = player.got_gold
        self.post_event_with_params("got_house_complete", house_id=3, key="lannister")
        self.advance_time_and_run(0.1)
        self.assertEqual(gold + 200, player.got_gold)
        self.assertEqual(4, player.got_button_ability)
        self.assertEqual(8, player.got_ability_uses)
        self.assertEqual("", player.got_lit_houses or "")

    def test_choose_your_battle_stack_and_pass(self):
        self._start_game()
        player = self.machine.game.player
        combos = self.machine.modes["combos"]
        player.got_lit_houses = "lannister,stark"
        self.hit_and_release_switch("s_throne")
        self.assertIsNotNone(combos.cyb)
        self.assertEqual([["stark"], ["lannister"], ["stark", "lannister"], []], combos.cyb["entries"])
        # PASS starts nothing and leaves both lit
        self.hit_and_release_switch("s_l_flipper_button")      # wraps to the last entry (PASS)
        self.assertEqual([], combos.cyb["entries"][combos.cyb["cursor"]])
        self.hit_and_release_switch("s_lockdown")
        self.advance_time_and_run(0.3)
        self.assertFalse(self.machine.modes["stark"].active or self.machine.modes["lannister"].active)
        self.assertEqual("lannister,stark", player.got_lit_houses)
        # the pair entry starts both houses together
        self.hit_and_release_switch("s_throne")
        self.hit_and_release_switch("s_r_flipper_button")
        self.hit_and_release_switch("s_r_flipper_button")      # entry 2 = the pair
        self.hit_and_release_switch("s_lockdown")
        self.advance_time_and_run(0.3)
        self.assertTrue(self.machine.modes["stark"].active and self.machine.modes["lannister"].active)

    def test_casual_mode_right_flipper_starts_and_auto_picks(self):
        self.machine.settings.set_setting_value("ad_casual_mode", 1)
        for i in range(1, 7):
            self.hit_switch_and_run("s_trough_%d" % i, 0.1)
        self.advance_time_and_run(3)
        self.hit_and_release_switch("s_r_flipper_button")      # attract: the right flipper starts the game
        self.advance_time_and_run(3)
        self.assertIsNotNone(self.machine.game)
        player = self.machine.game.player
        self.hit_and_release_switch("s_r_flipper_button")      # no house choice in casual mode
        self.assertFalse(player.got_house_picked)
        player.got_lit_houses = "stark"
        self.hit_and_release_switch("s_throne")                # auto-pick: no menu, the house starts
        self.advance_time_and_run(0.3)
        self.assertIsNone(self.machine.modes["combos"].cyb)
        self.assertTrue(self.machine.modes["stark"].active)

    def test_settings_reach_special_and_video_mode(self):
        self.machine.settings.set_setting_value("ad_special_award", 3)       # 25M points instead of a credit
        self.machine.settings.set_setting_value("ad_video_mode_difficulty", 4)
        self._start_game()
        player = self.machine.game.player
        before = player.score
        self.post_event("got_special")
        self.advance_time_and_run(0.1)
        self.assertEqual(25000000, player.score - before)
        self.post_event_with_params("got_video_mode_start", n=1)
        self.advance_time_and_run(0.1)
        self.assertEqual(7, self.machine.modes["videomode"]._ai)             # AI health at level 4

    def test_special_extra_ball_setting(self):
        self.machine.settings.set_setting_value("ad_special_award", 4)
        self._start_game()
        player = self.machine.game.player
        self.post_event("got_special")
        self.advance_time_and_run(0.1)
        self.assertEqual(1, player.extra_balls)

    def test_iron_bank_cash_in(self):
        self._start_game()
        player = self.machine.game.player
        combos = self.machine.modes["combos"]
        player.got_button_ability = 5
        player.got_ability_uses = 1
        player.got_multiplier = 2
        combos._armed = {0: 3, 1: 3}                           # c = (3 + 3) x 2 = 12
        before = player.score
        self.hit_and_release_switch("s_lockdown")
        self.assertEqual(20000000 * 2 - 18000000 + 75000 * 4 * 12, player.score - before)
        self.assertEqual(0, player.got_ability_uses)

    def _start_mb(self, key):
        self._start_game()
        self.post_event("start_mode_" + key)
        self.advance_time_and_run(0.5)
        self.assertTrue(self.machine.modes[key].active)

    def test_blackwater_rounds_jackpot_and_super(self):
        from got.combos import jackpot_value
        self._start_game()
        player = self.machine.game.player
        player.got_wildfire = 10
        self.post_event("start_mode_blackwater")
        self.advance_time_and_run(0.5)
        v = jackpot_value(10)
        self.assertEqual(v, player.got_bw_jackpot)
        shots = ("s_left_loop", "s_kickback", "s_left_ramp_exit", "s_right_ramp_exit", "s_right_loop")
        before = player.score
        self._hit(shots[0], 2)                                # round 1: each shot once; a repeat pays nothing
        self.assertGreaterEqual(player.score - before, v)
        self.assertLess(player.score - before, 2 * v)
        for sw in shots[1:]:
            self._hit(sw)
        before = player.score
        self._hit("s_battering_ram")                          # Super level 1 = V x 6 + 10M
        self.assertGreaterEqual(player.score - before, v * 6 + 10000000)
        # round 2 needs every shot twice
        for sw in shots:
            self._hit(sw, 2)
        for sw in shots:
            self._hit(sw)
        before = player.score
        self._hit("s_battering_ram")
        self.assertGreaterEqual(player.score - before, v * 12 + 10000000)

    def test_blackwater_upper_playfield_super_jackpot(self):
        self._start_game()
        player = self.machine.game.player
        self.post_event("start_mode_blackwater")
        self.advance_time_and_run(0.5)
        v = player.got_bw_jackpot
        self._hit("s_u_p_center_target")                       # state 0: any standup (a jackpot)
        self._hit("s_u_p_left_target")                        # state 1: left or right
        self._hit("s_u_p_center_target")                      # state 2: centre
        before = player.score
        self._hit("s_u_p_left_rollover")                      # state 3: Super Jackpot V x 6 + 10M
        self.assertGreaterEqual(player.score - before, v * 6 + 10000000)

    def test_blackwater_super_times_out(self):
        self._start_mb("blackwater")
        for sw in ("s_left_loop", "s_kickback", "s_left_ramp_exit", "s_right_ramp_exit", "s_right_loop"):
            self._hit(sw)
        self.advance_time_and_run(22)                         # Super lit 20 s (+ grace) only
        before = self.machine.game.player.score
        self._hit("s_battering_ram")
        self.assertLess(self.machine.game.player.score - before, 1000000)

    def test_special_pays_credit_then_points_over_limit(self):
        self._start_game()
        credits = int(self.machine.variables.get_machine_var("credits") or 0)
        player = self.machine.game.player
        score = player.score
        self.post_event("got_special")
        self.advance_time_and_run(0.1)
        self.assertEqual(1, player.got_specials)
        self.assertEqual(score, player.score)                 # adjustment 54 = 0: one credit
        self.assertEqual(credits + 1, int(self.machine.variables.get_machine_var("credits") or 0))
        self.post_event("got_special")                        # limit 1 reached: 25M points instead
        self.advance_time_and_run(0.1)
        self.assertGreaterEqual(player.score - score, 25000000)

    def test_hand_needs_two_sets_with_greyjoy(self):
        self._start_game()
        player = self.machine.game.player
        self._progression_of(player).complete.add(4)
        self.post_event("start_mode_hand_of_the_king")
        self.advance_time_and_run(0.5)
        for _ in range(2):
            for sw in ("s_left_return_lane", "s_right_return_lane", "s_left_ramp_exit", "s_right_ramp_exit"):
                self._hit(sw)
            self._hit("s_battering_ram")
        self.assertFalse(self.machine.modes["hand_of_the_king"].active)

    def _progression_of(self, player):
        return self.machine.modes["base"]._progression()

    def test_hand_ends_after_three_sets(self):
        self._start_mb("hand_of_the_king")
        for _ in range(3):
            for sw in ("s_left_return_lane", "s_right_return_lane", "s_left_ramp_exit", "s_right_ramp_exit"):
                self._hit(sw)
            self._hit("s_battering_ram")
        self.assertFalse(self.machine.modes["hand_of_the_king"].active)

    def test_wall_ramps_then_dragon_super_then_loops(self):
        self._start_mb("wall")
        player = self.machine.game.player
        for sw in ("s_left_ramp_exit", "s_right_ramp_exit", "s_u_p_left_loop"):
            self._hit(sw)
        before = player.score
        self._hit("s_kickback")                               # dragon Super
        self.assertGreater(player.score - before, 3 * 3250000 - 1)
        before = player.score
        self._hit("s_left_ramp_exit")                         # jackpots moved to the loops: a ramp no longer pays a jackpot
        self.assertLess(player.score - before, 3250000)
        for sw in ("s_left_loop", "s_right_loop", "s_right_2_bank_top"):
            self._hit(sw)
        self.assertGreater(self.machine.modes["wall"]._set_points, 0)

    def test_winter_has_come_horde_lieutenant_super(self):
        self._start_game()
        player = self.machine.game.player
        player.got_winter_super = 3000000                       # fed by the Winter Is Coming hurry-ups
        self.post_event("start_mode_winter_has_come")
        self.advance_time_and_run(0.5)
        mb = self.machine.modes["winter_has_come"]
        self.assertTrue(mb.active)
        for sw in ("s_left_ramp_exit", "s_left_ramp_exit", "s_right_ramp_exit", "s_left_loop", "s_right_loop", "s_kickback",
                   "s_3_bank_drop_tgt_top", "s_right_2_bank_bottom"):
            self._hit(sw)
        self.assertEqual("lieutenant", mb._phase)               # all seven majors collected in Horde
        self.assertEqual(3, len(mb._lieutenant))
        inv = {"left_ramp": "s_left_ramp_exit", "right_ramp": "s_right_ramp_exit", "left_loop": "s_left_loop", "right_loop": "s_right_loop",
               "kickback": "s_kickback", "bank": "s_3_bank_drop_tgt_mid", "right2": "s_right_2_bank_top"}
        before = player.score
        for _ in range(5):
            self._hit(inv[sorted(mb._lieutenant)[0]])
        self.assertEqual("horde", mb._phase)                    # 5 collected: Super paid, back to Horde
        self.assertGreaterEqual(player.score - before, 3000000)
        self.assertEqual(0, player.got_winter_super)

    def test_house_choice_cycles_with_flippers_and_baratheon_advances(self):
        self._start_game()
        player = self.machine.game.player
        self.hit_and_release_switch("s_r_flipper_button")      # Stark -> Baratheon
        self.advance_time_and_run(0.1)
        self.assertEqual(2, player.got_house_index)
        self.hit_and_release_switch("s_shooter_lane")          # (re)seat then release: the ball leaves the lane
        self.release_switch_and_run("s_shooter_lane", 0.5)
        self.assertEqual("baratheon", player.got_house)
        self.assertEqual(2, player.got_wall_advances)
        self.hit_and_release_switch("s_r_flipper_button")      # later flipper hits no longer change the house
        self.assertEqual("baratheon", player.got_house)

    def test_targaryen_starts_with_house_complete(self):
        self._start_game()
        player = self.machine.game.player
        self.hit_and_release_switch("s_l_flipper_button")      # Stark -> Targaryen (wraps from 1 to 0)
        self.release_switch_and_run("s_shooter_lane", 0.5)
        self.assertEqual("targaryen", player.got_house)
        self.assertIn(0, player.got_progression.complete)

    def test_stark_direwolf_completes_current_house_once_per_ball(self):
        self._start_game()
        player = self.machine.game.player
        self.release_switch_and_run("s_shooter_lane", 0.5)     # default Stark
        self.assertEqual("stark", player.got_house)
        self.post_event("start_mode_tyrell")
        self.advance_time_and_run(0.3)
        before = player.score
        self.hit_and_release_switch("s_lockdown")
        self.advance_time_and_run(0.3)
        self.assertEqual(5000000, player.score - before)
        self.assertIn(5, player.got_progression.complete)
        self.assertFalse(self.machine.modes["tyrell"].active)
        self.post_event("start_mode_lannister")
        self.advance_time_and_run(0.3)
        self.hit_and_release_switch("s_lockdown")              # second press on the same ball: nothing
        self.advance_time_and_run(0.3)
        self.assertTrue(self.machine.modes["lannister"].active)

    def test_targaryen_action_freezes_timers_15s(self):
        self._start_game()
        player = self.machine.game.player
        self.hit_and_release_switch("s_l_flipper_button")
        self.release_switch_and_run("s_shooter_lane", 0.5)
        self.post_event("start_mode_greyjoy")
        self.advance_time_and_run(0.3)
        self.hit_and_release_switch("s_lockdown")
        self.advance_time_and_run(10)
        self.assertTrue(self.machine.modes["greyjoy"].active)  # the 15 s Greyjoy timer is frozen
        self.advance_time_and_run(30)
        self.assertFalse(self.machine.modes["greyjoy"].active)  # it runs again after the freeze

    def test_pfx_from_ram_hits(self):
        self._start_game()
        player = self.machine.game.player
        self._hit("s_battering_ram", 3)
        self.assertEqual(0, player.got_multiplier)             # 3 hits only qualify
        self._hit("s_battering_ram")
        self.assertEqual(2, player.got_multiplier)             # 4th starts 2x
        self._hit("s_battering_ram", 4)
        self.assertEqual(3, player.got_multiplier)
        self._hit("s_battering_ram", 12)
        self.assertEqual(5, player.got_multiplier)             # capped at 5x
        before = player.score
        self._hit("s_left_outlane")
        self.assertEqual(25000, player.score - before)         # fixed switch scores are not multiplied here (ROM base points)

    def test_bonus_x_from_top_lanes(self):
        self._start_game()
        player = self.machine.game.player
        self._hit("s_left_top_lane")
        self._hit("s_left_top_lane")
        self.assertEqual(1, player.got_bonus_x)
        self._hit("s_right_top_lane")
        self.assertEqual(2, player.got_bonus_x)

    def test_gold_standups_light_mystery_and_buy_an_award(self):
        self._start_game()
        player = self.machine.game.player
        player.got_gold = 1000
        for i in range(1, 6):
            self._hit("s_target_%d" % i)
        self.assertEqual(1500, player.got_gold)                # 5 x 100
        self.assertTrue(player.got_mystery_lit)
        self.hit_switch_and_run("s_elevator_popper", 0.5)
        self.assertFalse(player.got_mystery_lit)
        self.advance_time_and_run(11)                          # the menu confirms itself (timer 22)
        self.assertLess(player.got_gold, 1500)                 # the preselected (most expensive) award was bought

    def test_coin_pop_and_video_mode_audits(self):
        self._start_game()
        self.hit_and_release_switch("s_right_coin")
        self.post_event_with_params("got_pop_award", award="Add A Ball")
        self.post_event_with_params("got_video_mode_result", outcome="win", n=1, level=2)
        self.advance_time_and_run(0.1)
        audits = self.machine.auditor.current_audits["events"]
        self.assertEqual(1, audits["au_total_right_coins"])
        self.assertEqual(1, audits["au_pops_add_a_ball"])
        self.assertEqual(1, audits["au_pops_total_awards"])
        self.assertEqual(1, audits["au_video_mode_won"])

    def test_rom_audits_are_counted(self):
        self._start_game()
        self._hit("s_left_loop", 2)
        self._hit("s_battering_ram")
        self._hit("s_l_flipper_button")
        self.post_event("start_mode_blackwater")
        self.advance_time_and_run(0.3)
        audits = self.machine.auditor.current_audits["events"]
        self.assertEqual(2, audits["au_left_loop"])
        self.assertEqual(1, audits["au_battering_ram"])
        self.assertEqual(1, audits["au_blackwater_multiball_started"])
        self.assertGreaterEqual(audits["au_total_left_flipper"], 1)

    def test_rom_audit_names_exist_in_audits_csv(self):
        import csv
        from got import audit_map as am
        names = {r["name"] for r in csv.DictReader(open(os.path.join(os.path.dirname(__file__), "..", "..", "Game-of-Thrones", "data", "audits.csv")))} \
            if os.path.exists(os.path.join(os.path.dirname(__file__), "..", "..", "Game-of-Thrones", "data", "audits.csv")) else None
        if names is None:
            self.skipTest("Game-of-Thrones data not next to this repo")
        mapped = set(am.SWITCH_AUDITS) | set(am.EVENT_AUDITS.values()) | set(am.MYSTERY_AUDITS.values()) | set(am.HOUSE_SELECT.values()) \
            | set(am.BATTLE_START.values()) | set(am.BATTLE_COMPLETE.values()) | set(am.TARGARYEN_START) | set(am.TARGARYEN_COMPLETE) \
            | set(am.PLAYER_GAMES.values())
        self.assertEqual(set(), mapped - names)

    def test_end_of_ball_bonus_formula(self):
        self._start_game()
        player = self.machine.game.player
        self._hit("s_left_loop", 4)                              # 4 playfield switch events (every_sw_work)
        extras = self.machine.modes["extras"]
        self.assertEqual(125000 + 4 * 3330, extras.bonus_total())
        player.got_gold = 1000
        player.got_bonus_x = 3
        self.assertEqual((125000 + 4 * 3330 + 300 * 1000) * 3, extras.bonus_total())
        before = player.score
        self.release_switch_and_run("s_shooter_lane", 0.5)
        self.advance_time_and_run(12)                            # ball save over
        self.drain_all_balls()
        self.advance_time_and_run(5)
        self.assertGreaterEqual(player.score - before, (125000 + 4 * 3330 + 300000) * 3)

    def test_hold_bonus_keeps_value_and_x_to_next_ball(self):
        self._start_game()
        player = self.machine.game.player
        self._hit("s_left_loop", 2)
        player.got_bonus_x = 4
        player.got_hold_bonus = 1
        self.release_switch_and_run("s_shooter_lane", 0.5)
        self.advance_time_and_run(12)
        self.drain_all_balls()
        self.advance_time_and_run(10)
        self.assertEqual(2, player.ball)                         # the next ball started
        self.assertEqual(4, player.got_bonus_x)
        self.assertEqual(2, player.got_bonus_hits)

    def test_pop_reels_pair_completes_and_never_repeats_last_award(self):
        from got import pops
        tape, names = pops.load_tape()
        self.assertEqual(112, len(tape))
        reels = pops.Reels(tape)
        awards = []
        for i in range(60):
            win = reels.hit((30, 32, 31)[i % 3], lambda x: x != reels.last)
            if win is not None:
                awards.append(win)
        self.assertGreater(len(awards), 3)
        self.assertTrue(all(a != b for a, b in zip(awards, awards[1:])))

    def test_pop_award_is_paid_in_game(self):
        self._start_game()
        player = self.machine.game.player
        got = []
        self.machine.events.add_handler("got_pop_award", lambda **kwargs: got.append(kwargs["award"]))
        for i in range(40):
            self._hit(("s_left_pop_bumper", "s_bottom_pop_bumper", "s_right_pop_bumper")[i % 3])
        self.assertTrue(got)

    def _lit(self, name):
        return self.machine.lights["l_" + name].get_color() is not None and sum(self.machine.lights["l_" + name].get_color().rgb) > 0

    def test_lights_attract_gi_start_and_house(self):
        for i in range(1, 7):
            self.hit_switch_and_run("s_trough_%d" % i, 0.1)
        self.advance_time_and_run(3)
        self.assertTrue(self._lit("backbox_gi"))
        self.assertTrue(self._lit("start_button"))            # attract show lights the Start button
        seen = set()
        for i in range(8):                                    # the sigils sweep through the houses
            self.advance_time_and_run(0.5)
            seen |= {h for h in ("targaryen", "stark", "baratheon", "lannister", "greyjoy", "tyrell", "martell") if self._lit(h + "_sigil")}
        self.assertGreaterEqual(len(seen), 5)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(3)
        self.assertFalse(self._lit("stark_sigil"))            # show stopped with attract
        self.assertTrue(self._lit("start_button"))            # ball 1
        self.post_event("start_mode_stark")
        self.advance_time_and_run(0.5)
        self.assertTrue(self._lit("stark_sigil"))             # running house
        self.hit_and_release_switch("s_left_pop_bumper")
        self.advance_time_and_run(0.05)
        self.assertTrue(self._lit("fl_pop_bumpers"))          # flasher pulse
        self.advance_time_and_run(0.5)
        self.assertFalse(self._lit("fl_pop_bumpers"))

    def _trough(self):
        for i in range(1, 7):
            self.hit_switch_and_run("s_trough_%d" % i, 0.1)
        self.advance_time_and_run(3)

    def test_start_needs_a_credit_and_coins_add_them(self):
        self._trough()
        self.machine.variables.set_machine_var("credits", 0)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(2)
        self.assertIsNone(self.machine.game)
        self.hit_and_release_switch("s_left_coin")
        self.hit_and_release_switch("s_right_coin")
        self.assertEqual(2, self.machine.variables.get_machine_var("credits"))
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(3)
        self.assertIsNotNone(self.machine.game)
        self.assertEqual(1, self.machine.variables.get_machine_var("credits"))

    def _entry_started(self, seen):
        return bool(seen)

    def test_attract_pages_and_high_score_entry_and_match(self):
        self._trough()
        pages = []
        self.machine.events.add_handler("got_attract_page", lambda **kwargs: pages.append(kwargs["line1"]))
        self.advance_time_and_run(30)
        self.assertIn("GAME OF THRONES", pages)
        self.assertIn("GRAND CHAMPION", pages)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(3)
        self.machine.game.player.score = 80000000                      # beats the grand champion (75 M)
        seen = []
        self.machine.events.add_handler("got_initials", lambda **kwargs: seen.append(kwargs["line2"]))
        self.machine.events.add_handler("got_game_over", lambda **kwargs: seen.append("OVER"))
        self.machine.game.balls_per_game = 1 if False else self.machine.game.balls_per_game
        for _ in range(6):
            if self._entry_started(seen):
                break
            self.advance_time_and_run(10)
            if self.machine.ball_devices["bd_plunger"].balls:
                self.release_switch_and_run("s_shooter_lane", 1)
            self.drain_all_balls()
        self.advance_time_and_run(1)
        for ch in 1, 2, 3:                                             # right flipper once = B, then Start
            self.hit_and_release_switch("s_r_flipper_button")
            self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(10)
        t = self.machine.modes["scoreboard"].table()
        self.assertEqual("BBB", t[0]["name"])
        self.assertGreaterEqual(t[0]["score"], 80000000)
        self.assertIn("OVER", seen)

    def test_sound_variants_pick_one_at_random(self):
        import json
        v = json.load(open(os.path.join(os.path.dirname(__file__), "..", "game", "config", "rom", "sound_variants.json")))
        ev, names = next(iter(v.items()))
        played = []
        for n in names:
            self.machine.events.add_handler(n, lambda **kwargs: played.append(1))
        self.post_event(ev)
        self.advance_time_and_run(0.1)
        self.assertEqual(1, len(played))

    def test_rom_display_effect_plays_sounds_and_clip(self):
        self._start_game()
        played = []
        self.machine.events.add_handler("got_def_stark_start", lambda **kwargs: played.append("def"))
        self.post_event("start_mode_stark")
        self.advance_time_and_run(0.5)
        self.assertIn("def", played)
        self.assertIn("got_def_stark_start", self.machine.config["slide_player"])        # its DMD clip

    def test_background_music_follows_state(self):
        tunes = []
        self.machine.events.add_handler("got_se_tune_main_play", lambda **kwargs: tunes.append("main"))
        self.machine.events.add_handler("got_se_tune_stark", lambda **kwargs: tunes.append("stark"))
        self._start_game()
        self.advance_time_and_run(0.5)
        self.assertEqual(["main"], tunes)
        self.post_event("start_mode_stark")
        self.advance_time_and_run(0.5)
        self.assertEqual(["main", "stark"], tunes)
        self.assertEqual(-1, self.machine.config["sound_player"]["got_se_tune_stark"][
            next(iter(self.machine.config["sound_player"]["got_se_tune_stark"]))]["loops"])

    def test_live_text_values_are_set_before_the_effect(self):
        self._start_game()
        self.machine.game.player.score += 2500000
        self.advance_time_and_run(0.1)
        self.post_event("got_def_tilt_warning")
        self.advance_time_and_run(0.1)
        self.assertEqual("2,500,000", self.machine.variables.get_machine_var("got_arg_award"))
        self.assertEqual("2,500,000", self.machine.variables.get_machine_var("got_arg_score"))

    def test_live_timer_value_follows_running_mode_timer(self):
        self._start_game()
        self.post_event("start_mode_stark")
        self.advance_time_and_run(3)
        self.post_event("got_def_tilt_warning")
        self.advance_time_and_run(0.1)
        self.assertGreater(int(self.machine.variables.get_machine_var("got_arg_timer")), 0)

    def test_live_shots_left_for_greyjoy(self):
        self._start_game()
        self.post_event("start_mode_greyjoy")
        self.advance_time_and_run(1)
        self.hit_and_release_switch("s_left_loop")
        self.advance_time_and_run(0.5)
        self.post_event("got_def_greyjoy_BG")
        self.advance_time_and_run(0.1)
        self.assertEqual("4", self.machine.variables.get_machine_var("got_arg_shots"))

    def test_live_shots_left_for_winter_has_come(self):
        self._start_game()
        self.post_event("start_mode_winter_has_come")
        self.advance_time_and_run(1)
        self.post_event("got_def_winter_mball_BG")
        self.advance_time_and_run(0.1)
        self.assertEqual("7", self.machine.variables.get_machine_var("got_arg_shots"))

    def test_ready_music_when_wall_is_lit(self):
        tunes = []
        self.machine.events.add_handler("got_se_tune_wall_multiball_ready", lambda **kwargs: tunes.append(1))
        self._start_game()
        self.machine.game.player.got_wall_lit = 1
        self.post_event("got_wall_lit")
        self.advance_time_and_run(0.5)
        self.assertEqual([1], tunes)

    def test_rom_lamp_effect_follows_its_display_effect(self):
        self._start_game()
        self.post_event("got_def_extra_ball_lit")               # def_extra_ball_lit requests lef_extra_ball_lit (extraction)
        self.advance_time_and_run(0.1)
        self.assertTrue(self._lit("extra_ball"))
        self.advance_time_and_run(0.3)
        self.assertFalse(self._lit("extra_ball"))
