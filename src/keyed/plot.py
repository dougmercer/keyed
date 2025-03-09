"""Plotting functionality."""

from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, Self, Sequence

import cairo
import numpy as np
import shapely
import shapely.affinity
from signified import Computed, Signal, as_signal, computed

from .animation import Animation
from .base import Base
from .scene import Scene

__all__ = ["ParametricPlot", "FunctionPlot", "PointPlot", "AxisConfig", "Axes"]


@dataclass
class AxisConfig:
    """Configuration for plot axis styling and ticks."""

    show_ticks: bool = True
    show_labels: bool = True
    num_ticks: int = 5
    tick_length: float = 6
    tick_width: float = 1
    label_offset: float = 20
    font_size: float = 18
    font: str = "Roboto"
    font_color: tuple[float, float, float] = (1.0, 1.0, 1.0)
    line_color: tuple[float, float, float] = (0.8, 0.8, 0.8)
    format: str = "{:.1f}"  # Format string for tick labels


@dataclass
class AxesAnchor:
    """Information needed by Axes to render alongside a plot."""

    width: float
    height: float
    ranges: dict[str, tuple[float, float]]
    transform: cairo.Matrix
    metadata: dict[str, Any] = field(default_factory=dict)


class AxesAnchorable(Protocol):
    """Interface for objects that can have axes attached."""

    def get_axes_anchor(self) -> AxesAnchor: ...


class Axes(Base):
    """Renders axes for a plot."""

    def __init__(
        self,
        scene: Scene,
        x_config: AxisConfig | None = None,
        y_config: AxisConfig | None = None,
        plot: AxesAnchorable | None = None,
    ):
        super().__init__(scene)
        self.scene = scene
        self.ctx = scene.get_context()
        self.x_config = x_config or AxisConfig()
        self.y_config = y_config or AxisConfig()
        self.plot = plot
        self.alpha = Signal(1.0)

    def _calculate_tick_positions(self, start: float, end: float, num: int) -> list[float]:
        """Calculate evenly spaced tick positions."""
        return np.linspace(start, end, num).flatten().tolist()

    def _draw_x_axis(self, anchor: AxesAnchor) -> None:
        """Draw x-axis line, ticks, and labels."""
        if not self.x_config or (not self.x_config.show_ticks and not self.x_config.show_labels):
            return

        x_min, x_max = anchor.ranges["x"]
        height = anchor.height

        # Draw axis line
        self.ctx.new_path()
        self.ctx.move_to(0, height)
        self.ctx.line_to(anchor.width, height)
        self.ctx.set_source_rgba(*self.x_config.line_color, self.alpha.value)
        self.ctx.set_line_width(self.x_config.tick_width)
        self.ctx.stroke()

        # Draw ticks and labels
        x_ticks = self._calculate_tick_positions(x_min, x_max, self.x_config.num_ticks)
        for x_val in x_ticks:
            x_pos = (x_val - x_min) / (x_max - x_min) * anchor.width

            if self.x_config.show_ticks:
                # Draw tick mark
                self.ctx.set_source_rgba(*self.x_config.line_color, self.alpha.value)
                self.ctx.move_to(x_pos, height)
                self.ctx.line_to(x_pos, height + self.x_config.tick_length)
                self.ctx.stroke()

            if self.x_config.show_labels:
                # Draw label
                self.ctx.set_source_rgba(*self.x_config.font_color, self.alpha.value)
                self.ctx.select_font_face(self.x_config.font)
                self.ctx.set_font_size(self.x_config.font_size)
                label = self.x_config.format.format(x_val)

                # Center text
                extents = self.ctx.text_extents(label)
                text_x = x_pos - extents.width / 2
                text_y = height + self.x_config.label_offset

                self.ctx.move_to(text_x, text_y)
                self.ctx.show_text(label)

    def _draw_y_axis(self, anchor: AxesAnchor) -> None:
        """Draw y-axis line, ticks, and labels."""
        if not self.y_config or (not self.y_config.show_ticks and not self.y_config.show_labels):
            return

        y_min, y_max = anchor.ranges["y"]

        # Draw axis line
        self.ctx.new_path()
        self.ctx.move_to(0, 0)
        self.ctx.line_to(0, anchor.height)
        self.ctx.set_source_rgba(*self.y_config.line_color, self.alpha.value)
        self.ctx.set_line_width(self.y_config.tick_width)
        self.ctx.stroke()

        # Draw ticks and labels
        y_ticks = self._calculate_tick_positions(y_min, y_max, self.y_config.num_ticks)
        for y_val in y_ticks:
            y_pos = anchor.height - (y_val - y_min) / (y_max - y_min) * anchor.height

            if self.y_config.show_ticks:
                # Draw tick mark
                self.ctx.move_to(0, y_pos)
                self.ctx.line_to(-self.y_config.tick_length, y_pos)
                self.ctx.stroke()

            if self.y_config.show_labels:
                # Draw label
                self.ctx.set_source_rgba(*self.y_config.font_color, self.alpha.value)
                self.ctx.select_font_face(self.y_config.font)
                self.ctx.set_font_size(self.y_config.font_size)
                label = self.y_config.format.format(y_val)

                # Right align text
                extents = self.ctx.text_extents(label)
                text_x = -self.y_config.label_offset - extents.width
                text_y = y_pos + extents.height / 3  # Adjust for vertical centering

                self.ctx.move_to(text_x, text_y)
                self.ctx.show_text(label)

    def draw(self) -> None:
        """Draw both axes if plot is attached."""
        if not self.plot:
            return

        anchor = self.plot.get_axes_anchor()

        self.ctx.save()
        self.ctx.transform(anchor.transform)

        if self.x_config:
            self._draw_x_axis(anchor)
        if self.y_config:
            self._draw_y_axis(anchor)

        self.ctx.restore()

    @property
    def _raw_geom_now(self) -> shapely.Polygon:
        """Return a minimal geometry for the axes area."""
        if not self.plot:
            return shapely.Polygon()

        anchor = self.plot.get_axes_anchor()
        return shapely.box(0, 0, anchor.width, anchor.height)


