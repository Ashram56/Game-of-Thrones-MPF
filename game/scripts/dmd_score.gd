extends TextureRect
## ROM-style score screen: the score in the largest ROM digit font (fonts 19-26) that fits 128 px, BALL n / PLAYER n in font 0 (ROM fonts,
## res://images/fonts/fontNN.json copied by scripts/gen_media.py). Redrawn when the current player's score, ball or number changes.

const COLOR := Color(1.0, 0.51, 0.0)
const DIGIT_FONTS := [26, 25, 24, 23, 22, 21, 20, 19]    # large to small (heights 18,20,18,18,12,12,7,7)
var _fonts := {}
var _last := ""

func _font(n: int) -> Dictionary:
	if not _fonts.has(n):
		var path := ProjectSettings.globalize_path("res://images/fonts/font%02d.json" % n)
		var d = {}
		if FileAccess.file_exists(path):
			d = JSON.parse_string(FileAccess.get_file_as_string(path))
		_fonts[n] = d
	return _fonts[n]

func _glyphs(font: Dictionary, text: String) -> Array:
	var gl: Dictionary = font["glyphs"]
	var out: Array = []
	for c in text:
		var key: String = "x20" if c == " " else c
		out.append(gl.get(key, gl.get(key.to_upper(), gl.get("x20"))))
	return out

func _width(glyphs: Array) -> int:
	var w := 0
	for g in glyphs:
		w += int(g["w"]) + 1
	return w - 1

func _put(img: Image, font: Dictionary, glyphs: Array, ox: int, bottom: int) -> void:
	var oy: int = bottom - int(font["height_px"]) + 1
	for g in glyphs:
		var rows: Array = g["rows"]
		for j in rows.size():
			var row: String = rows[j]
			for i in row.length():
				var v := row.substr(i, 1).hex_to_int()
				var gx := ox + i
				var gy := oy + j
				if v > 0 and gx >= 0 and gx < 128 and gy >= 0 and gy < 32:
					var k := v / 15.0
					img.set_pixel(gx, gy, Color(COLOR.r * k, COLOR.g * k, COLOR.b * k, 1.0))
		ox += int(g["w"]) + 1

func _commas(n: int) -> String:
	var s := str(n)
	var out := ""
	while s.length() > 3:
		out = "," + s.substr(s.length() - 3) + out
		s = s.substr(0, s.length() - 3)
	return s + out

func _process(_delta: float) -> void:
	var p: Dictionary = MPF.game.player
	var score := int(p.get("score", 0))
	var ball := int(p.get("ball", 1))
	var num := int(p.get("number", 1))
	var key := "%d/%d/%d" % [score, ball, num]
	if key == _last:
		return
	_last = key
	var img := Image.create(128, 32, false, Image.FORMAT_RGBA8)
	var text := _commas(score)
	for n in DIGIT_FONTS:
		var f := _font(n)
		if f.is_empty():
			continue
		var gs := _glyphs(f, text)
		if _width(gs) <= 126 or n == DIGIT_FONTS[-1]:
			_put(img, f, gs, 64 - _width(gs) / 2, 22)
			break
	var f0 := _font(0)
	if not f0.is_empty():
		_put(img, f0, _glyphs(f0, "BALL %d" % ball), 1, 31)
		var pg := _glyphs(f0, "PLAYER %d" % num)
		_put(img, f0, pg, 127 - _width(pg), 31)
	texture = ImageTexture.create_from_image(img)
