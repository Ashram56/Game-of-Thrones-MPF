"""Multiball shot sets (pure data; see got.multiballs for the rules and their confidence)."""

RAM = "s_battering_ram"
MAJORS = ("s_left_ramp_exit", "s_right_ramp_exit", "s_left_loop", "s_right_loop", "s_right_2_bank_top")

# key -> shot groups (a set = every shot of the current group once), Super multiplier of the set's jackpot total,
# sets before the mode ends (0 = until the balls drain), Super window in seconds (0 = until collected)
PHASES = {
    "blackwater": {"groups": [MAJORS], "super_mult": 6, "sets": 0, "window": 20},              # rulesheet: 5 majors, Super lit 20 s
    "wall": {"groups": [("s_left_ramp_exit", "s_right_ramp_exit", "s_u_p_left_loop"),
                        ("s_left_loop", "s_right_loop", "s_right_2_bank_top")], "super_mult": 3, "sets": 0, "window": 0,
             "super_switch": "s_kickback"},                                                    # ramps, dragon Super, then loops
    "hand_of_the_king": {"groups": [("s_left_return_lane", "s_right_return_lane", "s_left_ramp_exit", "s_right_ramp_exit")],
                         "super_mult": 1, "sets": 3, "window": 0},                              # 3 sets, then it ends
    "iron_throne": {"groups": [("s_throne", "s_left_ramp_exit", "s_right_ramp_exit", "s_left_loop", "s_right_loop")],
                    "super_mult": 2, "sets": 7, "window": 0},                                   # one set per house, 7 sets
}
