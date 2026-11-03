"""Credits, attract pages, high scores with initials, match and game over (always-on mode).

Rules from data/adjustments.csv (credit limit 65, free play 66, match percentage 61) and docs/03 section 5 (grand champion
75 M, #1-#4 50/40/30/20 M). CFG, the ROM's screens are not decoded for Spike 1: the pages, the initials entry (flippers
change the letter, Start confirms) and the match draw (a random tens digit, award = one credit) are mine; default initials GOT.
"""
import json
import random

from mpf.core.mode import Mode

DEFAULTS = [("GRAND CHAMPION", 75000000), ("HIGH SCORE #1", 50000000), ("HIGH SCORE #2", 40000000),
            ("HIGH SCORE #3", 30000000), ("HIGH SCORE #4", 20000000)]
LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .-"
COINS = ("s_left_coin", "s_center_coin", "s_right_coin", "s_fourth_coin", "s_fifth_coin")
PAGE_S = 4


def fmt(n):
    return "{:,}".format(int(n))


class Scoreboard(Mode):
    def mode_start(self, **kwargs):
        self._page = 0
        self._entry = None
        self._last = []
        for sw in COINS:
            self.add_mode_event_handler(sw + "_active", self._coin)
        self.add_mode_event_handler("request_to_start_game", self._allow_start)
        self.add_mode_event_handler("player_add_request", self._allow_start)
        self.add_mode_event_handler("player_added", self._paid)
        self.add_mode_event_handler("mode_attract_started", self._attract_start)
        self.add_mode_event_handler("mode_attract_stopped", self._attract_stop)
        self.add_mode_event_handler("game_ending", self._game_ending)
        self.add_mode_event_handler("s_l_flipper_button_active", self._letter, step=-1)
        self.add_mode_event_handler("s_r_flipper_button_active", self._letter, step=1)
        self.add_mode_event_handler("s_start_button_active", self._confirm_letter)
        if self.machine.modes["attract"].active:
            self._attract_start()

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
            t = [{"label": l, "name": "GOT", "score": s} for l, s in DEFAULTS]
        return t

    def _save(self, t):
        self.machine.variables.set_machine_var("got_highscores", json.dumps(t))

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
        return out

    def _attract_start(self, **kwargs):
        self._page = 0
        self._show_page()

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
        self._todo = [(i + 1, s) for i, s in enumerate(scores) if self._qualifies(s)]
        self._next_entry()

    def _next_entry(self):
        if not self._todo:
            return self._match()
        num, score = self._todo.pop(0)
        self._entry = {"num": num, "score": score, "name": "", "pos": 0}
        self.delay.reset(20000, self._entry_timeout, name="entry")
        self._entry_show()

    def _letter(self, step, **kwargs):
        e = self._entry
        if not e:
            return
        e["pos"] = (e["pos"] + step) % len(LETTERS)
        self._entry_show()

    def _confirm_letter(self, **kwargs):
        e = self._entry
        if not e:
            return
        e["name"] += LETTERS[e["pos"]]
        e["pos"] = 0
        if len(e["name"]) >= 3:
            return self._entry_done()
        self.delay.reset(20000, self._entry_timeout, name="entry")
        self._entry_show()

    def _entry_show(self):
        e = self._entry
        rank = [r["score"] for r in self.table()]
        title = "GRAND CHAMPION" if e["score"] > rank[0] else "HIGH SCORE"
        shown = e["name"] + LETTERS[e["pos"]]
        l1, l2, l3 = "PLAYER %d %s" % (e["num"], title), shown.ljust(3, "_"), fmt(e["score"])
        self.machine.events.post("got_initials", line1=l1, line2=l2, line3=l3)
        self.screen(l1, l2, l3)

    def _entry_timeout(self):
        e = self._entry
        if e:
            e["name"] = (e["name"] + "GOT")[:3]
            self._entry_done()

    def _entry_done(self):
        e, self._entry = self._entry, None
        self.delay.remove("entry")
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
