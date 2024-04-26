from manic import AnimationType, Code, Rectangle, Scene, lag_animation, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="write_on_lines", num_frames=24, width=1920, height=1080)
code = Code(scene.ctx, styled_tokens, font_size=48, alpha=1)

scene.add(code)

# print(code.lines[0][0].extents())
r = code.lines[0].emphasize()
scene.add(r)

# emphs = [c.emphasize() for c in code.chars]
# scene.add(*emphs)

code.chars.shift(100, 0, 0, 12)

scene.preview()
