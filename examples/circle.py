from keyed import Animation, AnimationType, Circle, PingPong, Scene, Text, easing

scene = Scene(scene_name="circle", num_frames=90, width=3840, height=2160)

circle = Circle(scene, 100, 100, radius=20)

scene.add(circle)

circle.animate(
    "y",
    PingPong(
        Animation(
            start_value=100,
            end_value=200,
            animation_type=AnimationType.ABSOLUTE,
            start_frame=0,
            end_frame=12,
            easing=easing.CubicEaseInOut,
        ),
        n=5,
    ),
)

text = Text(scene, "Abc", 24, x=200, y=200, font="Anonymous Pro", color=(1, 0, 0), token_type=None)
scene.add(text)

c2 = text.emphasize()

text.animate(
    "x",
    PingPong(
        Animation(
            start_value=1,
            end_value=5,
            animation_type=AnimationType.MULTIPLICATIVE,
            start_frame=0,
            end_frame=12,
            easing=easing.CubicEaseInOut,
        ),
        n=5,
    ),
)

scene.add(c2)
scene.preview()
