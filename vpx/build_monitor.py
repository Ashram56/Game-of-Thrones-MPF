#!/usr/bin/env python3
"""Build the MPF Monitor layout for Game of Thrones from a vpx_extract.py output folder.

    python3 vpx/build_monitor.py EXTRACT_DIR [--data /path/to/Game-of-Thrones/data] [--out game/monitor] [--csv vpx]

Why not vpx_map.py: this table (VPW 1.2.1) is pure VBScript, no PinMAME. Its switch and lamp numbers
(sw1..sw84, Lampz 1..82) are the table's own, not Stern's, so numbers cannot be joined to the MPF config. Every
device here is placed by object name, using the script's own logic (see vpx/README.md for the evidence).
Names are the MPF machine config's (game/config/rom/*.yaml); lights and flashers the config lacks get the table
data's lt_* name as l_<name> / f_<name> and in_mpf_config=no in vpx/lights.csv.
"""
import argparse, csv, json, os, re, sys
from PIL import Image, ImageDraw, ImageFont

# ---- switches: MPF name -> (VPX object, note) ------------------------------------------------------------
SW = {
 "s_left_return_lane": ("sw1", "inlane (script: DoInlaneHit 0)"),
 "s_right_return_lane": ("sw2", "inlane (DoInlaneHit 1)"),
 "s_left_outlane": ("sw3", "Outlane_Hit"),
 "s_right_outlane": ("sw4", "Outlane_Hit"),
 "s_left_slingshot": ("Leftslingshot", "slingshot wall"),
 "s_right_slingshot": ("Rightslingshot", "slingshot wall"),
 "s_3_bank_drop_tgt_top": ("Target7", "LoL drop target 3 (DTHit 1), top of bank by position"),
 "s_3_bank_drop_tgt_mid": ("Target8", "LoL drop target 2 (DTHit 2)"),
 "s_3_bank_drop_tgt_btm": ("Target9", "LoL drop target 1 (DTHit 3), bottom of bank by position"),
 "s_u_p_left_loop": ("sw79", "upper PF castle loop (RegisterUPFHit 1)"),
 "s_u_p_left_target": ("Target80", "upper PF left target (STHit 13)"),
 "s_u_p_center_target": ("Target81", "upper PF center target (STHit 12)"),
 "s_u_p_right_target": ("Target82", "upper PF right target (STHit 11)"),
 "s_left_loop": ("LorbitSW30", "left orbit: Greyjoy shot (sw30a/sw30b are its lead-in triggers)"),
 "s_shooter_lane": ("swPlungerRest", "plunger lane rest trigger"),
 "s_right_loop": ("RorbitSW31", "right orbit: Martell shot"),
 "s_left_ramp_entrance": ("sw38", "left ramp entrance (sound only)"),
 "s_left_ramp_exit": ("sw39", "left ramp switch: Lannister shot, arms the lock switch sw48"),
 "s_right_ramp_entrance": ("sw41", "right ramp entrance (sound only)"),
 "s_right_ramp_exit": ("sw42", "right ramp switch: Stark shot"),
 "s_right_2_bank_top": ("Target43", "wildfire target (STHit 9): Tyrell shot"),
 "s_right_2_bank_bottom": ("Target44", "wildfire target (STHit 10): Tyrell shot"),
 "s_left_pop_bumper": ("Bumper1", "BumperLights li168"),
 "s_right_pop_bumper": ("Bumper2", "BumperLights li171"),
 "s_bottom_pop_bumper": ("Bumper3", "BumperLights li174"),
 "s_target_1": ("Target32", "gold target 1 (STHit 4, GoldHit 0, light li92)"),
 "s_target_2": ("Target33", "gold target 2 (li105)"),
 "s_target_3": ("Target34", "gold target 3 (li120)"),
 "s_target_4": ("Target35", "gold target 4 (li135)"),
 "s_target_5": ("Target36", "gold target 5 (li147)"),
 "s_left_top_lane": ("sw53", "TopLane_Hit 0"),
 "s_right_top_lane": ("sw54", "TopLane_Hit 1"),
 "s_left_spinner": ("Spinner001", "spinner"),
 "s_battering_ram": ("BatteringRam", "ram (also _Mid, _High walls)"),
 "s_lock_1": ("sw46", "ball lock lane: first ball rests at the lowest switch (inferred)"),
 "s_lock_2": ("sw47", "lock lane (inferred)"),
 "s_lock_3": ("sw48", "lock lane top; script: 'lock switch' sw48"),
 "s_elevator_popper": ("kickerfloor", "elevator bottom kicker (DestroyBall, ElevatorKick)"),
 "s_throne": ("KickerIT", "Iron Throne kicker"),
 "s_1_bank_drop": ("Target90", "right ramp drop target (DTHit 4)"),
 "s_u_p_left_lane": ("sw83", "upper PF left inlane (UPFHit 7)"),
 "s_u_p_right_lane": ("sw84", "upper PF right inlane (UPFHit 8)"),
 "s_u_p_left_10pt": ("rlbandsw85", "upper PF left sling rubber (ROM: upper playfield left sling)"),
 "s_u_p_right_10pt": ("rlbandsw86", "upper PF right sling rubber"),
 "s_u_p_left_rollover": ("sw77", "upper PF left rollover (UPFHit 3, li180)"),
 "s_u_p_right_rollover": ("sw78", "upper PF right rollover (UPFHit 5, li183)"),
}
# no VPX object, placed by hand (x, y fractions): estimates
HAND_SW = {
 "s_kickback": (0.060, 0.800, "no VPX object; at the left outlane (estimate)"),
}
# trough: six ball switches in a row, no objects (simulated stack); jam at the ball release
TROUGH = ["s_trough_6", "s_trough_5", "s_trough_4", "s_trough_3", "s_trough_2", "s_trough_1"]
# cabinet strip (no playfield object): name -> (x, y)
STRIP_Y = 0.985
CAB = {
 "s_l_flipper_button": (0.04, STRIP_Y), "s_left_flipper_eos": (0.09, STRIP_Y), "s_up_left_flipper_button": (0.14, STRIP_Y),
 "s_start_button": (0.22, STRIP_Y), "s_tournament_start_button": (0.27, STRIP_Y), "s_lockdown": (0.32, STRIP_Y),
 "s_tilt_pendulum": (0.38, STRIP_Y), "s_slam_tilt": (0.43, STRIP_Y), "s_power_interlock_sense": (0.48, STRIP_Y),
 "s_service_back": (0.54, STRIP_Y), "s_service_minus": (0.59, STRIP_Y), "s_service_plus": (0.64, STRIP_Y),
 "s_service_select": (0.69, STRIP_Y),
 "s_up_right_flipper_button": (0.79, STRIP_Y), "s_right_flipper_eos": (0.87, STRIP_Y), "s_r_flipper_button": (0.94, STRIP_Y),
 "s_left_coin": (0.10, 0.950), "s_center_coin": (0.15, 0.950), "s_right_coin": (0.20, 0.950),
 "s_fourth_coin": (0.25, 0.950), "s_fifth_coin": (0.30, 0.950),
 "s_10_points": (0.55, 0.950), "s_topper_dragon": (0.62, 0.950), "s_dragon_home": (0.69, 0.950),
}
SKIP_SW = re.compile(r"^s_dip_")