class ParametricPlot(Base, AxesAnchorable):
    """A general parametric plot that efficiently visualizes parametric functions.

    This implementation draws the curve and tracking point using Cairo.

    Args:
        scene: The scene to which the plot belongs
        x_func: Function that computes x coordinate given parameter t
        y_func: Function that computes y coordinate given parameter t
        width: Width of the plot area
        height: Height of the plot area
        t_start: Starting value for parameter t
        t_end: Ending value for parameter t
        x_range: Optional fixed range for x axis as (min, max)
        y_range: Optional fixed range for y axis as (min, max)
        point_color: RGB color tuple for the tracking point
        curve_color: RGB color tuple for the curve
        line_width: Width of the curve line
        point_radius: Radius of the tracking point
        num_segments: Number of segments to use when drawing the curve
        show_reference_lines: Whether to show dashed reference lines
    """

    def __init__(
        self,
        scene: Scene,
        x_func: Callable[[float], float],
        y_func: Callable[[float], float],
        width: float = 400,
        height: float = 400,
        t_start: float = 0,
        t_end: float = 1,
        x_range: tuple[float, float] | None = None,
        y_range: tuple[float, float] | None = None,
        point_color: tuple[float, float, float] = (1, 0.5, 0),
        curve_color: tuple[float, float, float] = (1, 1, 1),
        line_width: float = 2,
        point_radius: float = 8,
        num_segments: int = 100,
        show_reference_lines: bool = False,
    ):
        super().__init__(scene)

        # Store scene and context
        self.scene = scene
        self.ctx = scene.get_context()

        # Store functions and parameters
        self.x_func = x_func
        self.y_func = y_func
        self._width = width
        self._height = height
        self.t_start = t_start
        self.t_end = t_end
        self.num_segments = num_segments
        self.show_reference_lines = show_reference_lines

        # Store styling parameters
        self.point_color = point_color
        self.curve_color = curve_color
        self.line_width = as_signal(line_width)
        self.point_radius = as_signal(point_radius)
        self.alpha = Signal(1.0)

        # Add progress property for animation
        self.progress = Signal(0.0)

        # Calculate ranges if not provided
        self._calculate_ranges(x_range, y_range)

        # Store the curve points
        self._calculate_curve_points()

        # Initialize transform controls
        self._dependencies.extend([self.line_width, self.point_radius, self.progress])
        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

    def _calculate_ranges(self, x_range: tuple[float, float] | None, y_range: tuple[float, float] | None) -> None:
        """Calculate x and y ranges if not provided."""
        if x_range is None:
            t_vals = np.linspace(self.t_start, self.t_end, self.num_segments)
            x_vals = [self.x_func(t) for t in t_vals]
            self.x_min, self.x_max = min(x_vals), max(x_vals)
        else:
            self.x_min, self.x_max = x_range

        if y_range is None:
            t_vals = np.linspace(self.t_start, self.t_end, self.num_segments)
            y_vals = [self.y_func(t) for t in t_vals]
            self.y_min, self.y_max = min(y_vals), max(y_vals)
        else:
            self.y_min, self.y_max = y_range

    def _calculate_curve_points(self) -> None:
        """Calculate and store the curve points."""
        t_vals = np.linspace(self.t_start, self.t_end, self.num_segments)
        self.curve_points = np.array([[self.map_x(self.x_func(t)), self.map_y(self.y_func(t))] for t in t_vals])

    def map_x(self, x: float) -> float:
        """Map an x value from function space to plot space."""
        return ((x - self.x_min) / (self.x_max - self.x_min)) * self._width

    def map_y(self, y: float) -> float:
        """Map a y value from function space to plot space."""
        return self._height - ((y - self.y_min) / (self.y_max - self.y_min)) * self._height

    def get_axes_anchor(self) -> AxesAnchor:
        """Provide information needed by axes for rendering."""
        return AxesAnchor(
            width=self._width,
            height=self._height,
            ranges={"x": (self.x_min, self.x_max), "y": (self.y_min, self.y_max)},
            transform=self.controls.matrix.value,
        )

    def draw(self) -> None:
        """Draw the curve, tracking point, and reference lines."""
        self.ctx.save()
        self.ctx.transform(self.controls.matrix.value)

        # Draw the curve
        self.ctx.new_path()
        self.ctx.move_to(*self.curve_points[0])
        for point in self.curve_points[1:]:
            self.ctx.line_to(*point)
        self.ctx.set_source_rgba(*self.curve_color, self.alpha.value)
        self.ctx.set_line_width(self.line_width.value)
        self.ctx.stroke()

        # Get current point position
        x, y = self.get_point_position()

        # Draw reference lines if enabled
        if self.show_reference_lines:
            self._draw_reference_lines(x, y)

        # Draw the tracking point
        self.ctx.new_path()
        self.ctx.arc(x, y, self.point_radius.value, 0, 2 * np.pi)
        self.ctx.set_source_rgba(*self.point_color, self.alpha.value)
        self.ctx.fill()

        self.ctx.restore()

    def _draw_reference_lines(self, x: float, y: float) -> None:
        """Draw dashed reference lines to axes."""
        # Draw horizontal reference line
        self.ctx.new_path()
        self.ctx.move_to(0, y)
        self.ctx.line_to(x, y)
        self.ctx.set_source_rgba(*self.point_color, self.alpha.value * 0.5)
        self.ctx.set_dash([5, 5])
        self.ctx.set_line_width(self.line_width.value)
        self.ctx.stroke()

        # Draw vertical reference line
        self.ctx.new_path()
        self.ctx.move_to(x, self._height)
        self.ctx.line_to(x, y)
        self.ctx.stroke()
        self.ctx.set_dash([])

    def get_point_position(self) -> tuple[float, float]:
        """Calculate the current position of the tracking point."""
        t = self.t_start + self.progress.value * (self.t_end - self.t_start)
        x = self.map_x(self.x_func(t))
        y = self.map_y(self.y_func(t))
        return x, y

    def animate_progress(self, start: int = 0, end: int | None = None) -> Self:
        """Animate the plot's progress from start to end frames.

        Args:
            start: Starting frame for the animation
            end: Ending frame for the animation (defaults to scene.num_frames)

        Returns:
            self for method chaining
        """
        if end is None:
            end = self.scene.num_frames

        self.progress = Animation(start, end, 0, 1)(0, self.scene.frame)
        return self

    @property
    def _raw_geom_now(self) -> shapely.Polygon:
        """Return the geometric representation of the plot area."""
        buffer = max(self.line_width.value, self.point_radius.value)
        return shapely.box(-buffer, -buffer, self._width + buffer, self._height + buffer)

    @property
    def position(self) -> Computed[shapely.Point]:
        """Return a reactive Point representing the current position of the tracking point, respecting transformations."""

        @computed
        def point_position(progress: float, matrix: cairo.Matrix) -> shapely.Point:
            # Calculate raw point position
            t = self.t_start + progress * (self.t_end - self.t_start)
            x = self.map_x(self.x_func(t))
            y = self.map_y(self.y_func(t))
            point = shapely.Point(x, y)

            # Apply current transformation matrix
            transform_params = [matrix.xx, matrix.xy, matrix.yx, matrix.yy, matrix.x0, matrix.y0]
            return shapely.affinity.affine_transform(point, transform_params)

        return point_position(self.progress, self.controls.matrix)


