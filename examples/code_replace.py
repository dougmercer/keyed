from keyed import Code, Scene, stagger, tokenize

scene = Scene(scene_name="code_replace", num_frames=60, width=800, height=600)

styled_tokens1 = tokenize(r"import this")
code1 = Code(scene, styled_tokens1, font_size=48)

styled_tokens2 = tokenize(r"import that")
code2 = Code(scene, styled_tokens2, font_size=48, alpha=0)

scene.add(code1, code2)

code1.chars[-1:-5:-1].write_on(
    "alpha",
    animator=stagger(start_value=1, end_value=0),
    delay=4,
    duration=1,
    start=0,
)

code2.chars[-5:].write_on(
    "alpha",
    animator=stagger(),
    delay=4,
    duration=1,
    start=24,
)
