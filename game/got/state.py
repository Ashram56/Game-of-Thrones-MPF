"""Game-state predicates shared by the base mode and Winter (rules: Game-of-Thrones docs/06, H unless noted)."""


def multiball_running(machine):
    return any(m.active and m.config.get("mode_settings", {}).get("kind") == "multiball" for m in machine.modes)


def house_running(machine):
    """A house mode (ids 0-6) runs; Winter Is Coming (7) is not counted."""
    return any(m.active and m.config.get("mode_settings", {}).get("kind") == "house" and m.config["mode_settings"]["id"] != 7
               for m in machine.modes)


def _prog(player):
    return player.got_progression or None


def iron_startable(machine, player):
    """ciron::OkForStart: flag 40 (all 7 houses done) and no multiball running."""
    prog = _prog(player)
    return bool(prog and "iron_throne" in prog.ready and "iron_throne" not in prog.started and not multiball_running(machine))


def hand_startable(machine, player):
    """chand::OkToStart: ready (4 houses done), no multiball running, no house mode running."""
    prog = _prog(player)
    return bool(prog and "hand_of_the_king" in prog.ready and "hand_of_the_king" not in prog.started
                and not multiball_running(machine) and not house_running(machine))


def fast_loop(machine, sw):
    """docs/22 1c (H): a right loop inside the 1.45 s launch window is routed to the elevator; the normal right-loop shot is skipped."""
    return sw == "s_right_loop" and bool(getattr(machine, "got_fast_loop", False))
