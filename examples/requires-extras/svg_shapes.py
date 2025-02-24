from keyed import Scene
from keyed.extras import SVGShapes

scene = Scene()

svg = (
    SVGShapes(
        scene=scene,
        file_name="manim_logo.svg",
        height=1000,
        disable_stroke=True,
    )
    .center()
    .translate(100, 0, 0, 12)
    .rotate(360, 0, 24)
)

scene.add(svg)
