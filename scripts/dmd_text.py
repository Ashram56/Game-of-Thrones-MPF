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


def rom_lines(data):
    """{effect name: [page, ...]} with page = [(text, font, x, y)], for every def with at least one fully known line."""
    out = {}
    with open(os.path.join(data, "font_usage.csv"), encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["font_kind"] != "font_index" or not r["text_en"] or not r["font"] or not r["x"] or not r["y"]:
                continue
            name = r["function"] if r["function"].startswith("def_") else None
            if not name:
                continue
            text = _clean(r["text_en"])
            if not text:
                continue
            item = (text, int(r["font"]), int(r["x"]), int(r["y"]))
            pages = out.setdefault(name, [[]])
            if item in [i for pg in pages for i in pg]:
                continue
            if pages[-1] and item[3] <= pages[-1][-1][3]:     # the y goes back up: the next screen of the same effect
                pages.append([])
            pages[-1].append(item)
    return out


_fonts = {}


def _font(data, n):
    if n not in _fonts:
        with open(os.path.join(data, "fonts", "font%02d.json" % n), encoding="utf-8") as f:
            _fonts[n] = json.load(f)
    return _fonts[n]


def render(data, lines, path):
    from PIL import Image
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = img.load()
    for text, fnum, x, y in lines:
        font = _font(data, fnum)
        gl = font["glyphs"]
        glyphs = [gl.get("x20" if c == " " else c) or gl.get(c.upper()) or gl.get("x20") for c in text]
        width = sum(g["w"] + 1 for g in glyphs) - 1
        height = font["height_px"]
        ox, oy = x - width // 2, y - height + 1
        for g in glyphs:
            for j, row in enumerate(g["rows"]):
                for i, ch in enumerate(row):
                    v = int(ch, 16)
                    gx, gy = ox + i, oy + j
                    if v and 0 <= gx < W and 0 <= gy < H:
                        k = v / 15.0
                        px[gx, gy] = (int(COLOR[0] * k), int(COLOR[1] * k), int(COLOR[2] * k), 255)
            ox += g["w"] + 1
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
