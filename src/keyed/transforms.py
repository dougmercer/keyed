"""Transform objects by rotations, translations, scale, and more."""

from __future__ import annotations

import math
from typing import Any, Callable, Literal, Self, cast

import cairo
import shapely
import shapely.affinity
from signified import Computed, HasValue, ReactiveValue, Signal, Variable, computed, unref

from .animation import Animation, AnimationType
from .constants import ALWAYS, LEFT, ORIGIN, Direction
from .easing import EasingFunctionT, cubic_in_out
from .types import GeometryT

__all__ = [
    "Transformable",
    "TransformControls",
    "affine_transform",
    "translate",
    "rotate",
    "scale",
    "move_to",
    "align_to",
    "lock_on",
    "shear",
    "stretch",
    "match_size",
    "next_to",
    "get_critical_point",
    "get_critical_point_now",
    "get_position_along_dim",
    "get_position_along_dim_now",
]


class Transformable:
    """A base class for things that have a geometry."""

    controls: TransformControls
    frame: Signal[int]
    _dependencies: list[Any]
    _cache: dict[str, Computed[Any]]

    def __init__(self, frame: Signal[int]) -> None:
        super().__init__()
        self.frame = frame
        self.controls = TransformControls(self)
        self._dependencies = []
        # self._dependencies = [self.controls.delta_x, self.controls.delta_y, self.controls.scale, self.controls.rotation]
        self._cache: dict[str, Computed[Any]] = {}

    def _get_cached_computed(self, name: str, factory: Callable[[], Computed[Any]]) -> Computed[Any]:
        """Get a cached computed value, creating it if it doesn't exist.

        This is intended to reduce the number of reactive values created when accessing methods like `geom`.

        Args:
            name: The name to cache the computed value under
            factory: A function that creates the computed value

        Returns:
            The cached computed value
        """
        if name not in self._cache:
            self._cache[name] = factory()
        return self._cache[name]

    def _invalidate_cache(self) -> Self:
        """Clear all cached computed values."""
        self._cache.clear()
        return self

    @property
    def _raw_geom_now(self) -> GeometryT:
        """Return the geometry at the current frame, before any transformations.

        Returns:
            The raw geometry, before any transformations, now.
        """
        ...

    @property
    def _raw_geom(self) -> Computed[GeometryT]:
        """Return a reactive value of the raw geometry."""
        return self._get_cached_computed("_raw_geom", lambda: Computed(lambda: self._raw_geom_now, self._dependencies))

    @property
    def geom(self) -> Computed[GeometryT]:
        """Return a reactive value of the transformed geometry."""
        return self._get_cached_computed(
            "geom", lambda: computed(affine_transform)(self._raw_geom, self.controls.matrix)
        )

    @property
    def geom_now(self) -> GeometryT:
        m = self.controls.matrix
        return affine_transform(unref(self._raw_geom), m.value)

    def apply_transform(self, matrix: ReactiveValue[cairo.Matrix]) -> Self:
        self.controls.matrix *= matrix
        # Invalidate cached geometry
        self._invalidate_cache()
        # self._cache.pop('geom', None)
        return self

    def rotate(
        self,
        amount: HasValue[float],
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
    ) -> Self:
        """Rotate the object.

        Args:
            amount: Amount to rotate by.
            start: The frame to start rotating.
            end: The frame to end rotating.
            easing: The easing function to use.
            center: The object around which to rotate.
            direction: The relative critical point of the center.

        Returns:
            self
        """
        center = center if center is not None else self.geom
        cx, cy = get_critical_point(center, direction)
        return self.apply_transform(rotate(start, end, amount, cx, cy, self.frame, easing))

    def scale(
        self,
        amount: HasValue[float],
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
    ) -> Self:
        """Scale the object.

        Args:
            amount: Amount to scale by.
            start: The frame to start scaling.
            end: The frame to end scaling.
            easing: The easing function to use.
            center: The object around which to rotate.
            direction: The relative critical point of the center.

        Returns:
            self
        """
        center = center if center is not None else self.geom
        cx, cy = get_critical_point(center, direction)
        return self.apply_transform(scale(start, end, amount, cx, cy, self.frame, easing))

    def translate(
        self,
        x: HasValue[float] = 0,
        y: HasValue[float] = 0,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
    ) -> Self:
        """Translate the object.

        Args:
            x: x offset.
            y: y offset.
            start: The frame to start translating.
            end: The frame to end translating.
            easing: The easing function to use.
        """
        return self.apply_transform(translate(start, end, x, y, self.frame, easing))

    def move_to(
        self,
        x: HasValue[float] | None = None,
        y: HasValue[float] | None = None,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
    ) -> Self:
        """Move object to absolute coordinates.

        Args:
            x: Destination x coordinate
            y: Destination y coordinate
            start: Starting frame, by default ALWAYS
            end: Ending frame, by default ALWAYS
            easing: Easing function, by default cubic_in_out

        Returns:
            Self
        """
        center = center if center is not None else self.geom
        cx, cy = get_critical_point(center, direction)
        self.apply_transform(move_to(start=start, end=end, x=x, y=y, cx=cx, cy=cy, frame=self.frame, easing=easing))
        return self

    def align_to(
        self,
        to: Transformable,
        start: int = ALWAYS,
        lock: int | None = None,
        end: int = ALWAYS,
        from_: ReactiveValue[GeometryT] | None = None,
        easing: EasingFunctionT = cubic_in_out,
        direction: Direction = ORIGIN,
        center_on_zero: bool = False,
    ) -> Self:
        """Align the object to another object.

        Args:
            to: The object to align to.
            start: Start of animation (begin aligning to the object).
            end: End of animation (finish aligning to the object at this frame, and then stay there).
            from_: Use this object as self when doing the alignment. Defaults to self. This is necessary
                for code animations. It is sometimes desirable to align, say, the top-left edge of one
                character in a TextSelection to the top-left of another character.

                This is a subtle feature that is missing in manim that made code animations difficult.
            easing: The easing function to use.
            direction: The critical point of to and from_to use for the alignment.
            center_on_zero: If true, align along the "0"-valued dimensions. Otherwise, only align to on non-zero
                directions. This is beneficial for, say, centering the object at the origin (which has
                a vector that consists of two zeros).

        Returns:
            self

        Todo:
            I'd like to get rid of center_on_zero.
        """
        from_ = from_ or self.geom
        lock = lock if lock is not None else end
        return self.apply_transform(
            align_to(
                to.geom,
                from_,
                frame=self.frame,
                start=start,
                lock=lock,
                end=end,
                ease=easing,
                direction=direction,
                center_on_zero=center_on_zero,
            )
        )

    def lock_on(
        self,
        target: Transformable,
        reference: ReactiveValue[GeometryT] | None = None,
        start: int = ALWAYS,
        end: int = -ALWAYS,
        direction: Direction = ORIGIN,
        x: bool = True,
        y: bool = True,
    ) -> Self:
        """Lock on to a target.

        Args:
            target: Object to lock onto
            reference: Measure from this object. This is useful for TextSelections, where you want to align
                to a particular character in the selection. Defaults to self.
            start: When to start locking on. Defaults to ALWAYS.
            end: When to end locking on. Defaults to -ALWAYS.
            x: If true, lock on in the x dimension.
            y: If true, lock on in the y dimension.
        """
        reference = reference or self.geom
        return self.apply_transform(
            lock_on(
                target=target.geom,
                reference=reference,
                frame=self.frame,
                start=start,
                end=end,
                direction=direction,
                x=x,
                y=y,
            )
        )

    def lock_on2(
        self,
        target: Transformable,
        reference: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
        x: bool = True,
        y: bool = True,
    ) -> Self:
        """Lock on to a target.

        Args:
            target: Object to lock onto
            reference: Measure from this object. This is useful for TextSelections, where you want to align
                to a particular character in the selection. Defaults to self.
            x: If true, lock on in the x dimension.
            y: if true, lock on in the y dimension.
        """
        reference = reference or self.geom
        return self.apply_transform(
            align_now(
                target=target.geom,
                reference=reference,
                direction=direction,
                x=x,
                y=y,
            )
        )

    def shear(
        self,
        angle_x: HasValue[float] = 0,
        angle_y: HasValue[float] = 0,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
    ) -> Self:
        """Shear the object.

        Args:
            angle_x: Angle (in degrees) to shear by along x direction.
            angle_y: Angle (in degrees) to shear by along x direction.
            start: The frame to start scaling.
            end: The frame to end scaling.
            easing: The easing function to use.
            center: The object around which to rotate.

        Returns:
            self
        """
        center = center if center is not None else self.geom
        cx, cy = get_critical_point(center, ORIGIN)
        return self.apply_transform(
            shear(
                start=start,
                end=end,
                angle_x=angle_x,
                angle_y=angle_y,
                cx=cx,
                cy=cy,
                frame=self.frame,
                ease=easing,
            )
        )

    def stretch(
        self,
        scale_x: HasValue[float] = 1,
        scale_y: HasValue[float] = 1,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
    ) -> Self:
        """Stretch the object.

        Args:
            scale_x: Amount to scale by in x direction.
            scale_y: Amount to scale by in y direction.
            start: The frame to start scaling.
            end: The frame to end scaling.
            easing: The easing function to use.
            center: The object around which to rotate.
            direction: The relative critical point of the center.

        Returns:
            self
        """
        center = center if center is not None else self.geom
        cx, cy = get_critical_point(center, direction)
        return self.apply_transform(
            stretch(
                start=start,
                end=end,
                scale_x=scale_x,
                scale_y=scale_y,
                cx=cx,
                cy=cy,
                frame=self.frame,
                ease=easing,
            )
        )

    def match_size(
        self,
        other: Transformable,
        match_x: bool = True,
        match_y: bool = True,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
    ) -> Self:
        center_ = center if center is not None else self.geom
        cx, cy = get_critical_point(center_, direction)  # type: ignore[argument]
        matrix = match_size(
            start=start,
            end=end,
            match_x=match_x,
            match_y=match_y,
            target_width=other.width,
            target_height=other.height,
            original_width=self.width,
            original_height=self.height,
            cx=cx,
            cy=cy,
            frame=self.frame,
            ease=easing,
        )
        self.apply_transform(matrix)
        return self

    def next_to(
        self,
        to: Transformable,
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        offset: HasValue[float] = 10.0,
        direction: Direction = LEFT,
    ) -> Self:
        """Align the object to another object.

        Args:
            to: The object to align to.
            start: Start of animation (begin aligning to the object).
            end: End of animation (finish aligning to the object at this frame, and then stay there).
            easing: The easing function to use.
            offset: Distance between objects (in pixels).
            direction: The critical point of to and from_to use for the alignment.

        Returns:
            self
        """
        self_x, self_y = get_critical_point(self.geom, -1 * direction)
        target_x, target_y = get_critical_point(to.geom, direction)
        matrix = next_to(
            start=start,
            end=end,
            target_x=target_x,
            target_y=target_y,
            self_x=self_x,
            self_y=self_y,
            direction=direction,
            offset=offset,
            ease=easing,
            frame=self.frame,
        )
        return self.apply_transform(matrix)

    @property
    def down(self) -> Computed[float]:
        return self._get_cached_computed("down", lambda: self.geom.bounds[3])

    @property
    def up(self) -> Computed[float]:
        return self._get_cached_computed("up", lambda: self.geom.bounds[1])

    @property
    def left(self) -> Computed[float]:
        return self._get_cached_computed("left", lambda: self.geom.bounds[0])

    @property
    def right(self) -> Computed[float]:
        return self._get_cached_computed("right", lambda: self.geom.bounds[2])

    @property
    def width(self) -> Computed[float]:
        return self._get_cached_computed("width", lambda: self.right - self.left)

    @property
    def height(self) -> Computed[float]:
        return self._get_cached_computed("height", lambda: self.down - self.up)

    @property
    def center_x(self) -> Computed[float]:
        return self._get_cached_computed("center_x", lambda: (self.left + self.right) / 2)

    @property
    def center_y(self) -> Computed[float]:
        return self._get_cached_computed("center_y", lambda: (self.up + self.down) / 2)


