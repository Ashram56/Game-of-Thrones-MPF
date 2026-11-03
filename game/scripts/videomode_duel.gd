extends MPFSlide
## Video mode duel on the DMD (ROM cvideomode / cplayer / canimation, data/videomode_sprites.csv): the player's sprite at x=5, the AI's
## (images already mirrored) right-aligned at x=123 (inferred), the YOU / FOE labels and the two procedural health bars (3x32 border
## and fill at x=0 and x=124). Frames res://images/vm/<id>.png, 20 per second. The health values are the machine variables
## got_vm_me, got_vm_ai, got_vm_ai_max set by got.videomode; a drop starts the attack / hit / death animations.

const FPS := 20.0
const ONESHOT := ["attack", "strong_attack", "parry", "hit", "knockback_loop"]

var _sprites := {}
var _tex := {}
var _side := {"player": {"state": "idle", "f": 0.0}, "ai": {"state": "idle", "f": 0.0}}
var _me := -1
var _ai := -1
var _rects := {}
var _bars := {}
var _hp_max := {"player": 3, "ai": 3}

func _ready() -> void:
	var f := FileAccess.open(ProjectSettings.globalize_path("res://config/rom/vm_sprites.json"), FileAccess.READ)
	if f:
		_sprites = JSON.parse_string(f.get_as_text())
	var bg := ColorRect.new()
	bg.color = Color.BLACK
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(bg)
	var canvas := Control.new()                  # 128x32 DMD space, scaled to the slide
	canvas.set_anchors_preset(Control.PRESET_FULL_RECT)
	add_child(canvas)
	canvas.resized.connect(func(): _layout(canvas))
	for k in ["player", "ai", "label_l", "label_r"]:
		var t := TextureRect.new()
		t.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		t.stretch_mode = TextureRect.STRETCH_SCALE
		t.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
		canvas.add_child(t)
		_rects[k] = t
	for k in ["player", "ai"]:
		var b := ColorRect.new()
		b.color = Color(1.0, 0.51, 0.0)
		canvas.add_child(b)
		_bars[k] = b
	_rects["label_l"].texture = _load(int(_sprites.get("labels", {}).get("left", 0)))
	_rects["label_r"].texture = _load(int(_sprites.get("labels", {}).get("right", 0)))
	_layout(canvas)
	_read_health(true)

func _load(id: int) -> Texture2D:
	if id == 0:
		return null
	if not _tex.has(id):
		var path := ProjectSettings.globalize_path("res://images/vm/%d.png" % id)
		_tex[id] = ImageTexture.create_from_image(Image.load_from_file(path)) if FileAccess.file_exists(path) else null
	return _tex[id]

func _layout(canvas: Control) -> void:
	var sx: float = canvas.size.x / 128.0
	var sy: float = canvas.size.y / 32.0
	var s: float = min(sx, sy)
	var ox: float = (canvas.size.x - 128.0 * s) / 2.0
	var oy: float = (canvas.size.y - 32.0 * s) / 2.0
	canvas.set_meta("s", s)
	canvas.set_meta("o", Vector2(ox, oy))
	_place(canvas)

func _place(canvas: Control) -> void:
	var s: float = canvas.get_meta("s", 1.0)
	var o: Vector2 = canvas.get_meta("o", Vector2.ZERO)
	for k in ["player", "ai", "label_l", "label_r"]:
		var t: TextureRect = _rects[k]
		if t.texture == null:
			continue
		var w: float = t.texture.get_width()
		var x := 5.0
		if k == "ai":
			x = 123.0 - w
		elif k == "label_l":
			x = 5.0
		elif k == "label_r":
			x = 114.0
		t.position = o + Vector2(x, 0) * s
		t.size = Vector2(w, 32.0) * s
	for k in ["player", "ai"]:
		var hp: float = float(_me if k == "player" else _ai)
		var frac: float = clamp(hp / float(_hp_max[k]), 0.0, 1.0)
		var bx := 0.0 if k == "player" else 124.0
		var b: ColorRect = _bars[k]
		b.position = o + Vector2(bx + 1.0, 32.0 * (1.0 - frac)) * s
		b.size = Vector2(1.0, 32.0 * frac) * s

func _read_health(first: bool) -> void:
	var me: int = int(MPF.game.machine_vars.get("got_vm_me", 3))
	var ai: int = int(MPF.game.machine_vars.get("got_vm_ai", 3))
	_hp_max["player"] = 3
	_hp_max["ai"] = max(1, int(MPF.game.machine_vars.get("got_vm_ai_max", 3)))
	if not first:
		if ai < _ai:
			_start("player", "attack")
			_start("ai", "death" if ai <= 0 else "hit")
		if me < _me:
			var heavy: bool = _me - me >= 2
			_start("ai", "strong_attack" if heavy else "attack")
			_start("player", "death" if me <= 0 else ("knockback" if heavy else "hit"))
	_me = me
	_ai = ai

func _start(who: String, state: String) -> void:
	if _side[who]["state"] == "death":
		return
	_side[who]["state"] = state
	_side[who]["f"] = 0.0

func _process(delta: float) -> void:
	_read_health(false)
	for who in ["player", "ai"]:
		var st: Dictionary = _side[who]
		var frames: Array = _sprites.get(who, {}).get(st["state"], [])
		if frames.is_empty():
			continue
		st["f"] += delta * FPS
		var i := int(st["f"])
		if i >= frames.size():
			if st["state"] == "death":
				i = frames.size() - 1
			elif st["state"] == "knockback":
				st["state"] = "knockback_loop"
				st["f"] = 0.0
				i = 0
				frames = _sprites[who].get("knockback_loop", frames)
			elif st["state"] in ONESHOT or st["state"] == "strong_attack":
				st["state"] = "idle"
				st["f"] = 0.0
				i = 0
				frames = _sprites[who].get("idle", frames)
			else:
				st["f"] = fmod(st["f"], float(frames.size()))
				i = int(st["f"])
		_rects[who].texture = _load(int(frames[min(i, frames.size() - 1)]))
	_place(_rects["player"].get_parent())