class EasingVisualizer(ParametricPlot):
    """Specialized parametric plot for visualizing easing functions."""

    def __init__(
        self,
        scene: Scene,
        easing_func: Callable[[float], float],
        width: float = 400,
        height: float = 400,
        point_color: tuple[float, float, float] = (1, 0.5, 0),
        curve_color: tuple[float, float, float] = (1, 1, 1),
        line_width: float = 2,
        point_radius: float = 8,
        num_segments: int = 100,
        show_reference_lines: bool = False,
        **kwargs,
    ):
        super().__init__(
            scene=scene,
            x_func=lambda t: t,
            y_func=easing_func,
            width=width,
            height=height,
            t_start=0,
            t_end=1,
            x_range=(0, 1),
            y_range=(0, 1),
            point_color=point_color,
            curve_color=curve_color,
            line_width=line_width,
            point_radius=point_radius,
            num_segments=num_segments,
            show_reference_lines=show_reference_lines,
            **kwargs,
        )


class FunctionPlot(ParametricPlot):
    """A plot for visualizing 2D functions of the form y = f(x).

    Args:
        scene: The scene to which the plot belongs
        func: Function that computes y coordinate given x
        width: Width of the plot area
        height: Height of the plot area
        x_start: Starting x value
        x_end: Ending x value
        y_range: Optional fixed range for y axis as (min, max)
        point_color: RGB color tuple for the tracking point
        curve_color: RGB color tuple for the curve
        line_width: Width of the curve line
        point_radius: Radius of the tracking point
        num_segments: Number of segments to use when drawing the curve
        show_reference_lines: Whether to show dashed reference lines
    """

    def __init__(
        self,
        scene: Scene,
        func: Callable[[float], float],
        width: float = 400,
        height: float = 400,
        x_start: float = -5,
        x_end: float = 5,
        y_range: tuple[float, float] | None = None,
        point_color: tuple[float, float, float] = (1, 0.5, 0),
        curve_color: tuple[float, float, float] = (1, 1, 1),
        line_width: float = 2,
        point_radius: float = 8,
        num_segments: int = 100,
        show_reference_lines: bool = False,
        **kwargs,
    ):
        # Create parametric functions from the 2D function
        def x_func(t):
            return x_start + t * (x_end - x_start)

        def y_func(t):
            return func(x_func(t))

        super().__init__(
            scene=scene,
            x_func=x_func,
            y_func=y_func,
            width=width,
            height=height,
            t_start=0,
            t_end=1,
            x_range=(x_start, x_end),
            y_range=y_range,
            point_color=point_color,
            curve_color=curve_color,
            line_width=line_width,
            point_radius=point_radius,
            num_segments=num_segments,
            show_reference_lines=show_reference_lines,
            **kwargs,
        )