class TransformControls:
    """Control how transforms are applied to the object.

    Args:
        obj: A reference to the object being transformed.

    Todo:
        Passing obj seems a little awkward.
    """

    def __init__(self, obj: Transformable) -> None:
        super().__init__()
        self.rotation = Signal(0.0)
        self.scale = Signal(1.0)
        self.delta_x = Signal(0.0)
        self.delta_y = Signal(0.0)
        self.matrix: ReactiveValue[cairo.Matrix] = Signal(cairo.Matrix())
        self.obj = obj

    def base_matrix(self) -> Computed[cairo.Matrix]:
        """Get the base transform matrix.

        This applies only the translations, rotations, and scale from potentially
        animated attributes on the object's controls. applying on the rotation,
        translations matrix at the specified frame.

        Returns:
            The transform matrix, before any transformations.
        """
        return computed(base_transform_matrix)(
            self.obj._raw_geom, self.delta_x, self.delta_y, self.rotation, self.scale
        )


def base_transform_matrix(
    _raw_geom: GeometryT, delta_x: float, delta_y: float, rotation: float, scale: float
) -> cairo.Matrix:
    matrix = cairo.Matrix()
    bounds = _raw_geom.bounds

    pivot_x = (bounds[2] - bounds[0]) / 2
    pivot_y = (bounds[3] - bounds[1]) / 2

    # Translate
    if delta_x or delta_y:
        matrix.translate(delta_x, delta_y)

    # Rotate
    radians = math.radians(rotation)
    if radians:
        matrix.translate(pivot_x, pivot_y)
        matrix.rotate(radians)
        matrix.translate(-pivot_x, -pivot_y)

    # Scale
    if scale:
        matrix.translate(pivot_x, pivot_y)
        matrix.scale(scale, scale)
        matrix.translate(-pivot_x, -pivot_y)
    return matrix


