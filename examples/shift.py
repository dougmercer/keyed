from keyed import Animation, AnimationType, Code, Scene, tokenize
from keyed.easing import CubicEaseInOut

styled_tokens = tokenize(r"import this")

scene = Scene(scene_name="shift", num_frames=24, width=800, height=600)
code = Code(scene, styled_tokens, font_size=48)

scene.add(code.lines[0])

a = code.lines[0:1]

a.animate(
    "y",
    Animation(
        start_frame=2,
        end_frame=12,
        start_value=0,
        end_value=200,
        animation_type=AnimationType.ADDITIVE,
        easing=CubicEaseInOut,
    ),
)
for i in range(13, 24):
    sign = -(2 * (i % 2) - 1)
    a.translate(x=0, y=sign * 100, start_frame=i, end_frame=i + 1)

scene.preview()
