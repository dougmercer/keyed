from pygments import format, lex
from pygments.lexers import PythonLexer

from manic import manic_pygments
from manic.animation import Animation, Code, Scene

with open("example.py", "r") as f:
    content = f.read()
tokens = lex(content, PythonLexer())
json_str = format(tokens, manic_pygments.ManicFormatter(style="base16-nord"))
styled_tokens = manic_pygments.StyledTokens.validate_json(json_str)

scene = Scene(scene_name="fade_in_example", num_frames=24, width=1920, height=1080)
code = Code(scene.ctx, styled_tokens, font_size=48)

scene.add(code)

code.chars[:10].animate(
    "alpha",
    Animation(start_frame=0, end_frame=24, start_value=0, end_value=1),
)

scene.draw()
