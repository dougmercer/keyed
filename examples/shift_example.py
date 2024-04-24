from pygments import format, lex
from pygments.lexers import PythonLexer

from manic import manic_pygments
from manic.animation import Animation, AnimationType, Code, Scene
from manic.easing import CubicEaseInOut

tokens = lex(r"import this", PythonLexer())
json_str = format(tokens, manic_pygments.ManicFormatter(style="base16-nord"))
styled_tokens = manic_pygments.StyledTokens.validate_json(json_str)

scene = Scene(scene_name="shift_example", num_frames=24, width=800, height=600)
code = Code(scene.ctx, styled_tokens, font_size=48)

scene.add(code.lines[0])

a = code.lines[0:1]

a.animate(
    "y",
    Animation(
        start_frame=2,
        end_frame=12,
        start_value=0,
        end_value=200,
        animation_type=AnimationType.ADDITIVE,
        easing=CubicEaseInOut,
    ),
)
for i in range(13, 24):
    sign = -(2 * (i % 2) - 1)
    a.shift(delta_x=0, delta_y=sign * 100, start_frame=i, end_frame=i + 1)

# scene.draw()
scene.preview()