class PointPlot(ParametricPlot):
    """A plot for visualizing a sequence of (x,y) points with smooth interpolation.

    Args:
        scene: The scene to which the plot belongs
        x_points: Sequence of x coordinates
        y_points: Sequence of y coordinates
        width: Width of the plot area
        height: Height of the plot area
        x_range: Optional fixed range for x axis as (min, max)
        y_range: Optional fixed range for y axis as (min, max)
        point_color: RGB color tuple for the tracking point
        curve_color: RGB color tuple for the curve
        line_width: Width of the curve line
        point_radius: Radius of the tracking point
        show_reference_lines: Whether to show dashed reference lines
        interpolate: Whether to interpolate between points (True) or connect with straight lines (False)
    """

    def __init__(
        self,
        scene: Scene,
        x_points: Sequence[float] | np.ndarray,
        y_points: Sequence[float] | np.ndarray,
        width: float = 400,
        height: float = 400,
        x_range: tuple[float, float] | None = None,
        y_range: tuple[float, float] | None = None,
        point_color: tuple[float, float, float] = (1, 0.5, 0),
        curve_color: tuple[float, float, float] = (1, 1, 1),
        line_width: float = 2,
        point_radius: float = 8,
        show_reference_lines: bool = True,
        interpolate: bool = True,
        **kwargs,
    ):
        if len(x_points) != len(y_points):
            raise ValueError("x_points and y_points must have the same length")

        if len(x_points) < 2:
            raise ValueError("Must provide at least 2 points")

        # Convert points to numpy arrays for easier manipulation
        x = np.array(x_points)
        y = np.array(y_points)

        if interpolate:
            # Create interpolation functions using cubic splines
            from scipy.interpolate import CubicSpline

            t = np.linspace(0, 1, len(x))
            x_spline = CubicSpline(t, x)
            y_spline = CubicSpline(t, y)

            def x_func(t):
                return float(x_spline(t))

            def y_func(t):
                return float(y_spline(t))

            num_segments = 100 * len(x_points)  # More segments for smooth curves
        else:
            # Linear interpolation between points
            def make_lerp_func(points):
                def lerp(t):
                    # Convert t to index
                    idx = t * (len(points) - 1)
                    i = int(idx)
                    if i >= len(points) - 1:
                        return float(points[-1])
                    # Interpolate between points[i] and points[i+1]
                    frac = idx - i
                    return float(points[i] * (1 - frac) + points[i + 1] * frac)

                return lerp

            x_func = make_lerp_func(x)
            y_func = make_lerp_func(y)
            num_segments = len(x_points) * 2  # Fewer segments needed for lines

        super().__init__(
            scene=scene,
            x_func=x_func,
            y_func=y_func,
            width=width,
            height=height,
            t_start=0,
            t_end=1,
            x_range=x_range or (np.min(x), np.max(x)),
            y_range=y_range or (np.min(y), np.max(y)),
            point_color=point_color,
            curve_color=curve_color,
            line_width=line_width,
            point_radius=point_radius,
            num_segments=num_segments,
            show_reference_lines=show_reference_lines,
            **kwargs,
        )
