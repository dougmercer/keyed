from keyed import LEFT, AnimationType, Circle, Code, Scene, stagger, tokenize

scene = Scene(scene_name="code_replace_complex", num_frames=90)

styled_tokens1 = tokenize(r"x = 1 + 2 + 3")
code1 = Code(scene, styled_tokens1, font_size=36, x=200, y=200)

styled_tokens2 = tokenize(r"x = 1 + get_two() + 3")
code2 = Code(scene, styled_tokens2, font_size=36, alpha=0, x=200, y=200)

scene.add(code1, code2)

code1.chars[8].fade(0, 0, 12)

code1.chars[-3:].align_to(code2.chars[-3], start=12, end=36, direction=LEFT)

code2.chars[8:18].write_on(
    "alpha",
    lagged_animation=stagger(),
    delay=4,
    duration=1,
    start=36,
)

scene.scale(2, 0, 24, center=Circle(scene, 200, 100).geom)