# ---- lights: VPX object -> table-data lt_ name (data/lights.csv); mpf = MPF config name if it has one -------
# (lampz = number in the script's Lampz.MassAssign)
LI = [
 # name in lights.csv, VPX object, lampz, note
 ("lt_shoot_again", "LightShootAgain", None, "insert at the shooter bottom"),
 ("lt_left_outlane", "li11", None, ""), ("lt_left_return_lane", "li14", None, ""),
 ("lt_left_3_bank_bot", "li17", None, "LoLLights(0)"), ("lt_left_3_bank_mid", "li20", None, "LoLLights(1)"),
 ("lt_left_3_bank_top", "li23", None, "LoLLights(2)"), ("lt_left_3_bank_sigil", "li26", None, "HouseShield Baratheon"),
 ("lt_hand_of_the_king", "li29", None, "round insert"), ("lt_targaryen_sigil", "li32", None, "HouseSigil(7)"),
 ("lt_iron_throne", "li35", None, "round insert"), ("lt_stark_sigil", "li38", None, "HouseSigil(1)"),
 ("lt_baratheon_sigil", "li41", None, "HouseSigil(2)"), ("lt_lannister_sigil", "li44", None, "HouseSigil(3)"),
 ("lt_greyjoy_sigil", "li47", None, "HouseSigil(4)"), ("lt_tyrell_sigil", "li50", None, "HouseSigil(5)"),
 ("lt_martell_sigil", "li53", None, "HouseSigil(6)"),
 ("lt_2x", "li56", None, "pfmuxlights"), ("lt_3x", "li59", None, "pfmuxlights"), ("lt_4x", "li62", None, "pfmuxlights"),
 ("lt_5x", "li65", None, "pfmuxlights"),
 ("lt_right_return_lane", "li71", None, ""), ("lt_right_outlane", "li74", None, ""),
 ("lt_right_2_bank_sigil", "li77", None, "HouseShield Tyrell"),
 ("lt_right_2_bank_top", "li80", None, "gear insert beside the 2-bank (li80/li83 flash with the wildfire targets)"),
 ("lt_right_2_bank_bot", "li83", None, "gear insert beside the 2-bank"),
 ("lt_left_loop_sigil", "li86", None, "HouseShield Greyjoy"), ("lt_left_loop_arrow", "li89", None, "arrow above li86"),
 ("lt_standup_target_1_l", "li92", None, "GoldTargetLights(0)"),
 ("lt_standup_target_2", "li105", None, "GoldTargetLights(1)"), ("lt_standup_target_3", "li120", None, "GoldTargetLights(2)"),
 ("lt_standup_target_4", "li135", None, "GoldTargetLights(3)"), ("lt_standup_target_5_r", "li147", None, "GoldTargetLights(4)"),
 ("lt_left_ramp_sigil", "li114", None, "HouseShield Lannister"), ("lt_left_ramp_arrow_top", "li117", None, "arrow above li114"),
 ("lt_left_ramp_lock", "li111", None, "LOCK insert"),
 ("lt_battering_ram_1_top", "li129", None, "SJP insert (SetBatteringRamLights)"),
 ("lt_battering_ram_2_mid", "li126", None, "wildfire insert"),
 ("lt_battering_ram_3_bot", "li123", None, "playfield multiplier insert (SetBatteringRamLights)"),
 ("lt_battering_ram_arrow", "li132", None, "midblue arrow above the ram inserts"),
 ("lt_right_ramp_sigil", "li141", None, "HouseShield Stark"), ("lt_right_ramp_arrow_top", "li144", None, "arrow above li141"),
 ("lt_extra_ball", "li150", None, "EXTRA BALL insert"),
 ("lt_right_loop_sigil", "li156", None, "HouseShield Martell"), ("lt_right_loop_arrow_top", "li159", None, "arrow above li156"),
 ("lt_left_top_lane", "li162", None, ""), ("lt_right_top_lane", "li165", None, ""),
 ("lt_left_pop_bumper", "li168", None, "BumperLights(0)"), ("lt_right_pop_bumper", "li171", None, "BumperLights(1)"),
 ("lt_bottom_pop_bumper", "li174", None, "BumperLights(2)"),
 ("lt_u_p_left_rollover", "li180", None, "UPFLights 3"), ("lt_u_p_right_rollover", "li183", None, "UPFLights 5"),
 ("lt_u_p_left_loop", "li186", None, "UPFLights 1, castle"), ("lt_u_p_left_target", "li189", None, "UPFLights 2"),
 ("lt_u_p_center_target", "li192", None, "UPFLights 4"), ("lt_u_p_right_target", "li195", None, "UPFLights 6"),
 ("lt_u_p_sigil", "li198", None, "UPFLights 7, shield"),
 ("lt_u_p_battle_mode_1", "li201", None, "UPF Castle MB (guess)"), ("lt_u_p_battle_mode_2", "li204", None, "guess"),
 ("lt_u_p_battle_mode_3", "li207", None, "UPF Charge (guess)"), ("lt_u_p_battle_mode_4", "li210", None, "UPF Arrows (guess)"),
 ("lt_u_p_2x", "li213", None, "UPF 2X"), ("lt_u_p_3x", "li216", None, "UPF 3X"),
]
# MPF config light names that exist for table-data lights (data/lamps.csv names -> game/config/rom/lights.yaml)
MPF_LIGHT = {"lt_left_outlane": "l_left_outlane", "lt_left_return_lane": "l_left_return_lane",
             "lt_right_outlane": "l_right_outlane", "lt_right_return_lane": "l_right_return_lane",
             "lt_extra_ball": "l_extra_ball", "lt_shoot_again": "l_shoot_again"}
