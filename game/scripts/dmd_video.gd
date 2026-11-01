extends MPFSlide
## Plays a ROM DMD video: frames res://images/<video>_fNNN.png (128x32, copied by scripts/gen_media.py) at `fps`,
## nearest-neighbour scaled to the slide. Holds the last frame (the ROM never clears the DMD itself).

@export var video: String = ""
@export var fps: int = 20

var _tex: TextureRect
var _frames: Array = []
var _t := 0.0

func _ready() -> void:
	var bg := ColorRect.new()
	bg.color = Color.BLACK
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	_tex = TextureRect.new()
	_tex.set_anchors_preset(Control.PRESET_FULL_RECT)
	_tex.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_tex.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	_tex.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(_tex)
	var k := 0
	while FileAccess.file_exists("res://images/dmd_%s_f%03d.png" % [video, k]):
		var img := Image.load_from_file(ProjectSettings.globalize_path("res://images/dmd_%s_f%03d.png" % [video, k]))
		_frames.append(ImageTexture.create_from_image(img))
		k += 1
	if _frames.size() > 0:
		_tex.texture = _frames[0]

func _process(delta: float) -> void:
	if _frames.size() < 2:
		return
	_t += delta
	var idx: int = min(int(_t * fps), _frames.size() - 1)
	_tex.texture = _frames[idx]
