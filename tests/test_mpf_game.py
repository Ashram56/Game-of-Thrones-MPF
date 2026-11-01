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
