from keyed import Animation, AnimationType, Code, PingPong, Scene, easing, tokenize

styled_tokens = tokenize(r"import this")

scene = Scene(scene_name="ping_pong", num_frames=90, width=800, height=600)
code = Code(scene, styled_tokens, font_size=48)

scene.add(code.lines[0])

a = code.lines[0:1]

a.animate(
    "y",
    PingPong(
        n=3,
        animation=Animation(
            start_frame=0,
            end_frame=12,
            start_value=50,
            end_value=150,
            easing=easing.CubicEaseInOut,
            animation_type=AnimationType.ABSOLUTE,
        ),
    ),
)

scene.preview()
