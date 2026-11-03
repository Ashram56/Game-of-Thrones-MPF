extends TextureRect
## Draws the text of the sibling Labels (filled by MPF's token updaters) with the ROM bitmap fonts instead of a system font.
## Rows: one label = vertically centred, two = y 14/28, three = y 10/20/30 (font 6, 7 px high; centred on x 64).

const COLOR := Color(1.0, 0.51, 0.0)
const FONT := 6
var _font := {}
var _last := ""

func _ready() -> void:
	var path := ProjectSettings.globalize_path("res://images/fonts/font%02d.json" % FONT)
	if FileAccess.file_exists(path):
		_font = JSON.parse_string(FileAccess.get_file_as_string(path))
	for n in get_parent().get_children():
		if n is Label:
			n.visible = false

func _process(_delta: float) -> void:
	if _font.is_empty():
		return
	var labels: Array = []
	for n in get_parent().get_children():
		if n is Label:
			labels.append(n)
	var texts: Array = []
	for l in labels:
		texts.append(String(l.text))
	var key := "|".join(texts)
	if key == _last:
		return
	_last = key
	var rows: Array
	match texts.size():
		1: rows = [20]
		2: rows = [14, 28]
		_: rows = [10, 20, 30]
	var img := Image.create(128, 32, false, Image.FORMAT_RGBA8)
	var gl: Dictionary = _font["glyphs"]
	for k in texts.size():
		var text: String = texts[k]
		if text == "":
			continue
		var glyphs: Array = []
		var width := 0
		for c in text:
			var gkey: String = "x20" if c == " " else c
			var g = gl.get(gkey, gl.get(gkey.to_upper(), gl.get("x20")))
			glyphs.append(g)
			width += int(g.get("advance", int(g["w"]) + 1))
		width -= int(_font.get("spacing", 1))
		var ox: int = clampi(64 - width / 2, 0, maxi(0, 128 - width))
		var oy: int = rows[k] - int(_font["height_px"]) + 1
		for g in glyphs:
			var grows: Array = g["rows"]
			for j in grows.size():
				var row: String = grows[j]
				for i in row.length():
					var v := row.substr(i, 1).hex_to_int()
					var gx := ox + int(g.get("dx", 0)) + i
					var gy := oy + int(g.get("dy", 0)) + j
					if v > 0 and gx >= 0 and gx < 128 and gy >= 0 and gy < 32:
						var kk := v / 15.0
						img.set_pixel(gx, gy, Color(COLOR.r * kk, COLOR.g * kk, COLOR.b * kk, 1.0))
			ox += int(g.get("advance", int(g["w"]) + 1))
	texture = ImageTexture.create_from_image(img)