def lock_on(
    target: ReactiveValue[GeometryT],
    reference: ReactiveValue[GeometryT],
    frame: ReactiveValue[int],
    start: int = ALWAYS,
    end: int = -ALWAYS,
    direction: Direction = ORIGIN,
    x: bool = True,
    y: bool = True,
) -> Computed[cairo.Matrix]:
    """Lock one object's position onto another object.

    Args:
        target: The object to lock onto.
        reference: The object to use as reference for self when locking on. This is useful, when
                   the overall object, self, is large, and you want to more precisely lock onto a point.
        frame: The reactive value for the scene's frame counter.
        start: The first frame to begin translating.
        end: The final frame to end translating.
        direction: The position in the 2D unit square in the geometry that you want to retrieve. Defaults to the center, ORIGIN.
        x: If true, lock on in the x dimension.
        y: If true, lock on in the y dimension.
    """

    to_x = get_position_along_dim(target, dim=0, direction=direction)
    to_y = get_position_along_dim(target, dim=1, direction=direction)
    from_x = get_position_along_dim(reference, dim=0, direction=direction)
    from_y = get_position_along_dim(reference, dim=1, direction=direction)
    delta_x = to_x - from_x
    delta_y = to_y - from_y

    # TODO - Is it possible to have an at() method for Computed objects?
    assert isinstance(frame, Signal)
    with frame.at(end):
        dx_end = delta_x.value
        dy_end = delta_y.value

    @computed
    def f(delta_x: float, delta_y: float, frame: int) -> cairo.Matrix:
        matrix = cairo.Matrix()
        if frame < start:
            return matrix
        if frame < end:
            dx = delta_x
            dy = delta_y
        else:
            dx = dx_end
            dy = dy_end
        matrix.translate(dx if x else 0, dy if y else 0)
        return matrix

    return f(delta_x, delta_y, frame)


