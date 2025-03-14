import tempfile
from pathlib import Path
import argparse

import cairo
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import TwoSlopeNorm

from keyed import Rectangle, Scene

# Create output directory
output_dir = Path("blend_mode_comparison")
output_dir.mkdir(exist_ok=True)

# Define blend modes to test
blend_modes = [
    ("OVER", cairo.OPERATOR_OVER),
    ("SOURCE", cairo.OPERATOR_SOURCE),
    ("CLEAR", cairo.OPERATOR_CLEAR),
    ("IN", cairo.OPERATOR_IN),
    ("OUT", cairo.OPERATOR_OUT),
    ("ATOP", cairo.OPERATOR_ATOP),
    ("DEST", cairo.OPERATOR_DEST),
    ("DEST_OVER", cairo.OPERATOR_DEST_OVER),
    ("DEST_IN", cairo.OPERATOR_DEST_IN),
    ("DEST_OUT", cairo.OPERATOR_DEST_OUT),
    ("DEST_ATOP", cairo.OPERATOR_DEST_ATOP),
    ("XOR", cairo.OPERATOR_XOR),
    ("ADD", cairo.OPERATOR_ADD),
    ("MULTIPLY", cairo.OPERATOR_MULTIPLY),
    ("SCREEN", cairo.OPERATOR_SCREEN),
    ("OVERLAY", cairo.OPERATOR_OVERLAY),
    ("DARKEN", cairo.OPERATOR_DARKEN),
    ("LIGHTEN", cairo.OPERATOR_LIGHTEN),
    ("COLOR_DODGE", cairo.OPERATOR_COLOR_DODGE),
    ("COLOR_BURN", cairo.OPERATOR_COLOR_BURN),
    ("HARD_LIGHT", cairo.OPERATOR_HARD_LIGHT),
    ("SOFT_LIGHT", cairo.OPERATOR_SOFT_LIGHT),
    ("DIFFERENCE", cairo.OPERATOR_DIFFERENCE),
    ("EXCLUSION", cairo.OPERATOR_EXCLUSION),
    ("HSL_HUE", cairo.OPERATOR_HSL_HUE),
    ("HSL_SATURATION", cairo.OPERATOR_HSL_SATURATION),
    ("HSL_COLOR", cairo.OPERATOR_HSL_COLOR),
    ("HSL_LUMINOSITY", cairo.OPERATOR_HSL_LUMINOSITY),
]

# Size of test images
WIDTH = 400
HEIGHT = 400

# Rectangle dimensions
RECT_WIDTH = 200
RECT_HEIGHT = 150


def create_keyed_image_single_layer(blend_mode, width=WIDTH, height=HEIGHT, draw_stroke=False):
    """Create an image using Keyed with the specified blend mode using single layer compositing

    Args:
        blend_mode: The blend mode to test
        width: Image width
        height: Image height
        draw_stroke: Whether to draw strokes around the rectangles
    """
    scene = Scene(
        scene_name="blend_test", num_frames=1, width=width, height=height, output_dir=Path(tempfile.gettempdir())
    )

    # Add the red rectangle (destination)
    red_rect = Rectangle(
        scene=scene,
        x=width / 2 - 30,
        y=height / 2 - 30,
        width=RECT_WIDTH,
        height=RECT_HEIGHT,
        fill_color=(0.8, 0, 0),
        alpha=0.7,
        draw_stroke=draw_stroke,
        line_width=2,
        color=(0, 0, 0),
    )
    scene.add(red_rect)

    # Add the blue rectangle with the specified blend mode (source)
    blue_rect = Rectangle(
        scene=scene,
        x=width / 2 + 30,
        y=height / 2 + 30,
        width=RECT_WIDTH,
        height=RECT_HEIGHT,
        fill_color=(0, 0, 0.9),
        alpha=0.4,
        draw_stroke=draw_stroke,
        line_width=2,
        color=(0, 0, 0),
        operator=blend_mode,
    )
    scene.add(blue_rect)

    # Render the scene and get the image data
    buf = scene.rasterize(0).get_data()

    # Convert to numpy array
    img_array = np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 4)
    return img_array


