from keyed import Animation, AnimationType, Code, Rotation, Scene, tokenize

with open("examples/example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="write_on_tokens", num_frames=24, width=1920, height=1080)
code = Code(scene.ctx, styled_tokens, font_size=48, alpha=1)
s = code.lines[3:]
scene.add(code)

s.add_transformation(
    Rotation(
        scene.ctx,
        code.lines[0].rotation,
        code.lines[0].geom,
        Animation(0, 12, 0, -180, animation_type=AnimationType.ABSOLUTE),
    )
)

code.lines[0].add_transformation(
    Rotation(
        scene.ctx,
        code.lines[0].rotation,
        code.lines[0].geom,
        Animation(0, 12, 0, 180, animation_type=AnimationType.ABSOLUTE),
    )
)

s.add_transformation(
    Rotation(
        scene.ctx,
        s.rotation,
        s.geom,
        Animation(0, 12, 0, -180, animation_type=AnimationType.ABSOLUTE),
    )
)
# NOTE: This only works if I add `s`` to the scene explictly. Since I use `draw` to rotate, I'm
#       not binding the animation to the underlying objects. This sucks.

scene.preview()