def align_now(
    target: ReactiveValue[GeometryT],
    reference: ReactiveValue[GeometryT],
    direction: Direction = ORIGIN,
    x: bool = True,
    y: bool = True,
) -> Computed[cairo.Matrix]:
    to_x, to_y = get_critical_point(target, direction=direction)
    from_x, from_y = get_critical_point(reference, direction=direction)
    dx = to_x - from_x if x else 0
    dy = to_y - from_y if y else 0

    @computed
    def f(dx: float, dy: float) -> cairo.Matrix:
        matrix = cairo.Matrix()
        matrix.translate(dx if x else 0, dy if y else 0)
        return matrix

    return f(dx, dy)


def align_to(
    to: ReactiveValue[GeometryT],
    from_: ReactiveValue[GeometryT],
    frame: Signal[int],
    start: int = ALWAYS,
    lock: int = ALWAYS,
    end: int = ALWAYS,
    ease: EasingFunctionT = cubic_in_out,
    direction: Direction = ORIGIN,
    center_on_zero: bool = False,
) -> Computed[cairo.Matrix]:
    to_x, to_y = get_critical_point(to, direction)
    from_x, from_y = get_critical_point(from_, direction)
    with frame.at(end):
        last_x = (to_x - from_x).value
        last_y = (to_y - from_y).value

    @computed
    def fx(to_x: float, from_x: float, frame: int) -> float:
        if center_on_zero or direction[0] != 0:
            return to_x - from_x if frame < end else last_x
        return 0

    delta_x = fx(to_x, from_x, frame)

    @computed
    def fy(to_y: float, from_y: float, frame: int) -> float:
        if center_on_zero or direction[1] != 0:
            return to_y - from_y if frame < end else last_y
        return 0

    delta_y = fy(to_y, from_y, frame)

    return translate(start, lock, delta_x, delta_y, frame, ease=ease)


