"""Pict-O-Pops awards (Game-of-Thrones docs/09, H logic, M tape order): three reels over a strip rebuilt on every pop hit.
The ROM walks a fixed tape of 112 ids; only the per-id counts are in data/pop_awards.csv, so the tape order here is a fixed
interleaving of those counts (M)."""
import json
import os

TAPE_JSON = os.path.join(os.path.dirname(__file__), "..", "config", "rom", "pop_awards.json")
NONE = 18                                    # "no award yet" index at game start


def build_tape(entries):
    """Deterministic 112-entry tape with each id repeated `tape` times, spread as evenly as possible."""
    slots = []
    for e in entries:
        n = e["tape"]
        slots += [((i + 0.5) / n, e["id"]) for i in range(n)]
    slots.sort()
    return [i for _, i in slots]


def load_tape(path=TAPE_JSON):
    with open(path, encoding="utf-8") as f:
        entries = json.load(f)
    # the Lannister Gold id 12 is a variant of Gold; both are on the tape
    return build_tape(entries), {e["id"]: e["award"] for e in entries}


class Reels:
    """Reel pointers into the live strip. step(hit) returns the awarded id or None."""

    def __init__(self, tape):
        self.tape = tape
        self.idx = {30: 0, 32: 0, 31: 0}          # left, bottom, right reel
        self.last = NONE
        self.strip = []

    def rebuild(self, go):
        strip = []
        for i in self.tape:
            if go(i) and (not strip or strip[-1] != i):
                strip.append(i)
        self.strip = strip
        for k in self.idx:
            self.idx[k] %= max(1, len(strip))

    def _sym(self, reel):
        return self.strip[self.idx[reel] % len(self.strip)] if self.strip else None

    def hit(self, reel, go):
        """A pop hit: rebuild the strip, move the hit reel one step, award on a match (a pair completes itself)."""
        self.rebuild(go)
        if not self.strip:
            return None
        win = self._match()
        if win is None:
            two = self._pair()
            if two is not None:
                sym, other = two
                n = 0
                while self._sym(other) != sym and n < len(self.strip):
                    self.idx[other] = (self.idx[other] + 1) % len(self.strip)
                    n += 1
                win = sym if self._sym(other) == sym else None
        if win is None:
            self.idx[reel] = (self.idx[reel] + 1) % len(self.strip)
            win = self._match()
        if win is not None:
            self.last = win
            self._randomize()
        return win

    def _match(self):
        a, b, c = (self._sym(r) for r in (30, 32, 31))
        return a if a is not None and a == b == c else None

    def _pair(self):
        r = (30, 32, 31)
        for i in range(3):
            for j in range(i + 1, 3):
                if self._sym(r[i]) == self._sym(r[j]):
                    return self._sym(r[i]), r[3 - i - j]
        return None

    def _randomize(self):
        n = len(self.strip)
        third = max(1, n // 3)
        self.idx = {30: 0, 32: third % n, 31: (2 * third) % n}
