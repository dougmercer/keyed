from keyed import Code, Scene, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(num_frames=24, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48, alpha=1)
scene.add(code)

code.lines[3:].rotate(-10, 0, 12)
code.lines[0].rotate(180, 0, 12)

scene.preview()
