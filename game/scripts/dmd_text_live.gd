extends TextureRect
## ROM text screens whose lines carry run-time values ({score}, {award}, {timer}). The pages are JSON [[text, font, x, y], ...] and are drawn
## with the ROM's bitmap fonts (res://images/fonts/fontNN.json, copied by scripts/gen_media.py) when the slide appears. The values
## are the machine variables got_arg_score / got_arg_award, set by got.defargs just before the effect.

@export var pages_json: String = "[]"
@export var period := 1.2
@export var page_var := ""        ## machine variable whose value (1-based) selects the page; the page is redrawn every `refresh` seconds
@export var refresh := 0.0
var _pages: Array = []
var _r := 0.0

const COLOR := Color(1.0, 0.51, 0.0)
var _tex: Array = []
var _fonts := {}
var _i := 0
var _t := 0.0

func _font(n: int) -> Dictionary:
	if not _fonts.has(n):
		var path := ProjectSettings.globalize_path("res://images/fonts/font%02d.json" % n)
		var d = {}
		if FileAccess.file_exists(path):
			d = JSON.parse_string(FileAccess.get_file_as_string(path))
		_fonts[n] = d
	return _fonts[n]

func _value(key: String) -> String:
	var v = MPF.game.machine_vars.get("got_arg_" + key)
	return "0" if v == null else str(v)

func _draw_page(page: Array) -> ImageTexture:
	var img := Image.create(128, 32, false, Image.FORMAT_RGBA8)
	for line in page:
		var text: String = str(line[0]).replace("{score}", _value("score")).replace("{award}", _value("award")).replace("{timer}", _value("timer")).replace("{player}", _value("player")).replace("{ball}", _value("ball")).replace("{shots}", _value("shots")).replace("{tickle}", _value("tickle")).replace("{price}", _value("price")).replace("{gold}", _value("gold")).replace("{wildfire}", _value("wildfire")).replace("{hurry}", _value("hurry")).replace("{sets}", _value("sets"))
		var font := _font(int(line[1]))
		if font.is_empty():
			continue
		var gl: Dictionary = font["glyphs"]
		var glyphs: Array = []
		var width := 0
		for c in text:
			var key: String = "x20" if c == " " else c
			var g = gl.get(key, gl.get(key.to_upper(), gl.get("x20")))
			glyphs.append(g)
			width += int(g.get("advance", int(g["w"]) + 1))
		width -= int(font.get("spacing", 1))
		var al: String = str(line[4]) if line.size() > 4 else "c"      # ROM align: "l" x is the left edge, "r" the right edge, "c" the centre
		var ax: int = int(line[2]) - (width if al == "r" else 0 if al == "l" else width / 2)
		var ox: int = clampi(ax, 0, maxi(0, 128 - width))               # never clipped at the left/right edge
		var oy: int = int(line[3]) - int(font["height_px"]) + 1
		var dim := 1.0
		if line.size() > 5 and str(line[5]) == "b":      # 8-frame blink of 6 ticks: the colour transform in frames 0-3, plain in 4-7 (docs/25 s7; dimmed, M)
			dim = 0.45 if (int(Time.get_ticks_msec() / 96.8) % 8) < 4 else 1.0
		for g in glyphs:
			var rows: Array = g["rows"]
			for j in rows.size():
				var row: String = rows[j]
				for i in row.length():
					var v := row.substr(i, 1).hex_to_int()
					var gx := ox + int(g.get("dx", 0)) + i
					var gy := oy + int(g.get("dy", 0)) + j
					if v > 0 and gx >= 0 and gx < 128 and gy >= 0 and gy < 32:
						var k := v / 15.0 * dim
						img.set_pixel(gx, gy, Color(COLOR.r * k, COLOR.g * k, COLOR.b * k, 1.0))
			ox += int(g.get("advance", int(g["w"]) + 1))
	return ImageTexture.create_from_image(img)

func _ready() -> void:
	var pages = JSON.parse_string(pages_json)
	if page_var != "" and pages is Array:
		_pages = pages
		_show_var_page()
		return
	if pages is Array:
		for p in pages:
			_tex.append(_draw_page(p))
	if _tex.size() > 0:
		texture = _tex[0]

func _show_var_page() -> void:
	var v = MPF.game.machine_vars.get(page_var)
	var idx := clampi(int(str(v if v != null else "1")) - 1, 0, maxi(0, _pages.size() - 1))
	texture = _draw_page(_pages[idx])

func _process(delta: float) -> void:
	if page_var != "":
		_r += delta
		if _r >= refresh:
			_r = 0.0
			_show_var_page()
		return
	if _tex.size() < 2:
		return
	_t += delta
	if _t >= period:
		_t = 0.0
		_i = (_i + 1) % _tex.size()
		texture = _tex[_i]
