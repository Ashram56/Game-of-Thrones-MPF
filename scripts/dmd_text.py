"""ROM text on the DMD: the message lines of a display effect (data/font_usage.csv: text, font index, x, y) drawn with the ROM's
own bitmap fonts (data/fonts/fontNN.json) into a 128x32 PNG. x is the centre of the line, y the bottom row of the line."""
import csv
import json
import os
import re

W, H = 128, 32
COLOR = (255, 130, 0)


def _clean(t):
    t = re.sub(r"%[,0-9]*l*[du]", "0", t)
    t = re.sub(r"%P\d//(.*?)/%", r"\1", t)
    return t.replace("%s", "").strip()


def _arg_kinds(data):
    """{(def, text): 'score' | 'award'}: the 64-bit points arguments of dmd_text_args.csv (score when the table says current_player.score,
    otherwise the award just given, taken at run time as the last score increase, inferred)."""
    path = os.path.join(data, "dmd_text_args.csv")
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if "llu" not in r["format"]:
                if r["format"] == "%d" and "timer" in (r["mpf_hint"] + " " + r["meaning"]).lower() and "remaining" in (r["mpf_hint"] + " " + r["meaning"]).lower():
                    out.setdefault((r["def_name"], r["text"]), "timer")
                elif r["format"] == "%d":
                    m = r["meaning"].lower()
                    src = r["source_name_or_address"]
                    kind = ("tickle" if "tickles/shots still needed" in m else
                            "price" if "gold price of the next lannister" in m and "BUY" in r["text"] else
                            "gold" if "gold price of the next lannister" in m and "GOLD TOTAL" in r["text"] else
                            "wildfire" if "house ability bits/value" in m and "GetWildFire" in src else None) or ("award" if any(k in m for k in ("jackpot value", "hurry-up value", "points awarded")) else
                            "shots" if m == "shots still needed to complete the mode" else "player" if m == "player number" else "ball" if m == "ball number" else None)
                    if kind:
                        out.setdefault((r["def_name"], r["text"]), kind)
                continue
            kind = "score" if "player.score" in r["mpf_hint"] or "score" in r["meaning"].lower() else "award"
            out.setdefault((r["def_name"], r["text"]), kind)
    return out


def rom_lines(data):
    """{effect name: [page, ...]} with page = [(text, font, x, y)], for every def with at least one fully known line."""
    out = {}
    kinds = _arg_kinds(data)
    with open(os.path.join(data, "font_usage.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            name = r["function"] if r["function"].startswith("def_") else None
            if r["font_kind"] != "font_index" or not r["text_en"] or not r["font"] or not r["x"] or not r["y"]:
                continue
            if not name:
                continue
            raw = r["text_en"]
            kind = kinds.get((name, raw))
            if kind in ("timer", "player", "ball", "shots", "tickle", "price", "gold", "wildfire") or (kind == "award" and not re.search(r"%[,0-9]*l+u", raw)):
                raw = re.sub(r"%[,0-9]*d", "{%s}" % kind, raw, count=1)
            elif kind and re.search(r"%[,0-9]*l+u", raw):
                raw = re.sub(r"%[,0-9]*l+u", "{%s}" % kind, raw, count=1)
            text = _clean(raw.replace("{score}", "\x01").replace("{award}", "\x02").replace("{timer}", "\x03").replace("{player}", "\x04").replace("{ball}", "\x05").replace("{shots}", "\x06").replace("{tickle}", "\x07").replace("{price}", "\x08").replace("{gold}", "\x09").replace("{wildfire}", "\x0b")).replace("\x01", "{score}").replace("\x02", "{award}").replace("\x03", "{timer}").replace("\x04", "{player}").replace("\x05", "{ball}").replace("\x06", "{shots}").replace("\x07", "{tickle}").replace("\x08", "{price}").replace("\x09", "{gold}").replace("\x0b", "{wildfire}")
            if not text:
                continue
            item = (text, int(r["font"]), int(r["x"]), int(r["y"]))
            pages = out.setdefault(name, [[]])
            if item in [i for pg in pages for i in pg]:
                continue
            if pages[-1] and item[3] <= pages[-1][-1][3]:     # the y goes back up: the next screen of the same effect
                pages.append([])
            pages[-1].append(item)
    # docs/20 section 7 (static): ball search text, font 12 centred, y 13 / 25 (the table row has no font)
    out["def_ball_search"] = [[("LOCATING PINBALLS", 12, 64, 13), ("PLEASE WAIT...", 12, 64, 25)]]
    return out


_fonts = {}


def _font(data, n):
    if n not in _fonts:
        with open(os.path.join(data, "fonts", "font%02d.json" % n), encoding="utf-8") as f:
            _fonts[n] = json.load(f)
    return _fonts[n]


def is_live(pages):
    return any("{" in t for page in pages for t, *_rest in page)


def render(data, lines, path):
    from PIL import Image
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    for ln in lines:
        text, fnum, x, y = ln[:4]
        align = ln[4] if len(ln) > 4 else "c"
        font = _font(data, fnum)
        gl = font["glyphs"]
        glyphs = [gl.get("x20" if c == " " else c) or gl.get(c.upper()) or gl.get("x20") for c in text]
        spacing = font.get("spacing", 1)
        adv = [g.get("advance", g["w"] + 1) for g in glyphs]
        width = sum(adv) - spacing                           # docs/21: the last glyph's trailing spacing is not counted
        height = font["height_px"]
        ox = x - (width if align == "r" else 0 if align == "l" else width // 2)
        ox, oy = max(0, min(ox, W - width)), y - height + 1      # centre anchor; kept whole on screen
        for g, a in zip(glyphs, adv):
            for j, row in enumerate(g["rows"]):
                for i, ch in enumerate(row):
                    v = int(ch, 16)
                    gx, gy = ox + g.get("dx", 0) + i, oy + g.get("dy", 0) + j
                    if v and 0 <= gx < W and 0 <= gy < H:
                        k = v / 15.0
                        px[gx, gy] = (int(COLOR[0] * k), int(COLOR[1] * k), int(COLOR[2] * k), 255)
            ox += a
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
