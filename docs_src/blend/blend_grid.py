from math import ceil

import cairo

from keyed import UP, Rectangle, Scene, Text

BlendMode = cairo.Operator

# Define the blend modes we want to visualize
blend_modes = [
    ("OVER", BlendMode.OVER),
    ("SOURCE", BlendMode.SOURCE),
    ("CLEAR", BlendMode.CLEAR),
    ("IN", BlendMode.IN),
    ("OUT", BlendMode.OUT),
    ("ATOP", BlendMode.ATOP),
    ("DEST", BlendMode.DEST),
    ("DEST_OVER", BlendMode.DEST_OVER),
    ("DEST_IN", BlendMode.DEST_IN),
    ("DEST_OUT", BlendMode.DEST_OUT),
    ("DEST_ATOP", BlendMode.DEST_ATOP),
    ("XOR", BlendMode.XOR),
    ("ADD", BlendMode.ADD),
    ("MULTIPLY", BlendMode.MULTIPLY),
    ("SCREEN", BlendMode.SCREEN),
    ("OVERLAY", BlendMode.OVERLAY),
    ("DARKEN", BlendMode.DARKEN),
    ("LIGHTEN", BlendMode.LIGHTEN),
    ("COLOR_DODGE", BlendMode.COLOR_DODGE),
    ("COLOR_BURN", BlendMode.COLOR_BURN),
    ("HARD_LIGHT", BlendMode.HARD_LIGHT),
    ("SOFT_LIGHT", BlendMode.SOFT_LIGHT),
    ("DIFFERENCE", BlendMode.DIFFERENCE),
    ("EXCLUSION", BlendMode.EXCLUSION),
    ("HSL_HUE", BlendMode.HSL_HUE),
    ("HSL_SATURATION", BlendMode.HSL_SATURATION),
    ("HSL_COLOR", BlendMode.HSL_COLOR),
    ("HSL_LUMINOSITY", BlendMode.HSL_LUMINOSITY),
]

# Create a scene with enough space for all blend modes
num_modes = len(blend_modes)
cols = 7
rows = ceil(num_modes / cols)

# Create a scene with appropriate dimensions
scene = Scene(scene_name="blend_modes", num_frames=1, width=cols * 200, height=rows * 180)

# Create a background layer with checkerboard pattern
background_layer = scene.create_layer("background", z_index=0)
bg = Rectangle(scene=scene, width=scene.nx(1), height=scene.ny(1), draw_stroke=False)
background_layer.add(bg)

foreground_layer = scene.create_layer("background", z_index=1000)

draw_stroke = False

# For each blend mode, create its own layer
for i, (name, operator) in enumerate(blend_modes):
    # Create a new layer for this blend mode example
    layer = scene.create_layer(f"mode_{name}", z_index=i + 1)

    # Calculate grid position
    col = i % cols
    row = i // cols

    # Calculate center position
    x = col * 200 + 100
    y = row * 180 + 90

    # Add the red rectangle (dest)
    red_rect = Rectangle(
        scene=scene,
        x=x - 20,
        y=y - 15,
        width=120,
        height=90,
        fill_color=(0.7, 0, 0),
        alpha=0.8,
        draw_stroke=draw_stroke,
    )
    layer.add(red_rect)

    # Add the blue rectangle (source)
    blue_rect = Rectangle(
        scene=scene,
        x=x + 20,
        y=y + 15,
        width=120,
        height=90,
        fill_color=(0, 0, 0.9),
        alpha=0.4,
        draw_stroke=draw_stroke,
        operator=operator,
    )
    layer.add(blue_rect)

    # Add a frame around the example
    frame = Rectangle(
        scene=scene,
        x=x,
        y=y,
        width=180,
        height=140,
        color=(0.2, 0.2, 0.2),
        alpha=1.0,
        line_width=2,
        draw_fill=False,
        draw_stroke=True,
    )
    foreground_layer.add(frame)

    # Add title text
    title = (
        Text(scene=scene, text=name.replace("_", " "), size=18, color=(0, 0, 0), alpha=1.0)
        .align_to(frame, direction=UP, center_on_zero=True)
        .translate(y=-15)
    )
    foreground_layer.add(title)
