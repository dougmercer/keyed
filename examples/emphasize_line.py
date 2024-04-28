import cairo
from manic import Code, Scene, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="write_on_lines", num_frames=24, width=1920, height=1080)
code = Code(scene.ctx, styled_tokens, font_size=48, alpha=1)

scene.add(code)

r = code.lines[0].emphasize(
    operator=cairo.OPERATOR_SCREEN,
    fill_color=(0.5, 0.1, 0),
    dash=((10, 2), 0),
)
scene.add(r)

# emphs = [c.emphasize() for c in code.chars]
# scene.add(*emphs)

code.chars.shift(100, 0, 0, 12)

scene.preview()
