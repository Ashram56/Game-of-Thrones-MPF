"""Credits, attract pages, high scores with initials, match and game over (always-on mode).

Rules from data/adjustments.csv (credit limit 65, free play 66, match percentage 61) and docs/03 section 5 (grand champion
75 M, #1-#4 50/40/30/20 M). CFG, the ROM's screens are not decoded for Spike 1: the pages, the initials entry (flippers
change the letter, Start confirms) and the match draw (a random tens digit, award = one credit) are mine; default initials GOT.
"""
import json
import os
import random

from mpf.core.mode import Mode

# docs/22 and data/hstd_defaults.csv: default initials and scores of the five ranks
DEFAULTS = [("GRAND CHAMPION", 75000000, "SSR"), ("HIGH SCORE #1", 50000000, "XAQ"), ("HIGH SCORE #2", 40000000, "GGF"),
            ("HIGH SCORE #3", 30000000, "JMR"), ("HIGH SCORE #4", 20000000, "T")]
# alphabet A-Z, then the ROM's control entries: SPACE (always), BACKSPACE (only once a letter is typed), END (always)
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
CONTROLS = ("SPC", "BKSP", "END")
# mode champion tables (data/hstd_defaults.csv entries 6-18; default scores are adjustments 134-145): key -> (label, initials, score)
CHAMPIONS = {
    "targaryen": ("TARGARYEN CHAMPION", "MXV", 10000000), "stark": ("STARK CHAMPION", "NED", 17500000),
    "baratheon": ("BARATHEON CHAMPION", "ROB", 17500000), "lannister": ("LANNISTER CHAMPION", "TYR", 17500000),
    "greyjoy": ("GREYJOY CHAMPION", "THN", 17500000), "tyrell": ("TYRELL CHAMPION", "MCE", 17500000),
    "martell": ("MARTELL CHAMPION", "OBR", 17500000), "winter_is_coming": ("WINTER IS COMING CHAMPION", "SNO", 1500000),
    "winter_has_come": ("WINTER HAS COME CHAMPION", "WHC", 7500000), "hand_of_the_king": ("HAND OF THE KING CHAMPION", "JON", 25000000),
    "iron_throne": ("IRON THRONE CHAMPION", "KNG", 25000000), "midnight_madness": ("MIDNIGHT MADNESS CHAMPION", "ZZZ", 25000000)}
ENTRY_FIRST_S = 30           # entry timer: 30 s, reloaded to 15 s at every input (docs/22 2c)
ENTRY_STEP_S = 15
COINS = ("s_left_coin", "s_center_coin", "s_right_coin", "s_fourth_coin", "s_fifth_coin")
PAGE_S = 4


def fmt(n):
    return "{:,}".format(int(n))


