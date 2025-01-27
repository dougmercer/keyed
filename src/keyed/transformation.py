"""Transform objects by rotations, translations, scale, and more."""

from __future__ import annotations

import math
from typing import Any, Literal, Protocol, Self, runtime_checkable

import cairo
import shapely
import shapely.affinity
from signified import Computed, HasValue, ReactiveValue, Signal, Variable, computed, unref

from .animation import Animation, AnimationType
from .constants import ALWAYS, ORIGIN, Direction
from .easing import EasingFunctionT, cubic_in_out
from .helpers import Freezeable
from .types import GeometryT


@runtime_checkable
class Transformable(Protocol):
    """A base class for things that have a geometry."""

    controls: TransformControls
    frame: Signal[int]
    _geom_cached: Computed[GeometryT] | None
    _raw_geom_cached: Computed[GeometryT] | None
    _dependencies: list[Any]

    def __init__(self, frame: Signal[int]) -> None:
        super().__init__()
        self.frame = frame
        self.controls = TransformControls(self)
        self._dependencies = [self.controls.delta_x, self.controls.delta_y, self.controls.scale, self.controls.rotation]
        self._geom_cached: Computed[GeometryT] | None = None
        self._raw_geom_cached: Computed[GeometryT] | None = None

    @property
    def raw_geom_now(self) -> GeometryT:
        """Return the geometry at the current frame, before any transformations.

        Returns:
            The raw geometry, before any transformations, now.
        """
        ...

    @property
    def raw_geom(self) -> Computed[GeometryT]:
        if self._raw_geom_cached is None:
            self._raw_geom_cached = Computed(lambda: self.raw_geom_now, self._dependencies)
        return self._raw_geom_cached

    @property
    def geom(self) -> Computed[GeometryT]:
        """Return the geometry at the current frame.

        Returns:
            A reactive value of the geometry.
        """
        # Check if there is a value in the cache
        if self._geom_cached is None:
            # Bind to the current matrix.
            self._geom_cached = computed(affine_transform)(self.raw_geom, self.controls.matrix)
        return self._geom_cached

    @property
    def geom_now(self) -> GeometryT:
        m = self.controls.matrix
        return affine_transform(unref(self.raw_geom), m.value)

    def left_now(self, with_transforms: bool = True) -> float:
        """Get the left critical point.

        Args:
            with_transforms : Retrieve the coordinate after all transforms if True. Otherwise, use raw_geom.

        Returns:
            The left critical point.
        """
        g = self.geom_now if with_transforms else self.raw_geom_now
        return g.bounds[0]

    def right_now(self, with_transforms: bool = True) -> float:
        """Get the right critical point.

        Args:
            with_transforms: Retrieve the coordinate after all transforms if True. Otherwise, use raw_geom.

        Returns:
            The right critical point.
        """
        g = self.geom_now if with_transforms else self.raw_geom_now
        return g.bounds[2]

    def down_now(self, with_transforms: bool = True) -> float:
        """Get the down critical point.

        Args:
            with_transforms: Retrieve the coordinate after all transforms if True. Otherwise, use raw_geom.

        Returns:
            The down critical point.
        """
        g = self.geom_now if with_transforms else self.raw_geom_now
        return g.bounds[1]

    def up_now(self, with_transforms: bool = True) -> float:
        """Get the up critical point.

        Args:
            with_transforms: Retrieve the coordinate after all transforms if True. Otherwise, use raw_geom.

        Returns:
            The up critical point.
        """
        g = self.geom_now if with_transforms else self.raw_geom_now
        return g.bounds[3]

    def width_now(self, with_transforms: bool = True) -> float:
        return self.right_now(with_transforms) - self.left_now(with_transforms)

    def height_now(self, with_transforms: bool = True) -> float:
        return self.up_now(with_transforms) - self.down_now(with_transforms)

    def apply_transform(self, matrix: ReactiveValue[cairo.Matrix]) -> Self:
        self.controls.matrix *= matrix
        # Invalidate cached geometry
        self._geom_cached = None
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
        x: HasValue[float],
        y: HasValue[float],
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
        x: HasValue[float],
        y: HasValue[float],
        start: int = ALWAYS,
        end: int = ALWAYS,
        easing: EasingFunctionT = cubic_in_out,
        center: ReactiveValue[GeometryT] | None = None,
        direction: Direction = ORIGIN,
    ) -> Self:
        """Move object to absolute coordinates.

        Parameters
        ----------
        x : HasValue[float]
            Target x coordinate
        y : HasValue[float]
            Target y coordinate
        start : int, optional
            Starting frame, by default ALWAYS
        end : int, optional
            Ending frame, by default ALWAYS
        easing : EasingFunctionT, optional
            Easing function, by default cubic_in_out

        Returns
        -------
        Self
            The transformed object
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

    # def left_now(self, with_transforms: bool = True) -> float:
    #     return get_critical_point_now(self.geom_now if with_transforms else self.raw_geom_now, LEFT)[0]

    # def right_now(self, with_transforms: bool = True) -> float:
    #     return get_critical_point_now(self.geom_now if with_transforms else self.raw_geom_now, RIGHT)[0]

    # def down_now(self, with_transforms: bool = True) -> float:
    #     return get_critical_point_now(self.geom_now if with_transforms else self.raw_geom_now, DOWN)[1]

    # def up_now(self, with_transforms: bool = True) -> float:
    #     return get_critical_point_now(self.geom_now if with_transforms else self.raw_geom_now, UP)[1]

    def down(self, with_transforms: bool = True) -> Computed[float]:
        return (self.geom if with_transforms else self.raw_geom).bounds[1]

    def up(self, with_transforms: bool = True) -> Computed[float]:
        return (self.geom if with_transforms else self.raw_geom).bounds[3]

    def left(self, with_transforms: bool = True) -> Computed[float]:
        return (self.geom if with_transforms else self.raw_geom).bounds[0]

    def right(self, with_transforms: bool = True) -> Computed[float]:
        return (self.geom if with_transforms else self.raw_geom).bounds[2]

    def width(self, with_transforms: bool = True) -> Computed[float]:
        bounds = (self.geom if with_transforms else self.raw_geom).bounds
        return bounds[2] - bounds[0]

    def height(self, with_transforms: bool = True) -> Computed[float]:
        bounds = (self.geom if with_transforms else self.raw_geom).bounds
        return bounds[3] - bounds[1]

    def center_x(self, with_transforms: bool = True) -> Computed[float]:
        return (self.left(with_transforms) + self.right(with_transforms)) / 2

    def center_y(self, with_transforms: bool = True) -> Computed[float]:
        return (self.up(with_transforms) + self.down(with_transforms)) / 2


class TransformControls(Freezeable):
    """Control how transforms are applied to the object.

    Args:
        obj: A reference to the object being transformed.

    Todo:
        Passing obj seems a little awkward.
    """

    animatable_properties = ("rotation", "scale", "delta_x", "delta_y")

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
        return computed(base_transform_matrix)(self.obj.raw_geom, self.delta_x, self.delta_y, self.rotation, self.scale)


def base_transform_matrix(
    raw_geom: GeometryT, delta_x: float, delta_y: float, rotation: float, scale: float
) -> cairo.Matrix:
    matrix = cairo.Matrix()
    bounds = raw_geom.bounds

    # TODO Consider translating by this initially to center it?
    # or could just always draw centered... (e.g., rectangle)
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
    x: HasValue[float],
    y: HasValue[float],
    cx: HasValue[float],
    cy: HasValue[float],
    frame: ReactiveValue[int],
    easing: EasingFunctionT = cubic_in_out,
) -> Computed[cairo.Matrix]:
    """Create a transformation matrix that moves an object to absolute coordinates.

    Parameters
    ----------
    start : int
        Starting frame of the movement
    end : int
        Ending frame of the movement
    x : HasValue[float]
        Target x coordinate
    y : HasValue[float]
        Target y coordinate
    frame : ReactiveValue[int]
        Current frame
    easing : EasingFunctionT
        Easing function for the movement

    Returns
    -------
    Computed[cairo.Matrix]
        Transform matrix for the movement
    """

    @computed
    def compute_matrix(x: float, y: float, cx: float, cy: float) -> cairo.Matrix:
        matrix = cairo.Matrix()
        matrix.translate(x - cx, y - cy)
        return matrix

    if start == end:
        return compute_matrix(x, y, cx, cy)
    else:
        animated_x = Animation(start, end, cx, x, easing, AnimationType.ABSOLUTE)(cx, frame)
        animated_y = Animation(start, end, cy, y, easing, AnimationType.ABSOLUTE)(cy, frame)
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

    @computed
    def f(magnitude: float, cx: float, cy: float) -> cairo.Matrix:
        matrix = cairo.Matrix()
        matrix.translate(cx, cy)
        matrix.scale(magnitude, magnitude)
        matrix.translate(-cx, -cy)
        return matrix

    return f(magnitude, cx, cy)


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
