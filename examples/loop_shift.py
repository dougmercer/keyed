from keyed import Animation, AnimationType, Code, Loop, Scene, easing, tokenize

styled_tokens = tokenize(r"import this")

scene = Scene(scene_name="loop_shift", num_frames=48, width=800, height=600)
code = Code(scene, styled_tokens, font_size=48, y=110)

scene.add(code.lines[0])

a = code.lines[0:1]

a.animate(
    "y",
    Loop(
        n=3,
        animation=Animation(
            start_frame=0,
            end_frame=12,
            start_value=-100,
            end_value=100,
            easing=easing.CubicEaseInOut,
            animation_type=AnimationType.ADDITIVE,
        ),
    ),
)

scene.preview()