def create_keyed_image_multi_layer(blend_mode, width=WIDTH, height=HEIGHT, draw_stroke=False):
    """Create an image using Keyed with the specified blend mode using multi-layer compositing

    Args:
        blend_mode: The blend mode to test
        width: Image width
        height: Image height
        draw_stroke: Whether to draw strokes around the rectangles
    """
    scene = Scene(
        scene_name="blend_test", num_frames=1, width=width, height=height, output_dir=Path(tempfile.gettempdir())
    )

    # Create first layer for red rectangle (destination)
    red_layer = scene.create_layer("red_layer", z_index=0)

    # Add the red rectangle to the first layer
    red_rect = Rectangle(
        scene=scene,
        x=width / 2 - 30,
        y=height / 2 - 30,
        width=RECT_WIDTH,
        height=RECT_HEIGHT,
        fill_color=(0.8, 0, 0),
        alpha=0.7,
        draw_stroke=draw_stroke,
        line_width=2,
        color=(0, 0, 0),
    )
    red_layer.add(red_rect)

    # Create second layer for blue rectangle with the blend mode
    blue_layer = scene.create_layer("blue_layer", z_index=1, blend=blend_mode)

    # Add the blue rectangle to the second layer with normal compositing
    blue_rect = Rectangle(
        scene=scene,
        x=width / 2 + 30,
        y=height / 2 + 30,
        width=RECT_WIDTH,
        height=RECT_HEIGHT,
        fill_color=(0, 0, 0.9),
        alpha=0.4,
        draw_stroke=draw_stroke,
        line_width=2,
        color=(0, 0, 0),
        operator=cairo.OPERATOR_OVER,  # Use regular compositing within the layer
    )
    blue_layer.add(blue_rect)

    # Render the scene and get the image data
    buf = scene.rasterize(0).get_data()

    # Convert to numpy array
    img_array = np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 4)
    return img_array


def _cairo_draw_shape(
    ctx: cairo.Context,
    fill_color: tuple[float, float, float],
    alpha: float,
    width: float,
    height: float,
    x: float,
    y: float,
    draw_stroke: bool,
    blend_mode: cairo.Operator,
):
    direct_mode = blend_mode in (cairo.OPERATOR_CLEAR, cairo.OPERATOR_SOURCE, cairo.OPERATOR_DEST)
    if direct_mode:
        ctx.set_operator(blend_mode)
        ctx.set_source_rgba(*fill_color, alpha)
        ctx.rectangle(x, y, width, height)

        if draw_stroke:
            ctx.fill_preserve()
            ctx.set_source_rgba(0, 0, 0, alpha)
            ctx.set_line_width(2)
            ctx.stroke()
        else:
            ctx.fill()
    else:
        ctx.push_group()

        ctx.set_operator(cairo.OPERATOR_OVER)
        ctx.set_source_rgba(*fill_color, 1)
        ctx.rectangle(x, y, width, height)

        if draw_stroke:
            ctx.fill_preserve()
            ctx.set_source_rgba(0, 0, 0, 1)
            ctx.set_line_width(2)
            ctx.stroke()
        else:
            ctx.fill()
        ctx.pop_group_to_source()
        ctx.set_operator(blend_mode)
        ctx.paint_with_alpha(alpha)


def create_cairo_image(blend_mode, width=WIDTH, height=HEIGHT, draw_stroke=False):
    """Create an image using Cairo directly with the specified blend mode

    Args:
        blend_mode: The blend mode to test
        width: Image width
        height: Image height
        draw_stroke: Whether to draw strokes around the rectangles
    """
    # Create a surface and context
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)

    # Define rectangle positions and dimensions
    # In Keyed, Rectangle positions are center-based
    # In Cairo, rectangles are drawn from top-left corner
    # Convert from center coordinates to top-left coordinates
    red_x = width / 2 - 30 - RECT_WIDTH / 2
    red_y = height / 2 - 30 - RECT_HEIGHT / 2
    blue_x = width / 2 + 30 - RECT_WIDTH / 2
    blue_y = height / 2 + 30 - RECT_HEIGHT / 2

    _cairo_draw_shape(ctx, (0.8, 0, 0), 0.7, RECT_WIDTH, RECT_HEIGHT, red_x, red_y, draw_stroke, cairo.OPERATOR_OVER)
    _cairo_draw_shape(ctx, (0, 0, 0.9), 0.4, RECT_WIDTH, RECT_HEIGHT, blue_x, blue_y, draw_stroke, blend_mode)

    # Get the image data
    buf = surface.get_data()

    # Convert to numpy array
    img_array = np.frombuffer(buf, dtype=np.uint8).reshape(height, width, 4)
    return img_array