def affine_transform(geom: GeometryT, matrix: cairo.Matrix | None) -> GeometryT:
    """Apply the cairo.Matrix as shapely affine transform to the provided geometry.

    Args:
        geom: Geometry to transform
        matrix: Transformation matrix

    Returns:
        The transformed geometry.
    """
    if matrix is not None:
        transform_params = [matrix.xx, matrix.xy, matrix.yx, matrix.yy, matrix.x0, matrix.y0]
        return shapely.affinity.affine_transform(geom, transform_params)
    else:
        return geom


def translate(
    start: int,
    end: int,
    delta_x: HasValue[float],
    delta_y: HasValue[float],
    frame: ReactiveValue[int],
    ease: EasingFunctionT = cubic_in_out,
) -> Computed[cairo.Matrix]:
    """Translate matrix.

    Args:
        start: Start frame
        end: End frame
        delta_x: Amount to translate in the x direction.
        delta_y: Amount to translate in the y direction.
        frame: Frame reactive value.
        ease: Easing function.

    Returns:
        The time-varying transformation matrix.
    """
    if start == end:
        # Do not need to animate/ease.
        x = delta_x
        y = delta_y
    else:
        # Only create animations if Variable or non-zero
        x = Animation(start, end, 0, delta_x, ease)(0, frame) if isinstance(delta_x, Variable) or delta_x != 0 else 0
        y = Animation(start, end, 0, delta_y, ease)(0, frame) if isinstance(delta_y, Variable) or delta_y != 0 else 0

    @computed
    def f(x: float, y: float) -> cairo.Matrix:
        matrix = cairo.Matrix()
        matrix.translate(x, y)
        return matrix

    return f(x, y)


def move_to(
    start: int,
    end: int,
    x: HasValue[float] | None,
    y: HasValue[float] | None,
    cx: HasValue[float],
    cy: HasValue[float],
    frame: ReactiveValue[int],
    easing: EasingFunctionT = cubic_in_out,
) -> Computed[cairo.Matrix]:
    """Create a transformation matrix that moves an object to absolute coordinates.

    Args:
        start: Starting frame of the movement.
        end: Ending frame of the movement.
        x: Target x coordinate. If None, ignore.
        y: Target y coordinate. If None, ignore.
        frame: Current frame.
        easing: Easing function for the movement.

    Returns:
        matrix: Transform matrix for the movement
    """

    @computed
    def compute_matrix(x: float | None, y: float | None, cx: float, cy: float) -> cairo.Matrix:
        matrix = cairo.Matrix()
        matrix.translate(x - cx if x is not None else 0, y - cy if y is not None else 0)
        return matrix

    if start == end:
        return compute_matrix(x, y, cx, cy)
    else:
        animated_x = Animation(start, end, cx, x, easing, AnimationType.ABSOLUTE)(cx, frame) if x is not None else cx
        animated_y = Animation(start, end, cy, y, easing, AnimationType.ABSOLUTE)(cy, frame) if y is not None else cy
        return compute_matrix(animated_x, animated_y, cx, cy)


def rotate(
    start: int,
    end: int,
    amount: HasValue[float],
    cx: HasValue[float],
    cy: HasValue[float],
    frame: ReactiveValue[int],
    ease: EasingFunctionT = cubic_in_out,
) -> Computed[cairo.Matrix]:
    """Rotate matrix.

    Args:
        start: Start frame
        end: End frame
        amount: Amount to rotate by
        cx: Center x
        cy: Center y
        frame: Frame reactive value.
        ease: Easing function.

    Returns:
        The time-varying transformation matrix.
    """
    magnitude = Animation(start, end, 0, amount, ease, animation_type=AnimationType.ADDITIVE)(0, frame)

    @computed
    def f(magnitude: float, cx: float, cy: float) -> cairo.Matrix:
        matrix = cairo.Matrix()
        matrix.translate(cx, cy)
        matrix.rotate(math.radians(magnitude))
        matrix.translate(-cx, -cy)
        return matrix

    return f(magnitude, cx, cy)