class Scoreboard(Mode):
    def mode_start(self, **kwargs):
        self._page = 0
        self._entry = None
        self._last = []
        self._variants()
        for sw in COINS:
            self.add_mode_event_handler(sw + "_active", self._coin)
        self.add_mode_event_handler("request_to_start_game", self._allow_start)
        self.add_mode_event_handler("player_add_request", self._allow_start)
        self.add_mode_event_handler("player_added", self._paid)
        self.add_mode_event_handler("mode_attract_started", self._attract_start)
        self.add_mode_event_handler("mode_attract_stopped", self._attract_stop)
        self.add_mode_event_handler("game_ending", self._game_ending)
        self.add_mode_event_handler("got_service_open", self._attract_stop)
        self.add_mode_event_handler("got_service_close", self._service_closed)
        self.add_mode_event_handler("got_debug_initials", self._debug_entry)          # smoke_initials.yaml only
        self.add_mode_event_handler("s_l_flipper_button_active", self._letter, step=-1)
        self.add_mode_event_handler("s_r_flipper_button_active", self._letter, step=1)
        self.add_mode_event_handler("s_start_button_active", self._confirm_letter)
        if self.machine.modes["attract"].active:
            self._attract_start()

    def _variants(self):
        """An effect with several sounds (config/rom/sound_variants.json) plays one at random, never the same twice in a row."""
        path = os.path.join(self.machine.machine_path, "config", "rom", "sound_variants.json")
        if not os.path.exists(path):
            return
        with open(path, encoding="utf-8") as f:
            variants = json.load(f)
        self._last_variant = {}
        for ev, names in variants.items():
            self.add_mode_event_handler(ev, self._pick, ev=ev, names=names)

    def _pick(self, ev, names, **kwargs):
        choices = [n for n in names if n != self._last_variant.get(ev)] or names
        self._last_variant[ev] = random.choice(choices)
        self.machine.events.post(self._last_variant[ev])

    # --- credits
    def _setting(self, name, default):
        s = self.machine.settings
        return int(s.get_setting_value(name)) if name in s._settings else default

    def credits(self):
        return int(self.machine.variables.get_machine_var("credits") or 0)

    def free_play(self):
        return self._setting("ad_free_play", 0) == 1

    def _coin(self, **kwargs):
        limit = self._setting("ad_credit_limit", 30)
        if self.credits() < limit:
            self.machine.variables.set_machine_var("credits", self.credits() + 1)
        self.machine.events.post("got_credits", credits=self.credits())

    def _allow_start(self, **kwargs):
        if self.free_play() or self.credits() > 0:
            return True
        self.machine.events.post("got_sound_start_button_no_credits")
        self.machine.events.post("got_no_credits")
        return False

    def _paid(self, **kwargs):
        if not self.free_play() and self.credits() > 0:
            self.machine.variables.set_machine_var("credits", self.credits() - 1)

    def credit_line(self):
        if self.free_play():
            return "FREE PLAY"
        return "CREDITS %d" % self.credits()

    # --- high scores (machine variable, persisted)
    def table(self):
        raw = self.machine.variables.get_machine_var("got_highscores")
        try:
            t = json.loads(raw) if raw else None
        except ValueError:
            t = None
        if not t:
            t = [{"label": l, "name": n, "score": s} for l, s, n in DEFAULTS]
        return t

    def _save(self, t):
        self.machine.variables.set_machine_var("got_highscores", json.dumps(t))

    def champions(self):
        raw = self.machine.variables.get_machine_var("got_champions")
        try:
            saved = json.loads(raw) if raw else {}
        except ValueError:
            saved = {}
        return {k: saved.get(k) or {"name": v[1], "score": v[2]} for k, v in CHAMPIONS.items()}

    def _champion_entries(self, game):
        """(player number, best mode score, key) for every mode champion a player beat (docs/22 2b: one table per mode)."""
        champs = self.champions()
        out = []
        for key in CHAMPIONS:
            best = max(((int(getattr(pl, "got_best_" + key, 0) or 0), pl.number) for pl in game.player_list), default=(0, 0))
            if best[0] > champs[key]["score"]:
                out.append((best[1], best[0], key))
        return out

    def _qualifies(self, score):
        return score > self.table()[-1]["score"]

    def _insert(self, name, score):
        t = self.table()
        rows = sorted([(r["score"], r["name"]) for r in t] + [(score, name)], reverse=True)[:len(t)]
        self._save([{"label": t[i]["label"], "name": n, "score": s} for i, (s, n) in enumerate(rows)])

    # --- attract pages
    def pages(self):
        t = self.table()
        out = [("GAME OF THRONES", "INSERT COIN" if not (self.free_play() or self.credits()) else "PRESS START", self.credit_line())]
        if self._last:
            out.append(("LAST GAME", "  ".join("P%d %s" % (i + 1, fmt(s)) for i, s in enumerate(self._last[:2])),
                        "  ".join("P%d %s" % (i + 3, fmt(s)) for i, s in enumerate(self._last[2:4]))))
        for r in t:
            out.append((r["label"], r["name"], fmt(r["score"])))
        champs = self.champions()
        for key, (label, _ini, _sc) in CHAMPIONS.items():                # champion pages of the attract loop (docs/22 2d)
            out.append((label, champs[key]["name"], fmt(champs[key]["score"])))
        return out

    def _attract_start(self, **kwargs):
        self._page = 0
        self._show_page()

    def _service_closed(self, **kwargs):
        if self.machine.modes["attract"].active:
            self._attract_start()

    def _attract_stop(self, **kwargs):
        self.delay.remove("page")
        self.screen_clear()

    def screen(self, l1, l2, l3):
        """Show three lines: GMC keeps a slide of the same name when it is played again, so two copies alternate."""
        self._flip = not getattr(self, "_flip", False)
        self.machine.events.post("got_screen_" + ("a" if self._flip else "b"), line1=l1, line2=l2, line3=l3)

    def screen_clear(self):
        self.machine.events.post("got_screen_clear")

    def _show_page(self):
        pages = self.pages()
        l1, l2, l3 = pages[self._page % len(pages)]
        self.machine.events.post("got_attract_page", line1=l1, line2=l2, line3=l3)
        self.screen(l1, l2, l3)
        self._page += 1
        self.delay.reset(PAGE_S * 1000, self._show_page, name="page")

    # --- game end: initials, match, game over
    def _game_ending(self, queue=None, **kwargs):
        game = self.machine.game
        scores = [p.score for p in game.player_list] if game else []
        self._last = scores
        self._queue = queue
        if queue:
            queue.wait()
        self._todo = [(i + 1, s, None) for i, s in enumerate(scores) if self._qualifies(s)]
        if game:
            self._todo += self._champion_entries(game)
        self._next_entry()

    def _debug_entry(self, **kwargs):
        self._todo = [(1, 80000000, None)]
        self._next_entry()

    def _next_entry(self):
        if not self._todo:
            return self._match()
        num, score, key = self._todo.pop(0)
        self._entry = {"num": num, "score": score, "key": key, "name": "", "pos": 0, "touched": False}
        self.delay.reset(ENTRY_FIRST_S * 1000, self._entry_timeout, name="entry")
        self.machine.events.post("got_se_tune_hstd")                  # effect 67 tune_hstd
        self.machine.events.post("got_se_vo_hstd_anouncement_v1")     # voice 430
        self._entry_show()

    def _alphabet(self):
        e = self._entry
        return list(LETTERS) + [c for c in CONTROLS if c != "BKSP" or e["name"]]

    def _touch(self):
        self._entry["touched"] = True
        self.delay.reset(ENTRY_STEP_S * 1000, self._entry_timeout, name="entry")

    def _letter(self, step, **kwargs):
        e = self._entry
        if not e:
            return
        self._touch()
        e["pos"] = (e["pos"] + step) % len(self._alphabet())
        self.machine.events.post("got_se_fx_hstd_cursor_right" if step > 0 else "got_se_fx_hstd_cursor_left")
        self._entry_show()

    def _confirm_letter(self, **kwargs):
        e = self._entry
        if not e:
            return
        self._touch()
        item = self._alphabet()[e["pos"]]
        self.machine.events.post("got_se_fx_hstd_enter")
        if item == "END":
            return self._entry_done()
        if item == "BKSP":
            e["name"] = e["name"][:-1]
        else:
            e["name"] += " " if item == "SPC" else item
        e["pos"] = 0
        if len(e["name"]) >= 3:
            return self._entry_done()
        self._entry_show()

    def _entry_show(self):
        e = self._entry
        rank = [r["score"] for r in self.table()]
        idx = next((i for i, v in enumerate(rank) if e["score"] > v), len(rank) - 1)
        title = CHAMPIONS[e["key"]][0] if e.get("key") else self.table()[idx]["label"]
        self._flip = not getattr(self, "_flip", False)
        self.machine.events.post("got_initials_" + ("a" if self._flip else "b"), num=e["num"], title=title,
                                 initials=e["name"], alpha=",".join(self._alphabet()), pos=e["pos"], maxlen=3)

    def _entry_timeout(self):
        e = self._entry
        if e:
            if not e["name"].strip():                 # nothing typed: the entry's default initials (docs/22)
                rank = [r["score"] for r in self.table()]
                idx = next((i for i, v in enumerate(rank) if e["score"] > v), len(rank) - 1)
                e["name"] = CHAMPIONS[e["key"]][1] if e.get("key") else DEFAULTS[min(idx, len(DEFAULTS) - 1)][2]
            self._entry_done()

    def _entry_done(self):
        e, self._entry = self._entry, None
        self.delay.remove("entry")
        if e.get("key"):
            champs = self.champions()
            champs[e["key"]] = {"name": e["name"], "score": e["score"]}
            self.machine.variables.set_machine_var("got_champions", json.dumps(champs))
        else:
            self._insert(e["name"], e["score"])
        self.machine.events.post("got_initials_done")
        self.screen_clear()
        self._next_entry()

    def _match(self):
        pct = self._setting("ad_match_percentage", 9)
        digit = random.choice(range(0, 100, 10))
        lines = ("MATCH", "%02d" % digit, "")
        won = False
        if pct and self._last:
            for s in self._last:
                if (s // 10) % 10 * 10 == digit and random.random() * 100 < pct * 10:      # CFG: odds from the percentage
                    won = True
        if won:
            self.machine.variables.set_machine_var("credits", self.credits() + 1)
            lines = ("MATCH", "%02d" % digit, "FREE GAME")
        self.machine.events.post("got_match", line1=lines[0], line2=lines[1], line3=lines[2], won=won)
        self.screen(*lines)
        self.delay.reset(3000, self._game_over, name="match")

    def _game_over(self):
        self.machine.events.post("got_game_over", line1="GAME OVER", line2=self.credit_line(), line3="")
        self.screen("GAME OVER", self.credit_line(), "")
        self.delay.reset(3000, self._release, name="over")

    def _release(self):
        self.machine.events.post("got_match_end")
        self.screen_clear()
        if self._queue:
            self._queue.clear()
            self._queue = None
