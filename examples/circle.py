from keyed import Animation, AnimationType, Circle, PingPong, Scene, Text

scene = Scene(scene_name="circle", num_frames=90, width=3840, height=2160)

circle = Circle(scene, 100, 100, radius=20)

scene.add(circle)

a = PingPong(
    Animation(
        start_value=100,
        end_value=200,
        animation_type=AnimationType.ABSOLUTE,
        start=0,
        end=12,
    ),
    5,
)

circle.translate(0, a(circle.controls.delta_y, scene.frame))

text = Text(scene, "Abc", 24, x=200, y=200, font="Anonymous Pro", color=(1, 0, 0))
scene.add(text)

b = PingPong(
    Animation(
        start_value=1,
        end_value=5,
        animation_type=AnimationType.MULTIPLY,
        start=0,
        end=24,
    ),
    n=5,
)(text.controls.delta_x, scene.frame)
text.translate(b, 0)
c2 = text.emphasize()

scene.add(c2)