HAND_LIGHT = {  # buttons: cabinet strip, MPF names
 "l_start_button": (0.22, 0.915), "l_tournament_start_button": (0.27, 0.915),
 "l_top_player_button_green": (0.32, 0.915), "l_top_player_button_red": (0.37, 0.915), "l_top_player_button_blue": (0.42, 0.915)}
# flashers: table-data lt_fl_ name -> (VPX object or None, x, y, note)
FL = [
 ("lt_fl_right_ramp", "Flasher235", None, "flasher at the right ramp"),
 ("lt_fl_left_loop", "fl242", None, "light at the spinner / left orbit"),
 ("lt_fl_pop_bumpers", "Flasher237", None, "flasher at the pop bumpers"),
 ("lt_fl_sword_lock", "Flasher236", None, "uncertain: centre-right flasher assigned to the sword/lock"),
 ("lt_fl_throne", "Flasher008", None, "uncertain: flasher near the elevator/throne"),
 ("lt_fl_battering_ram", None, ("BatteringRam", 0.0, 0.03), "no VPX flasher: placed beside the ram"),
 ("lt_fl_left_right_sling", None, (None, 0.455, 0.765), "no VPX flasher: between the slingshots"),
 ("lt_u_p_left_flood", "UPFFlasher001", None, "UPF flasher (lt_u_p_left_flood in data)"),
 ("lt_u_p_right_flood", "UPFFlasher002", None, "UPF flasher"),
 ("lt_dragon_fire", "DragonFire", None, "dragon fire flasher"),
]


