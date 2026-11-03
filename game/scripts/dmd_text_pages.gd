extends TextureRect
## ROM text screens of one display effect: PNGs (128x32, drawn from the ROM bitmap fonts by scripts/gen_media.py), shown one after the
## other every `period` seconds, nearest-neighbour scaled. Loaded straight from disk, no import step.

@export var pages: PackedStringArray = []
@export var period := 1.2

var _tex: Array = []
var _i := 0
var _t := 0.0

func _ready() -> void:
	for p in pages:
		var path := ProjectSettings.globalize_path(p)
		if FileAccess.file_exists(path):
			_tex.append(ImageTexture.create_from_image(Image.load_from_file(path)))
	if _tex.size() > 0:
		texture = _tex[0]

func _process(delta: float) -> void:
	if _tex.size() < 2:
		return
	_t += delta
	if _t >= period:
		_t = 0.0
		_i = (_i + 1) % _tex.size()
		texture = _tex[_i]
