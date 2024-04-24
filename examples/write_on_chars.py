from pygments import format, lex
from pygments.lexers import PythonLexer

from manic import manic_pygments
from manic.animation import AnimationType, Code, Scene, lag_animation

with open("example.py", "r") as f:
    content = f.read()
tokens = lex(content, PythonLexer())
json_str = format(tokens, manic_pygments.ManicFormatter(style="base16-nord"))
styled_tokens = manic_pygments.StyledTokens.validate_json(json_str)

scene = Scene(scene_name="write_on_chars", num_frames=24, width=1920, height=1080)
code = Code(scene.ctx, styled_tokens, font_size=48, alpha=0)

scene.add(code)

code.chars[:].write_on(
    "alpha",
    lagged_animation=lag_animation(animation_type=AnimationType.ABSOLUTE),
    delay=1,
    duration=1,
    start_frame=0,
)

scene.preview()
