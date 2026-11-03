extends TextureRect
## ROM high-score initials entry screen (docs/22 2c): title "PLAYER n - ENTER INITIALS" y=4, the entry title y=10, the typed initials y=21
## in font 14 on 7 px cells, the alphabet strip y=30 in font 0 with a box round the cursor. Values come from the sibling Labels
## (event args num, title, name, alpha, pos, maxlen), filled by MPF's token updaters.

const COLOR := Color(1.0, 0.51, 0.0)
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

func _ready() -> void:
	for n in get_parent().get_children():
		if n is Label:
			n.visible = false

func _val(key: String) -> String:
	var n = get_parent().get_node_or_null(key)
	return "" if n == null else String(n.text)

func _glyph(font: Dictionary, c: String):
	var gl: Dictionary = font["glyphs"]
	var key: String = "x20" if c == " " else c
	return gl.get(key, gl.get(key.to_upper(), gl.get("x20")))

func _width(font: Dictionary, text: String) -> int:
	var w := 0
	for c in text:
		w += int(_glyph(font, c).get("advance", int(_glyph(font, c)["w"]) + 1))
	return w - int(font.get("spacing", 1))

func _text(img: Image, font: Dictionary, text: String, x: int, bottom: int, dim := 1.0) -> int:
	var oy: int = bottom - int(font["height_px"]) + 1
	for c in text:
		var g = _glyph(font, c)
		var rows: Array = g["rows"]
		for j in rows.size():
			var row: String = rows[j]
			for i in row.length():
				var v := row.substr(i, 1).hex_to_int()
				var gx: int = x + int(g.get("dx", 0)) + i
				var gy: int = oy + int(g.get("dy", 0)) + j
				if v > 0 and gx >= 0 and gx < 128 and gy >= 0 and gy < 32:
					var k := v / 15.0 * dim
					img.set_pixel(gx, gy, Color(COLOR.r * k, COLOR.g * k, COLOR.b * k, 1.0))
		x += int(g.get("advance", int(g["w"]) + 1))
	return x

func _process(_delta: float) -> void:
	var key := "|".join([_val("Num"), _val("Title"), _val("Name"), _val("Alpha"), _val("Pos"), _val("MaxLen")])
	if key == _last:
		return
	_last = key
	var f0 := _font(0)
	var f14 := _font(14)
	if f0.is_empty() or f14.is_empty():
		return
	var img := Image.create(128, 32, false, Image.FORMAT_RGBA8)
	var head := "PLAYER %s - ENTER INITIALS" % _val("Num")
	_text(img, f0, head, clampi(64 - _width(f0, head) / 2, 0, 127), 4)
	var title := _val("Title")
	if title != "":
		_text(img, f0, title, clampi(64 - _width(f0, title) / 2, 0, 127), 10)
	var maxlen := maxi(1, int(_val("MaxLen")))
	var name := _val("Name")
	var x0 := (129 - 7 * maxlen) / 2
	for k in maxlen:
		var ch := "_" if k >= name.length() else name.substr(k, 1)
		_text(img, f14, ch, x0 + k * 7, 21)
	var items := _val("Alpha").split(",")
	var pos := clampi(int(_val("Pos")), 0, maxi(0, items.size() - 1))
	var widths: Array = []
	var total := 0
	for it in items:
		widths.append(_width(f0, it) + 2)
		total += int(widths[-1])
	var start := 0
	for k in pos:
		start += int(widths[k])
	var x := 64 - start - int(widths[pos]) / 2
	for k in items.size():
		var w: int = widths[k]
		if x + w > 0 and x < 128:
			_text(img, f0, items[k], x + 1, 30, 1.0 if k == pos else 0.55)
			if k == pos:
				for gx in range(maxi(0, x), mini(127, x + w - 1) + 1):
					img.set_pixel(gx, 25, COLOR)
					img.set_pixel(gx, 31, COLOR)
				for gy in range(25, 32):
					if x >= 0 and x < 128:
						img.set_pixel(x, gy, COLOR)
					if x + w - 1 >= 0 and x + w - 1 < 128:
						img.set_pixel(x + w - 1, gy, COLOR)
		x += w
	texture = ImageTexture.create_from_image(img)
