from keyed import LEFT, Code, Scene, Text, tokenize
from keyed.text import blink

scene = Scene(num_frames=180, width=800, height=800)

# Create the before/after code snippets, and align them
# so that the final code snippet would be centered on the screen
before = Code(tokenize(r"x = 1 + 2 + 3"), font_size=60)
after = Code(tokenize(r"x = 1 + get_two() + 3"), font_size=60, alpha=0).center()
before.align_to(after, direction=LEFT, center_on_zero=True)

# Keep an invisible reference around so we can animate the tail back
# to the original layout after the replacement has been typed in.
before_reference = Code(tokenize(r"x = 1 + 2 + 3"), font_size=60, alpha=0)
before_reference.align_to(after, direction=LEFT, center_on_zero=True)

# Create a cursor
cursor = Text(
    "|",
    size=60,
    color=(1, 1, 1),
    alpha=blink(scene.frame, 12, 15),
)
scene.add(cursor)

before.chars[8:7:-1].type_off(12, 4, 1, cursor=cursor)

# Animate transforming from before to after
# First, fade out the "2"
# Move the "+ 3" over to align to where it is in after
before.chars[-3:].align_to(after.chars[-3], start=12, end=36, direction=LEFT)
# Make each character in "get_two()" appear one at a time.
after.chars[8:17].type_on(delay=4, duration=1, start=36, cursor=cursor)

# Hold on the replacement for a beat, then write it back off and
# restore the original code block.
after.chars[16:7:-1].type_off(delay=4, duration=1, start=93, cursor=cursor)
before.chars[-3:].align_to(
    before_reference.chars[-3],
    start=93,
    end=129,
    direction=LEFT,
)
before.chars[8:9].type_on(delay=4, duration=1, start=129, cursor=cursor)

# Outline the code
outline = before.emphasize(draw_fill = False, radius=10, line_width=5, buffer=40)

# Add everything to the scene
scene.add(before, after, outline)