def analyze_blend_mode(name, blend_mode, mode="single", draw_stroke=False):
    """Analyze a blend mode by comparing Keyed and Cairo implementations

    Args:
        name: Name of the blend mode
        blend_mode: Cairo blend mode operator
        mode: "single" for single layer compositing, "multi" for multi-layer compositing
        draw_stroke: Whether to draw strokes around the rectangles
    """
    print(f"Analyzing blend mode: {name} (Mode: {mode}, Stroke: {draw_stroke})")

    # Create images
    if mode == "single":
        keyed_img = create_keyed_image_single_layer(blend_mode, draw_stroke=draw_stroke)
        mode_display = "Single Layer"
    else:
        keyed_img = create_keyed_image_multi_layer(blend_mode, draw_stroke=draw_stroke)
        mode_display = "Multi Layer"

    cairo_img = create_cairo_image(blend_mode, draw_stroke=draw_stroke)

    # Save raw images for debugging
    keyed_rgb = keyed_img[..., [2, 1, 0, 3]].astype(np.uint8)
    cairo_rgb = cairo_img[..., [2, 1, 0, 3]].astype(np.uint8)

    # Generate a suffix for filenames based on stroke setting
    stroke_suffix = "_stroke" if draw_stroke else ""

    # Save as PNG using plt.imsave
    plt.imsave(output_dir / f"keyed_{name}_{mode}{stroke_suffix}.png", keyed_rgb)
    plt.imsave(output_dir / f"cairo_{name}{stroke_suffix}.png", cairo_rgb)

    # Calculate the difference for each channel
    diff = keyed_img.astype(float) - cairo_img.astype(float)
    # Positive means keyed is greater than cairo...

    # Create a figure to display the results
    fig, axs = plt.subplots(2, 3, figsize=(24, 12))

    # Display the images - convert BGRA to RGBA for proper display
    # Normalize values to 0-1 range for matplotlib
    keyed_display = keyed_rgb.astype(np.float32) / 255.0
    axs[0, 0].imshow(keyed_display)
    stroke_display = "With Stroke" if draw_stroke else "No Stroke"
    axs[0, 0].set_title(f"Keyed Implementation ({mode_display}, {stroke_display})\n{name}")
    axs[0, 0].axis("off")

    cairo_display = cairo_rgb.astype(np.float32) / 255.0
    axs[0, 1].imshow(cairo_display)
    axs[0, 1].set_title(f"Direct Cairo Implementation\n{name}")
    axs[0, 1].axis("off")

    norm = TwoSlopeNorm(vmin=-255, vcenter=0.0, vmax=255)

    # Display the differences for each channel with titles
    channel_names = ["B", "G", "R", "A"]
    positions = [(0, 2), (1, 0), (1, 1), (1, 2)]

    for i, (row, col) in enumerate(positions):
        im = axs[row, col].imshow(diff[..., i], cmap="PRGn", norm=norm)
        axs[row, col].set_title(f"Difference in {channel_names[i]} Channel")
        axs[row, col].axis("off")
        plt.colorbar(im, ax=axs[row, col], fraction=0.046, pad=0.04)

    # Set the figure title
    fig.suptitle(f"Blend Mode Comparison: {name} ({mode_display}, {stroke_display})", fontsize=16)

    # Save the figure
    output_path = output_dir / f"{name}_{mode}{stroke_suffix}.png"
    plt.tight_layout(rect=(0.0, 0.03, 1.0, 0.95))
    plt.savefig(output_path, dpi=150)
    plt.close()

    return output_path


def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Compare Cairo and Keyed blend modes")
    parser.add_argument(
        "--mode",
        choices=["single", "multi", "both"],
        default="both",
        help="Compositing mode: single layer, multi layer, or both (default)",
    )
    parser.add_argument(
        "--blend",
        type=str,
        default=None,
        help="Specific blend mode to test (e.g., 'OVER', 'MULTIPLY'). Default is to test all.",
    )
    parser.add_argument(
        "--stroke",
        choices=["on", "off", "both"],
        default="off",
        help="Whether to draw strokes: on, off, or both (default: off)",
    )
    args = parser.parse_args()

    # Filter blend modes if specific one is requested
    modes_to_test = blend_modes
    if args.blend:
        modes_to_test = [(name, mode) for name, mode in blend_modes if name == args.blend.upper()]
        if not modes_to_test:
            print(f"Error: Blend mode '{args.blend}' not found. Available modes:")
            for name, _ in blend_modes:
                print(f"  {name}")
            return

    # Test requested compositing modes and blend modes
    output_paths = []
    modes_to_run = []
    if args.mode in ["single", "both"]:
        modes_to_run.append("single")
    if args.mode in ["multi", "both"]:
        modes_to_run.append("multi")

    # Determine stroke settings to test
    strokes_to_test = []
    if args.stroke in ["on", "both"]:
        strokes_to_test.append(True)
    if args.stroke in ["off", "both"]:
        strokes_to_test.append(False)

    # Run all the requested combinations
    for compose_mode in modes_to_run:
        for stroke_setting in strokes_to_test:
            for name, blend_mode in modes_to_test:
                path = analyze_blend_mode(name, blend_mode, compose_mode, draw_stroke=stroke_setting)
                output_paths.append(path)
                print(f"Generated: {path}")

    print("\nAll blend mode comparison images have been generated at:")
    for path in output_paths:
        print(f"  {path}")


if __name__ == "__main__":
    main()
