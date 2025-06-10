from keyed import LEFT, Code, Scene, stagger, tokenize

scene = Scene(scene_name="code_replace_complex", num_frames=90, width=800, height=800)

# Create the before/after code snippets, and align them
# so that the final code snippet would be centered on the screen
before = Code(scene, tokenize(r"x = 1 + 2 + 3"), font_size=60)
after = Code(scene, tokenize(r"x = 1 + get_two() + 3"), font_size=60, alpha=0).center()
before.align_to(after, direction=LEFT, center_on_zero=True)

# Animate transforming from before to after
# First, fade out the "2"
before.chars[8].fade(0, 0, 12)
# Move the "+ 3" over to align to where it is in after
before.chars[-3:].align_to(after.chars[-3], start=12, end=36, direction=LEFT)
# Make each character in "get_two()" appear one at a time.
after.chars[8:18].write_on(
    "alpha",
    animator=stagger(),
    delay=4,
    duration=1,
    start=36,
)

# Outline the code
outline = before.emphasize(draw_fill=False, radius=10, line_width=5, buffer=40)

# Add everything to the scene
scene.add(before, after, outline)
