from keyed import Animation, Code, Scene, easing, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="write_on_tokens", num_frames=48, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, alpha=1)

scene.add(code)
# scene.controls.pivot.x.set(scene.width / 2)
# scene.controls.pivot.y.set(scene.height / 2)
scene.rotate(360, 0, 12)
scene.scale(2, 16, 30, center=code.geom)
scene.translate(100, 100, 36, 42)

scene.preview()