def scale(
    start: int,
    end: int,
    amount: HasValue[float],
    cx: HasValue[float],
    cy: HasValue[float],
    frame: ReactiveValue[int],
    ease: EasingFunctionT = cubic_in_out,
) -> Computed[cairo.Matrix]:
    """Scale matrix.

    Args:
        start: Start frame
        end: End frame
        amount: Amount to scale by
        cx: Center x
        cy: Center y
        frame: Frame reactive value.
        ease: Easing function.

    Returns:
        The time-varying transformation matrix.
    """
    magnitude = Animation(start, end, 1, amount, ease, animation_type=AnimationType.MULTIPLICATIVE)(1, frame)

    return _scale(magnitude, magnitude, cx, cy)


def stretch(
    start: int,
    end: int,
    scale_x: HasValue[float],
    scale_y: HasValue[float],
    cx: HasValue[float],
    cy: HasValue[float],
    frame: ReactiveValue[int],
    ease: EasingFunctionT = cubic_in_out,
) -> Computed[cairo.Matrix]:
    """Create a non-uniform scaling transformation matrix.

    This transformation allows independent scaling in x and y directions, centered
    around a specified point. Unlike the basic scale transform, this allows
    for effects like squash and stretch animation.

    Args:
        start: Starting frame for the animation
        end: Ending frame for the animation
        scale_x: Scale factor for x-axis
        scale_y: Scale factor for y-axis
        cx: X coordinate of the center point
        cy: Y coordinate of the center point
        frame: Current frame
        ease: Easing function to apply

    Returns:
        A computed transformation matrix
    """
    # Animate both scale factors independently
    sx = Animation(start, end, 1, scale_x, ease, AnimationType.MULTIPLICATIVE)(1, frame)
    sy = Animation(start, end, 1, scale_y, ease, AnimationType.MULTIPLICATIVE)(1, frame)

    return _scale(sx, sy, cx, cy)


def shear(
    start: int,
    end: int,
    angle_x: HasValue[float],
    angle_y: HasValue[float],
    cx: HasValue[float],
    cy: HasValue[float],
    frame: ReactiveValue[int],
    ease: EasingFunctionT = cubic_in_out,
) -> Computed[cairo.Matrix]:
    """Create a shear transformation matrix.

    A shear transformation slants the shape by a specified amount in either the
    x or y direction.

    Args:
        start: Starting frame for the animation
        end: Ending frame for the animation
        angle_x: Angle in degrees to shear along x-axis
        angle_y: Angle in degrees to shear along y-axis
        cx: X coordinate of the center point
        cy: Y coordinate of the center point
        frame: Current frame
        ease: Easing function to apply

    Returns:
        A computed transformation matrix
    """
    tan = computed(lambda angle: math.tan(math.radians(angle)))
    x_magnitude = Animation(start, end, 0, tan(angle_x), ease)(0, frame)
    y_magnitude = Animation(start, end, 0, tan(angle_y), ease)(0, frame)

    @computed
    def f(x_mag: float, y_mag: float, cx: float, cy: float) -> cairo.Matrix:
        matrix = cairo.Matrix()
        matrix.translate(cx, cy)
        matrix = cast(cairo.Matrix, cairo.Matrix(1, y_mag, x_mag, 1, 0, 0) * matrix)  # type: ignore
        matrix.translate(-cx, -cy)
        return matrix

    return f(x_magnitude, y_magnitude, cx, cy)


def match_size(
    start: int,
    end: int,
    target_width: HasValue[float],
    target_height: HasValue[float],
    original_width: HasValue[float],
    original_height: HasValue[float],
    cx: HasValue[float],
    cy: HasValue[float],
    frame: ReactiveValue[int],
    match_x: bool = True,
    match_y: bool = True,
    ease: EasingFunctionT = cubic_in_out,
) -> Computed[cairo.Matrix]:
    """Create a transformation matrix that resizes an object to match target dimensions.

    Args:
        start: Starting frame for the animation
        end: Ending frame for the animation
        target_width: Target width to match
        target_height: Target height to match
        original_width: Current width of the object
        original_height: Current height of the object
        cx: X coordinate of the center point
        cy: Y coordinate of the center point
        frame: Current frame
        match_x: Whether to match the width
        match_y: Whether to match the height
        ease: Easing function to apply

    Returns:
        A computed transformation matrix
    """
    # Calculate scale factors for each dimension
    scale_x = target_width / original_width if match_x else 1.0
    scale_y = target_height / original_height if match_y else 1.0

    # Animate both scale factors independently
    sx = Animation(start, end, 1, scale_x, ease, AnimationType.MULTIPLICATIVE)(1, frame)
    sy = Animation(start, end, 1, scale_y, ease, AnimationType.MULTIPLICATIVE)(1, frame)

    return _scale(sx, sy, cx, cy)


