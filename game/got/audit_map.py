"""ROM audit counters (Game-of-Thrones data/audits.csv names) -> MPF switches and events. Pure data.
Not mapped (no matching feature or no data): coins/credits/meters, score and game-time histograms, ball search and lost balls,
fixture and auto-play, video mode, wildfire/lock/sword/PFx mystery awards, all pop-bumper awards, Lord of Light, Castle shot counters."""

SWITCH_AUDITS = {
    "au_total_left_flipper": "s_l_flipper_button", "au_total_right_flipper": "s_r_flipper_button",
    "au_left_3_bank_drop_target_top": "s_3_bank_drop_tgt_top", "au_left_3_bank_drop_target_middle": "s_3_bank_drop_tgt_mid",
    "au_left_3_bank_drop_target_bottom": "s_3_bank_drop_tgt_btm", "au_left_loop": "s_left_loop", "au_right_loop": "s_right_loop",
    "au_left_ramp": "s_left_ramp_exit", "au_right_ramp": "s_right_ramp_exit", "au_dragon_kickback": "s_kickback",
    "au_battering_ram": "s_battering_ram", "au_elevator_eject": "s_elevator_popper", "au_throne_eject": "s_throne",
}

EVENT_AUDITS = {
    "ball_ended": "au_total_balls_played", "tilt": "au_total_tilts", "ball_save_default_saving_ball": "au_total_balls_saved",
    "extra_ball_group_default_awarded": "au_total_extra_balls", "game_ended": "au_total_plays_ended",
    "mode_blackwater_started": "au_blackwater_multiball_started", "mode_wall_started": "au_wall_multiball_started",
    "mode_hand_of_the_king_started": "au_hand_multiball_started", "mode_iron_throne_started": "au_iron_multiball_started",
    "mode_winter_has_come_started": "au_winter_multiball_started", "mode_castle_started": "au_castle_multiball_started",
    "got_winter_has_come_super": "au_winter_super_jackpot", "got_castle_super": "au_castle_super_jackpot",
    "got_wall_super": "au_wall_super_jackpot", "got_iron_throne_super": "au_iron_super_jackpot",
    "got_hand_of_the_king_super": "au_hand_super_jackpot_hurry_up",
    "mode_winter_is_coming_started": "au_start_winter_is_coming", "got_winter_is_coming_award": "au_complete_winte_is_coming",
    "got_mystery_award": "au_mystery_total_awards",
}

MYSTERY_AUDITS = {"big_points": "au_mystery_big_points", "bigger_points": "au_mystery_bigger_points",
                  "biggest_points": "au_mystery_biggest_points", "bonus_x_1": "au_mystery_1x_bonus_multiplier",
                  "bonus_x_2": "au_mystery_2x_bonus_multiplier", "bonus_x_3": "au_mystery_3x_bonus_multiplier",
                  "advance_wall": "au_mystery_advance_wall_mb", "light_extra_ball": "au_mystery_extra_ball",
                  "hold_bonus": "au_mystery_bonus_held"}

HOUSE_SELECT = {"targaryen": "au_house_select_targaryen", "stark": "au_house_select_stark", "baratheon": "au_house_select_baratheon",
                "lannister": "au_house_select_lannister", "greyjoy": "au_house_select_grejoy", "tyrell": "au_house_select_tyrell",
                "martell": "au_house_select_martell"}

BATTLE_START = {"stark": "au_battle_house_stark", "baratheon": "au_battle_house_baratheon", "lannister": "au_battle_house_lannister",
                "greyjoy": "au_battle_house_grejoy", "tyrell": "au_battle_house_tyrell", "martell": "au_battle_house_martell"}
BATTLE_COMPLETE = {"stark": "au_battle_stark_complete", "baratheon": "au_battle_baratheon_complete",
                   "lannister": "au_battle_lannister_complete", "greyjoy": "au_battle_greyjoy_complete",
                   "tyrell": "au_battle_tyrell_complete", "martell": "au_battle_martell_complete"}
TARGARYEN_START = ("au_battle_house_targaryen1", "au_battle_house_targaryen2", "au_battle_house_targaryen3")
TARGARYEN_COMPLETE = ("au_battle_targaryen1_complete", "au_battle_targaryen2_complete", "au_battle_targaryen3_complete")
PLAYER_GAMES = {1: "au_total_one_player_games", 2: "au_total_two_player_games", 3: "au_total_three_player_games",
                4: "au_total_four_player_games"}
