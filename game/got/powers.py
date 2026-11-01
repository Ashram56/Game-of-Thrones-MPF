"""House choice and house powers (community rulesheet rev 1.37, M). Ids are the ROM's house ids."""
HOUSES = ("targaryen", "stark", "baratheon", "lannister", "greyjoy", "tyrell", "martell")
ACTION_SWITCH = "s_lockdown"                      # the TOP PLAYER BUTTON dedicated switch (data/switches_dedicated.csv)
STARK_WINTER_BONUS = 10000000                     # Stark persistent: +10M base value of Winter Is Coming hurry-ups
BARATHEON_WALL_ADVANCES = 2                       # Baratheon persistent: 2 Wall advances at game start
FREEZE_S = 15                                     # Targaryen Action: freeze timers for 15 s
DIREWOLF_AWARD = 5000000                          # Stark Action: completes the house, awards only 5M in its place
