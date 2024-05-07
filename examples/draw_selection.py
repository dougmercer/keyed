from keyed import Code, Scene, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="draw_selection", num_frames=24, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48)

scene.add(code.tokens[:10])

scene.preview()
