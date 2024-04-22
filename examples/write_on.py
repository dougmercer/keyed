from pygments import format, lex
from pygments.lexers import PythonLexer

from manic import manic_pygments
from manic.animation import Animation, Character, Code, Scene, lag_animation

with open("example.py", "r") as f:
    content = f.read()
tokens = lex(content, PythonLexer())
json_str = format(tokens, manic_pygments.ManicFormatter(style="base16-nord"))
styled_tokens = manic_pygments.StyledTokens.validate_json(json_str)

scene = Scene(scene_name="write_on_example", num_frames=24, width=1920, height=1080)
code = Code(scene.ctx, styled_tokens, font_size=48)

runner = Character(
    scene.ctx, "hello", size=64, font="Anonymous Pro", color=(0.5, 0.5, 0.5), x=10, y=10
)
runner.x.add_animation(Animation(start_frame=0, end_frame=24, start_value=10, end_value=500))
runner.y.add_animation(Animation(start_frame=0, end_frame=24, start_value=10, end_value=500))

scene.add(code)
scene.add(runner)

# code.chars[:10].animate(
#     "alpha", Animation(start_frame=0, end_frame=24, start_value=0, end_value=1),
# )

code.lines[:].write_on(
    "alpha", lagged_animation=lag_animation(), delay=2, duration=1, start_frame=2
)

scene.draw()
