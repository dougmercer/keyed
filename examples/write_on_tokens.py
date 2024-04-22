from pygments import format, lex
from pygments.lexers import PythonLexer

from manic import manic_pygments
from manic.animation import Code, Scene, lag_animation

import pprint

with open("example.py", "r") as f:
    content = f.read()
tokens = lex(content, PythonLexer())
json_str = format(tokens, manic_pygments.ManicFormatter(style="base16-nord"))
styled_tokens = manic_pygments.StyledTokens.validate_json(json_str)

pprint.pprint(styled_tokens)

scene = Scene(scene_name="write_on_tokens", num_frames=24, width=1920, height=1080)
code = Code(scene.ctx, styled_tokens, font_size=48)

scene.add(code)

code.tokens[:].write_on(
    "alpha", lagged_animation=lag_animation(), delay=1, duration=1, start_frame=0
)

scene.draw()
