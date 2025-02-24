from keyed import Scene

# from keyed_extras.svg.native_objects import SVGShapes
from keyed_extras import SVG

scene = Scene(num_frames=72)
# svg = SVG(scene, "manim_logo.svg", width=2000, height=1000).rotate(360, 0, 30)
svg = SVG(scene, "complex.svg", width=1000, height=1000).scale(2)

scene.add(svg)