def scale_colour(h):
    """Insert colour: brighten so the brightest channel is near full."""
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (1, 3, 5))
    except Exception:
        return "#ffffff"
    m = max(r, g, b) or 1
    k = 255 / m
    return "#%02x%02x%02x" % (min(255, int(r * k)), min(255, int(g * k)), min(255, int(b * k)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("extract")
    ap.add_argument("--data", default="/home/user/Game-of-Thrones/data")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(__file__), "..", "game", "config", "rom"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "game", "monitor"))
    ap.add_argument("--csv", default=os.path.dirname(os.path.abspath(__file__)))
    ap.add_argument("--device-size", type=float, default=0.035)
    a = ap.parse_args()
    import yaml
    items = {i["name"].lower(): i for i in json.load(open(os.path.join(a.extract, "items.json")))["items"]}
    lrows = {r["vpx"].lower(): r for r in csv.DictReader(open(os.path.join(a.extract, "lights_all.csv"), encoding="utf-8"))}
    cfg_sw = yaml.safe_load(open(os.path.join(a.config, "switches.yaml")))["switches"]
    cfg_li = yaml.safe_load(open(os.path.join(a.config, "lights.yaml")))["lights"]
    ltid = {r["name"]: int(r["light_id"]) for r in csv.DictReader(open(os.path.join(a.data, "lights.csv")))}
    script = open(os.path.join(a.extract, "script.vbs"), encoding="latin-1").read()
    lampz = {}
    for m in re.finditer(r"^\s*Lampz\.MassAssign\((\d+)\)\s*=\s*(\w+)", script, re.M | re.I):
        lampz.setdefault(m.group(2).lower(), int(m.group(1)))
    pf = Image.open(os.path.join(a.extract, "playfield.png")).convert("RGB")
    W, H = pf.size
    aspect = H / W

    sw = []   # dict(name, number, x, y, vpx, note, kind)
    def addsw(n, x, y, vpx, note, kind):
        sw.append(dict(name=n, number=cfg_sw[n]["number"], nx=round(x, 4), ny=round(y, 4), vpx=vpx, note=note, kind=kind))
    for n, (obj, note) in SW.items():
        it = items[obj.lower()]
        addsw(n, it["nx"], it["ny"], obj, note, "table")
    for n, (x, y, note) in HAND_SW.items():
        addsw(n, x, y, "", note, "hand")
    bx = items["ballrelease"]
    for k, n in enumerate(TROUGH):
        addsw(n, 0.50 + 0.04 * k, 0.905, "", "trough: no object (simulated ball stack), drawn in a row", "trough")
    addsw("s_trough_jam", bx["nx"], bx["ny"], "BallRelease", "trough jam: at the ball release kicker", "trough")
    for n, (x, y) in CAB.items():
        addsw(n, x, y, "", "no playfield object: cabinet strip", "cabinet")
    placed = {s["name"] for s in sw}
    missing = [n for n in cfg_sw if n not in placed and not SKIP_SW.match(n)]
    if missing:
        print("switches in the config with no placement:", missing)

    li = []
    for lt, obj, _, note in LI:
        r = lrows[obj.lower()]
        mpf = MPF_LIGHT.get(lt)
        name = mpf or "l_" + lt[3:]
        number = cfg_li[mpf]["number"] if mpf else "lt%d" % ltid[lt]
        li.append(dict(name=name, number=number, lt_name=lt, lt_id=ltid[lt], vpx=obj, lampz=lampz.get(obj.lower(), ""),
                       nx=float(r["nx"]), ny=float(r["ny"]), colour=scale_colour(r["color"]), in_mpf_config="yes" if mpf else "no", note=note))
    for n, (x, y) in HAND_LIGHT.items():
        li.append(dict(name=n, number=cfg_li[n]["number"], lt_name="", lt_id="", vpx="", lampz="", nx=x, ny=y,
                       colour="#ffffff", in_mpf_config="yes", note="button lamp: cabinet strip"))

    fl = []
    for lt, obj, hand, note in FL:
        if obj:
            r = lrows[obj.lower()]; x, y = float(r["nx"]), float(r["ny"])
        else:
            ref, dx, dy = hand
            x, y = (items[ref.lower()]["nx"] + dx, items[ref.lower()]["ny"] + dy) if ref else (dx, dy)
        fl.append(dict(name="f_" + re.sub(r"^lt_(fl_)?", "", lt), lt_name=lt, lt_id=ltid[lt], vpx=obj or "", nx=round(x, 4), ny=round(y, 4), note=note))

    # push markers apart (same rule as vpx_map.py: a marker's diameter is device_size of the picture's width)
    devs = sw + li + fl
    d = a.device_size
    for _ in range(60):
        moved = False
        for i in range(len(devs)):
            for j in range(i + 1, len(devs)):
                p, q = devs[i], devs[j]
                dx, dy = (q["nx"] - p["nx"]), (q["ny"] - p["ny"]) * aspect
                dist = (dx * dx + dy * dy) ** 0.5
                if dist < d * 0.9:
                    if dist < 1e-6:
                        dx, dy, dist = 1.0, 0.0, 1.0
                    push = (d * 0.9 - dist) / 2 + 0.0005
                    for dev, s in ((p, -1), (q, 1)):
                        if dev.get("kind") == "cabinet":
                            continue
                        dev["nx"] += s * push * dx / dist
                        dev["ny"] += s * push * dy / dist / aspect
                    moved = True
        if not moved:
            break
    for dv in devs:
        dv["nx"] = round(min(0.99, max(0.01, dv["nx"])), 4); dv["ny"] = round(min(0.995, max(0.005, dv["ny"])), 4)

    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "monitor.yaml"), "w", encoding="utf-8") as f:
        f.write("# MPF Monitor layout for Game of Thrones (x/y: fractions of playfield.jpg). Generated by vpx/build_monitor.py\n")
        f.write("# from the VPW 1.2.1 table; names are the MPF machine config's (lights/flashers the config lacks: l_/f_ + data name).\n")
        f.write("device_size: %s\n" % d)
        for sec, rows in (("switch", sw), ("light", li), ("coil", fl)):
            f.write("%s:\n" % sec)
            for r in rows:
                f.write("  %s:\n    x: %s\n    y: %s\n" % (r["name"], r["nx"], r["ny"]))
    pf.convert("RGB").save(os.path.join(a.out, "playfield.jpg"), quality=86, optimize=True)

    def wcsv(fn, rows, cols):
        with open(os.path.join(a.csv, fn), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f); w.writerow(cols)
            for r in rows: w.writerow([r.get(c, "") for c in cols])
    wcsv("switches.csv", sw, ["number", "name", "vpx", "kind", "nx", "ny", "note"])
    wcsv("lights.csv", li, ["number", "name", "lt_name", "lt_id", "vpx", "lampz", "nx", "ny", "colour", "in_mpf_config", "note"])
    wcsv("flashers.csv", fl, ["name", "lt_name", "lt_id", "vpx", "nx", "ny", "note"])

    ov = pf.copy(); dr = ImageDraw.Draw(ov)
    font = ImageFont.load_default(size=22)
    r0 = int(d * W / 2)
    for r in sw:
        x, y = r["nx"] * W, r["ny"] * H
        dr.ellipse([x - r0, y - r0, x + r0, y + r0], outline=(0, 255, 0), width=4)
        dr.text((x + r0 + 2, y - 12), r["name"][2:].replace("_", " "), fill=(120, 255, 120), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
    for r in li:
        x, y = r["nx"] * W, r["ny"] * H
        dr.ellipse([x - r0 // 2, y - r0 // 2, x + r0 // 2, y + r0 // 2], fill=tuple(int(r["colour"][i:i + 2], 16) for i in (1, 3, 5)), outline=(255, 255, 255), width=2)
    for r in fl:
        x, y = r["nx"] * W, r["ny"] * H
        dr.rectangle([x - r0 // 2, y - r0 // 2, x + r0 // 2, y + r0 // 2], outline=(255, 0, 255), width=4)
    ov.save(os.path.join(a.csv, "overlay.png"))
    ov.resize((W * 2 // 5, H * 2 // 5)).save(os.path.join(a.csv, "overlay_small.png"))
    print("switches %d (table %d, trough %d, cabinet %d, hand %d), lights %d, flashers %d" % (
        len(sw), sum(s["kind"] == "table" for s in sw), sum(s["kind"] == "trough" for s in sw),
        sum(s["kind"] == "cabinet" for s in sw), sum(s["kind"] == "hand" for s in sw), len(li), len(fl)))


if __name__ == "__main__":
    main()
