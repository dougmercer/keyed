import sys

from pygments import format, lex
from pygments.lexers import PythonLexer

from manic import manic_pygments
from manic.animation import Animation, Code
with open("example.py", "r") as f:
    content = f.read()
tokens = lex(content, PythonLexer())
json_str = format(tokens, manic_pygments.ManicFormatter())
print(json_str)
styled_tokens = manic_pygments.StyledTokens.validate_json(json_str)
print(styled_tokens)


animation = Animation(num_frames=1)
code = Code(animation.ctx, styled_tokens)

print(code.lines)

code.draw(animation.ctx)

animation.surface.write_to_png("manic.png")