def next_to(
    start: int,
    end: int,
    target_x: HasValue[float],
    target_y: HasValue[float],
    self_x: HasValue[float],
    self_y: HasValue[float],
    direction: Direction,
    offset: HasValue[float],
    frame: ReactiveValue[int],
    ease: EasingFunctionT = cubic_in_out,
) -> Computed[cairo.Matrix]:
    """Create a transformation matrix that positions an object next to a target point.

    Args:
        start: Starting frame for the animation
        end: Ending frame for the animation
        target_x: X coordinate of the reference point on the target
        target_y: Y coordinate of the reference point on the target
        self_x: X coordinate of the reference point on self
        self_y: Y coordinate of the reference point on self
        direction: Direction vector indicating the positioning direction
        offset: Distance between the objects along the direction vector
        frame: Current frame
        ease: Easing function to apply

    Returns:
        A computed transformation matrix
    """
    new_x = target_x + direction.x * offset
    new_y = target_y - direction.y * offset  # negative, because Top Left = (0, 0) coordinate system

    # Calculate the translation amount to the new position
    dx = new_x - self_x
    dy = new_y - self_y

    # Animate the translation
    animated_dx = Animation(start, end, 0, dx, ease)(0, frame)
    animated_dy = Animation(start, end, 0, dy, ease)(0, frame)

    @computed
    def f(dx: float, dy: float) -> cairo.Matrix:
        matrix = cairo.Matrix()
        matrix.translate(dx, dy)
        return matrix

    return f(animated_dx, animated_dy)


def get_position_along_dim_now(
    geom: GeometryT,
    direction: Direction = ORIGIN,
    dim: Literal[0, 1] = 0,
) -> float:
    """Get value of a position along a dimension at the current frame.

    Args:
        geom: A Geometry
        direction: The position in the 2D unit square in the geometry that you want to retrieve. Defaults
            to ORIGIN (center of the object).
        dim: Dimension to query, where 0 is the horizontal direction and 1 is the vertical
            direction. Defaults to 0.

    Returns:
        Position along dimension.
    """
    assert -1 <= direction[dim] <= 1
    bounds = geom.bounds
    magnitude = 0.5 * (1 - direction[dim]) if dim == 0 else 0.5 * (direction[dim] + 1)
    return magnitude * bounds[dim] + (1 - magnitude) * bounds[dim + 2]


def get_position_along_dim(
    geom: ReactiveValue[GeometryT],
    direction: Direction = ORIGIN,
    dim: Literal[0, 1] = 0,
) -> Computed[float]:
    return computed(get_position_along_dim_now)(geom, direction, dim)


def get_critical_point_now(geom: GeometryT, direction: Direction = ORIGIN) -> tuple[float, float]:
    """Get value of a position along both dimensions at the current frame.

    Args:
        direction: The position in the 2D unit square in the geometry that you want to retrieve. Defaults
                   to ORIGIN (center of the object).

    Returns:
        The critical point as a tuple of the x and y directions.
    """
    x = get_position_along_dim_now(geom, direction, dim=0)
    y = get_position_along_dim_now(geom, direction, dim=1)
    return x, y


def get_critical_point(
    geom: HasValue[GeometryT], direction: Direction = ORIGIN
) -> tuple[Computed[float], Computed[float]]:
    """Get value of a position along both dimensions at the current frame.

    Args:
        direction: The position in the 2D unit square in the geometry that you want to retrieve. Defaults
                   to ORIGIN (center of the object).

    Returns:
        The critical point as a tuple of reactive values in the x and y directions.
    """
    x = computed(get_position_along_dim_now)(geom, direction, dim=0)
    y = computed(get_position_along_dim_now)(geom, direction, dim=1)
    return x, y


@computed
def _scale(sx: float, sy: float, cx: float, cy: float) -> cairo.Matrix:
    matrix = cairo.Matrix()
    matrix.translate(cx, cy)
    matrix.scale(sx, sy)
    matrix.translate(-cx, -cy)
    return matrix
