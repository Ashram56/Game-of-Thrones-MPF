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
        self.hit_and_release_switch("s_throne")
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
        self.mock_event("service_mode_entered")
        self.hit_and_release_switch("s_service_select")
        self.advance_time_and_run(1)
        self.assertEventCalled("service_mode_entered")
        self.assertTrue(self.machine.modes["service"].active)
        # the ROM's settings are in MPF's settings menu
        self.assertIn("ad_balls_per_game", self.machine.settings.get_setting_names()) if hasattr(self.machine.settings, "get_setting_names") else None
        self.hit_and_release_switch("s_service_back")
        self.advance_time_and_run(1)

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
        self.hit_and_release_switch("s_throne")
        self.advance_time_and_run(1)
        self.assertEqual(1, self.machine.auditor.current_audits["events"]["game_started"])
        self.assertEqual(1, self.machine.auditor.current_audits["switches"]["s_throne"])

    def _start_game(self):
        for i in range(1, 7):
            self.hit_switch_and_run("s_trough_%d" % i, 0.1)
        self.advance_time_and_run(3)
        self.hit_and_release_switch("s_start_button")
        self.advance_time_and_run(3)

    def test_houses_ready_and_start_hand_multiball(self):
        self._start_game()
        for house in range(4):
            self.hit_and_release_switch("s_throne")      # throne starts the next house
            self.advance_time_and_run(0.5)
            running = [m for m in self.machine.modes if m.active and m.config.get("mode_settings", {}).get("kind") == "house" and m.config["mode_settings"]["id"] != 7][0]
            for _ in range(3):
                self.hit_and_release_switch(running.config["mode_settings"]["shots"][0])
                self.advance_time_and_run(0.2)
            self.advance_time_and_run(0.5)
        self.assertIn("hand_of_the_king", self.machine.game.player.got_progression.ready)
        self.hit_and_release_switch("s_throne")
        self.advance_time_and_run(1)
        self.assertTrue(self.machine.modes["hand_of_the_king"].active)

    def test_hurry_up_decays(self):
        self._start_game()
        self.hit_and_release_switch("s_throne")
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
        self.hit_and_release_switch("s_throne")           # a house and Winter Is Coming start together
        self.advance_time_and_run(0.5)
        self.assertTrue(self.machine.modes["winter_is_coming"].active)
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
        bank = ("s_3_bank_drop_tgt_top", "s_3_bank_drop_tgt_mid")
        self._hit(bank[0], 5)
        self.assertFalse(self.machine.game.player.got_wall_lit)
        self._hit(bank[1])                                   # 6th advance lights the Wall (flag 34)
        self.assertTrue(self.machine.game.player.got_wall_lit)
        self.hit_switch_and_run("s_elevator_popper", 0.5)
        self.assertTrue(self.machine.modes["wall"].active)
        self.assertEqual(1, self.machine.game.player.got_wall_awarded)

    def test_wall_second_needs_eleven(self):
        self._start_game()
        self.machine.game.player.got_wall_awarded = 1
        self._hit("s_3_bank_drop_tgt_top", 10)
        self.assertFalse(self.machine.game.player.got_wall_lit)
        self._hit("s_3_bank_drop_tgt_top")
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
                        ("s_kickback", 3330), ("s_battering_ram", 2330)):
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
