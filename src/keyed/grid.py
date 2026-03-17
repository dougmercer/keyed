from contextlib import contextmanager
from dataclasses import dataclass
from typing import Self, Sequence

import cairo
import shapely
from signified import Computed, HasValue, ReactiveValue, Signal, as_signal, computed, unref

from .base import Base
from .color import Color, as_color
from .constants import ORIGIN, Direction
from .geometry import Geometry
from .group import Group
from .scene import Scene
from .transforms import affine_transform

__all__ = ["Grid"]


@dataclass
class _CellStyle:
    color: HasValue[Color]
    alpha: HasValue[float] = 1.0


class Grid(Base):
    """A grid/table you can put stuff in.

    Args:
        scene: The scene to which the grid belongs.
        width: Total width of the grid.
        height: Total height of the grid.
        rows: Number of rows in the grid.
        cols: Number of columns in the grid.
        color: Color of the grid lines.
        line_width: Width of the grid lines.
        x: X-coordinate of the center.
        y: Y-coordinate of the center
        alpha: The opacity of the grid.
        dash: Optional dash pattern for grid lines.
        operator: Cairo compositing operator.
        show_border: Whether to show the external border.
        show_inner_lines: Whether to show internal grid lines.

    Tip:
        Animate the grid *after* everything has been added to it.

    Experimental:
        This isn't particularly well tested.
    """

    def __init__(
        self,
        width: HasValue[float] = 400,
        height: HasValue[float] = 400,
        rows: HasValue[int] = 4,
        cols: HasValue[int] = 4,
        color: tuple[float, float, float] | HasValue[Color] = (1, 1, 1),
        line_width: HasValue[float] = 1,
        x: HasValue[float] | None = None,
        y: HasValue[float] | None = None,
        alpha: HasValue[float] = 1,
        dash: tuple[Sequence[float], float] | None = None,
        operator: cairo.Operator = cairo.OPERATOR_OVER,
        show_border: bool = True,
        show_inner_lines: bool = True,
        scene: Scene | None = None,
    ):
        super().__init__(scene)
        self.ctx = self.scene.get_context()

        self._width = as_signal(width)
        self._height = as_signal(height)
        self.rows = as_signal(rows)
        self.cols = as_signal(cols)
        self.color = as_color(color)
        self.line_width = as_signal(line_width)
        self.alpha = as_signal(alpha)
        self.dash = dash
        self.operator = operator
        self.show_border = show_border
        self.show_inner_lines = show_inner_lines

        self.x = x if x is not None else self.scene.nx(0.5)
        self.y = y if y is not None else self.scene.ny(0.5)

        self.controls.delta_x.value = self.x
        self.controls.delta_y.value = self.y

        assert isinstance(self.controls.matrix, Signal)
        self.controls.matrix.value = self.controls.base_matrix()

        self._cell_styles: dict[tuple[int, int], _CellStyle] = {}
        self.content: Group = Group()

    def _validate_grid_dimensions(self, rows: int, cols: int) -> None:
        if rows <= 0:
            raise ValueError(f"Grid must have at least 1 row, got {rows}.")
        if cols <= 0:
            raise ValueError(f"Grid must have at least 1 column, got {cols}.")

    def _validate_cell_index(
        self,
        row: int,
        col: int,
        *,
        rows: int | None = None,
        cols: int | None = None,
    ) -> None:
        rows_ = unref(self.rows) if rows is None else rows
        cols_ = unref(self.cols) if cols is None else cols
        self._validate_grid_dimensions(rows_, cols_)

        if not 0 <= row < rows_:
            raise ValueError(f"Row index {row} is out of bounds for a grid with {rows_} rows.")
        if not 0 <= col < cols_:
            raise ValueError(f"Column index {col} is out of bounds for a grid with {cols_} columns.")

    @contextmanager
    def _style(self):
        """Set up the drawing style for the grid."""
        try:
            self.ctx.save()

            # Set line properties
            self.ctx.set_operator(self.operator)
            self.ctx.set_line_width(unref(self.line_width))
            self.ctx.set_source_rgba(*unref(self.color).rgb, unref(self.alpha))

            # Set dash pattern if specified
            if self.dash is not None:
                self.ctx.set_dash(*self.dash)

            yield
        finally:
            self.ctx.restore()

    def draw(self) -> None:
        """Draw the grid using Cairo primitives."""
        # First draw any styled cells
        self._draw_styled_cells()

        # Then draw the grid lines
        with self._style():
            self.ctx.transform(self.controls.matrix.value)

            width = unref(self._width)
            height = unref(self._height)
            rows = unref(self.rows)
            cols = unref(self.cols)
            self._validate_grid_dimensions(rows, cols)

            start_x = -width / 2
            start_y = -height / 2
            cell_width = width / cols
            cell_height = height / rows

            if self.show_border:
                self.ctx.new_path()
                self.ctx.rectangle(start_x, start_y, width, height)
                self.ctx.stroke()

            if self.show_inner_lines:
                for i in range(1, rows):
                    y_pos = start_y + i * cell_height
                    self.ctx.new_path()
                    self.ctx.move_to(start_x, y_pos)
                    self.ctx.line_to(start_x + width, y_pos)
                    self.ctx.stroke()

                for j in range(1, cols):
                    x_pos = start_x + j * cell_width
                    self.ctx.new_path()
                    self.ctx.move_to(x_pos, start_y)
                    self.ctx.line_to(x_pos, start_y + height)
                    self.ctx.stroke()

        self.content.draw()

    def apply_transform(self, matrix: ReactiveValue[cairo.Matrix]) -> Self:
        self.content.apply_transform(matrix)
        super().apply_transform(matrix)
        return self

    def _draw_styled_cells(self) -> None:
        """Draw all styled cells."""
        # Exit early if no styled cells
        if not self._cell_styles:
            return

        # Get current values
        width = unref(self._width)
        height = unref(self._height)
        rows = unref(self.rows)
        cols = unref(self.cols)
        self._validate_grid_dimensions(rows, cols)

        # Calculate cell dimensions
        cell_width = width / cols
        cell_height = height / rows

        start_x = -width / 2
        start_y = -height / 2

        with self._style():
            self.ctx.transform(self.controls.matrix.value)

            grid_alpha = unref(self.alpha)

            for (row, col), style in self._cell_styles.items():
                self._validate_cell_index(row, col, rows=rows, cols=cols)

                x0 = start_x + col * cell_width
                y0 = start_y + row * cell_height

                rgb = unref(style.color).rgb
                alpha = grid_alpha * unref(style.alpha)

                self.ctx.new_path()
                self.ctx.set_source_rgba(*rgb, alpha)
                self.ctx.rectangle(x0, y0, cell_width, cell_height)
                self.ctx.fill()

    @property
    def _raw_geom_now(self) -> shapely.Polygon:
        """Return the geometry before any transformations."""
        width = self._width.value
        height = self._height.value

        start_x = -width / 2
        start_y = -height / 2

        return shapely.box(start_x, start_y, start_x + width, start_y + height)

    def get_cell_bounds(
        self, row: int, col: int
    ) -> tuple[Computed[float], Computed[float], Computed[float], Computed[float]]:
        """Get the bounds (x0, y0, x1, y1) of a specific cell.

        Args:
            row: Row index (0-based)
            col: Column index (0-based)

        Returns:
            Tuple of (left, top, right, bottom) coordinates of the cell

        Raises:
            ValueError: If row or column is out of bounds
        """
        self._validate_cell_index(row, col)

        rows = self.rows
        cols = self.cols
        width = self._width
        height = self._height

        @computed
        def bounds(width: float, height: float, rows: int, cols: int) -> tuple[float, float, float, float]:
            cell_width = width / cols
            cell_height = height / rows
            start_x = -width / 2
            start_y = -height / 2
            x0 = start_x + col * cell_width
            y0 = start_y + row * cell_height
            return (x0, y0, x0 + cell_width, y0 + cell_height)

        b = bounds(width, height, rows, cols)
        return (b[0], b[1], b[2], b[3])

    # def place_in_cell(self, obj: Base, row: int, col: int, direction: Direction = ORIGIN) -> Self:
    #     """Place an object in a specific cell (handles grid rotation/scale automatically)."""

    #     # 1. Get the four bounds as reactive values
    #     x0, y0, x1, y1 = self.get_cell_bounds(row, col)

    #     # 2. Compute the *center* of that cell
    #     find_avg = computed(lambda a, b: (a + b) / 2)
    #     cx = find_avg(x0, x1)
    #     cy = find_avg(y0, y1)

    #     # 3. Add to our content group
    #     self._add(obj)

    #     # 4. Move the object’s OWN pivot (default = its center) to (cx, cy)
    #     #    move_to will apply an instantaneous translation in grid‐local coordinates
    #     obj.move_to(x=cx, y=cy, direction=direction)

    #     return self

    def place_in_cell(self, obj: Base, row: int, col: int, direction: Direction = ORIGIN) -> Self:
        """Place an object in a specific cell.

        Args:
            obj: The object to place
            row: Row index (0-based)
            col: Column index (0-based)

        Returns:
            Self for method chaining
        """
        # Get cell center in local grid coordinates
        cell_geom = computed(shapely.box)(*self.get_cell_bounds(row, col))
        cell_geom = computed(affine_transform)(cell_geom, self.controls.matrix)
        cell = Geometry(cell_geom, center_geometry=False)
        obj.lock_on(cell, direction=direction)
        self._add(obj)
        return self

    def _add(self, obj: Base) -> None:
        self.content.append(obj)

    def style_cell(
        self,
        row: int,
        col: int,
        color: tuple[float, float, float] | HasValue[Color],
        alpha: HasValue[float] = 1.0,
    ) -> Self:
        """Apply a style to a cell that will be rendered during grid drawing.

        This is more efficient than creating separate Rectangle objects.

        Args:
            row: Row index of the cell to style
            col: Column index of the cell to style
            color: RGB color tuple for the cell
            alpha: Opacity of the cell
            radius: Optional corner radius (for rounded corners)

        Returns:
            Self for method chaining
        """
        self._validate_cell_index(row, col)
        style = _CellStyle(color=as_color(color), alpha=alpha)
        self._cell_styles[(row, col)] = style
        return self

    def clear_cell_style(self, row: int, col: int) -> Self:
        """Remove styling from a specific cell.

        Args:
            row: Row index of the cell
            col: Column index of the cell

        Returns:
            Self for method chaining
        """
        if (row, col) in self._cell_styles:
            del self._cell_styles[(row, col)]

        return self

    def clear_all_cell_styles(self) -> Self:
        """Remove styling from all cells.

        Returns:
            Self for method chaining
        """
        self._cell_styles.clear()
        return self
