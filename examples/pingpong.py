from keyed import Animation, Code, PingPong, Scene, Signal, easing, tokenize

styled_tokens = tokenize(r"import this")

scene = Scene(scene_name="ping_pong", num_frames=90, width=800, height=600)
code = Code(scene, styled_tokens, font_size=48)

scene.add(code.lines[0])

a = code.lines[0:1]
y_anim = PingPong(
    n=3,
    animation=Animation(
        start=0,
        end=12,
        start_value=0,
        end_value=150,
        ease=easing.cubic_in_out,
    ),
)(Signal(0.0), scene.frame)
a.translate(0, y_anim)

scene.preview()
