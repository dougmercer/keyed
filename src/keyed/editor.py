import shapely
import shapely.geometry

from .animation import Animation, Expression, Property
from .base import Selection
from .code import Code, Text
from .constants import DL, DR, LEFT, UL, UP
from .scene import Scene
from .shapes import Circle, Rectangle
from .transformation import Transform, Transformable

__all__ = ["Editor"]

MAC_RED = (255 / 255, 59 / 255, 48 / 255)
MAC_YELLOW = (255 / 255, 149 / 255, 0)
MAC_GREEN = (40 / 255, 205 / 255, 65 / 255)

BLACK = (0, 0, 0)
WHITE = (1, 1, 1)
WINDOW_COLOR = (0.1, 0.1, 0.1)
BAR_COLOR = (0.2, 0.2, 0.2)
SCROLL_COLOR = (0.3, 0.3, 0.3)


class ScrollBar(Selection):
    def __init__(
        self,
        scene: Scene,
        scroll_width: float,
        color: tuple[float, float, float],
        fill_color: tuple[float, float, float],
        radius: float,
        main_window: Rectangle,
        top_bar: Rectangle,
        indicator_height: float = 100,
        indicator_color: tuple[float, float, float] = BLACK,
        indicator_fill_color: tuple[float, float, float] = WHITE,
    ) -> None:
        scroll_bar = Rectangle(
            scene,
            x=0,
            y=0,
            width=scroll_width,
            height=0,
            fill_color=fill_color,
            color=color,
            round_bl=False,
            round_tl=False,
            round_tr=False,
            round_br=True,
            radius=radius,
        )

        self.scroll_width = scroll_bar._width
        scroll_bar._height.follow(main_window._height - top_bar._height)

        # Position the scrollbar.
        scroll_bar.lock_on(main_window, start_frame=-13, direction=DR)

        # Create the scroll_indicator within the scroll bar
        scroll_indicator = Rectangle(
            scene,
            x=0,
            y=0,
            width=scroll_width,
            height=indicator_height,
            fill_color=indicator_fill_color,
            color=indicator_color,
            radius=radius,
        )
        scroll_indicator._width.follow(scroll_bar._width)
        scroll_indicator.lock_on(scroll_bar, start_frame=-12, x=True, y=False)
        scroll_indicator.align_to(scroll_bar, -11, -11, direction=UP)

        self.progress = Property(0)
        scroll_indicator.controls.delta_y.follow((scroll_bar._height - indicator_height) * self.progress)

        self._width = scroll_bar._width
        self._height = scroll_bar._height
        super().__init__([scroll_bar, scroll_indicator])


class Editor(Selection):
    def __init__(
        self,
        scene: Scene,
        x: float = 10,
        y: float = 10,
        title: str = "",
        code: Code | None = None,
        width: float = 1920,
        height: float = 1080,
        menu_height: float = 40,
        scroll_width: float = 40,
        radius: float = 20,
        margin: float = 40,
        window_color: tuple[float, float, float] = WHITE,
        window_fill_color: tuple[float, float, float] = WINDOW_COLOR,
        bar_color: tuple[float, float, float] = WHITE,
        bar_fill_color: tuple[float, float, float] = BAR_COLOR,
        scroll_color: tuple[float, float, float] = WHITE,
        scroll_fill_color: tuple[float, float, float] = SCROLL_COLOR,
        scroll_indicator_height: float = 100,
        scroll_indicator_color: tuple[float, float, float] = BLACK,
        scroll_indicator_fill_color: tuple[float, float, float] = WHITE,
        draw_scroll_bar: bool = True,
    ):
        if 2 * radius > menu_height:
            raise ValueError(
                f"Corner radius must be less than 1/2 menu height ({radius=}, {menu_height})"
            )
        super().__init__()
        self.ctx = scene.get_context()
        self.code = code
        self.other_code: list[Code] = []
        self.draw_scroll_bar = draw_scroll_bar

        self.main_window = Rectangle(
            scene,
            x=0,
            y=0,
            width=width,
            height=height,
            fill_color=window_fill_color,
            color=window_color,
            radius=radius,
        )
        self._width = self.main_window._width
        self._height = self.main_window._height
        self.radius = self.main_window.radius

        top_bar = Rectangle(
            scene,
            x=0,
            y=0,
            width=width,
            height=menu_height,
            fill_color=bar_fill_color,
            color=bar_color,
            radius=radius,
            round_bl=False,
            round_br=False,
        )
        self.menu_height = top_bar._height

        menu_text = Text(scene, x=0, y=0, text=title, color=WHITE)

        circles = self._make_circles(scene)

        # TODO, don't tie sizing to scroll bar so we can avoid creating this
        scroll_bar = ScrollBar(
            scene,
            scroll_width=scroll_width,
            color=scroll_color,
            fill_color=scroll_fill_color,
            radius=radius,
            main_window=self.main_window,
            top_bar=top_bar,
            indicator_height=scroll_indicator_height,
            indicator_color=scroll_indicator_color,
            indicator_fill_color=scroll_indicator_fill_color,
        )
        self.scroll_bar = scroll_bar

        # The top bar's width should always match the window's width
        top_bar._width.follow(self.main_window._width)

        # The top bar should always be on aligned on top of the window.
        top_bar.lock_on(self.main_window, direction=UP, start_frame=-10)

        # Center the menu text in the menu bar
        menu_text.lock_on(top_bar, start_frame=-9)

        # Express font size relative to the menu_bar.
        # Note: this can technically overflow into the circles, but it looks weird to
        # center in the non-circles_container space.
        def font_size(frame: int) -> float:
            return menu_text.max_containing_font_size(
                0.75 * self._width.at(frame) - 3 * self.menu_height.at(frame),
                0.75 * self.menu_height.at(frame),
            )

        menu_text.size.follow(Expression(font_size))

        # Position the circles within a non-visible container in the top bar.
        circles_container = Rectangle(scene, x=0, y=0, alpha=0.5, fill_color=(1, 0, 0))
        circles_container._width.follow(3 * self.menu_height)
        circles_container._height.follow(self.menu_height)
        circles_container.lock_on(top_bar, start_frame=-8, direction=LEFT)
        circles.lock_on(circles_container, start_frame=-7)

        # Put the objects into Self
        self.extend([self.main_window, top_bar, circles, menu_text])

        if self.code is not None:
            text_extents = Rectangle(
                scene,
                width=0,
                height=0,
                round_tl=False,
                round_tr=False,
                round_br=False,
                round_bl=self.main_window.round_bl,
                alpha=0.5,
                fill_color=(1, 0, 0),
            )
            text_extents._height.follow(scroll_bar._height)
            text_extents._width.follow(self.main_window._width - self.scroll_bar._width)
            text_extents.radius = self.main_window.radius
            text_extents.lock_on(self.main_window, direction=DL, start_frame=-7)

            buffer = max(radius, margin)
            buffered_text_extents = Rectangle(
                scene, width=0, height=0, alpha=0.5, fill_color=(0, 0, 1)
            )
            buffered_text_extents._height.follow(text_extents._height - buffer)
            buffered_text_extents._width.follow(text_extents._width - buffer)
            buffered_text_extents.lock_on(text_extents, direction=DR, start_frame=-6)

            # Make all text objects share a common context
            # NOTE: Maybe they should already share a context?
            self.code.set("ctx", self.ctx)
            text_extents.ctx = self.ctx
            self.text_extents = text_extents
            self.buffered_text_extents = buffered_text_extents

            assert not self.code.controls.transforms, "Create editor before transforming code."

            if self.code.controls.transforms:
                anim_now = self.code.controls.transforms[-1]

                def get_geom(frame: int) -> shapely.geometry.Polygon:
                    return self.code._geom(frame, before=anim_now)  # type: ignore[union-attr]

            else:
                geom = self.code.geom(0)

                def get_geom(frame: int) -> shapely.geometry.Polygon:
                    return geom

            def code_height_func(frame: int) -> float:
                g = get_geom(frame)
                return g.bounds[3] - g.bounds[1]

            self.code.align_to(buffered_text_extents, -5, -5, direction=UL)
            code_height = Expression(code_height_func)

            self.code.translate(
                0,
                (buffered_text_extents._height - code_height - buffer) * scroll_bar.progress,
                0,
                0,
            )

        # Apply x/y offset.
        self.translate(x, y, -1, -1)

    def _make_circles(self, scene: Scene) -> Selection[Circle]:
        radius = self.menu_height / 4
        x_offset = self.menu_height / 2
        yellow_offset = x_offset + 3 * radius
        green_offset = x_offset + 6 * radius

        red = Circle(scene, x=0, y=0, fill_color=MAC_RED)
        red.controls.delta_x.follow(x_offset)
        red.radius.follow(radius)

        yellow = Circle(scene, x=0, y=0, fill_color=MAC_YELLOW)
        yellow.controls.delta_x.follow(yellow_offset)
        yellow.radius.follow(radius)

        green = Circle(scene, x=0, y=0, fill_color=MAC_GREEN)
        green.controls.delta_x.follow(green_offset)
        green.radius.follow(radius)
        return Selection([red, yellow, green])

    def draw(self, frame: int = 0) -> None:
        super().draw(frame)
        if self.draw_scroll_bar:
            self.scroll_bar.draw(frame)
        if self.code:
            with self.text_extents.clip(frame):
                self.code.draw(frame)
                for code in self.other_code:
                    code.draw(frame)

    def add_code(self, code: Code) -> None:
        code.set("ctx", self.ctx)
        self.other_code.append(code)

    def add_transform(self, transform: Transform) -> None:
        super().add_transform(transform)
        if self.scroll_bar is not None:
            self.scroll_bar.add_transform(transform)
        if self.code is not None:
            self.code.add_transform(transform)
            self.text_extents.add_transform(transform)
            self.buffered_text_extents.add_transform(transform)

    def animate(self, property: str, animation: Animation) -> None:
        super().animate(property, animation)
        if self.scroll_bar is not None:
            self.scroll_bar.animate(property, animation)
        if self.code is not None:
            self.code.animate(property, animation)
            self.text_extents.animate(property, animation)
            self.buffered_text_extents.animate(property, animation)

    def freeze(self) -> None:
        if not self.is_frozen:
            self.scroll_bar.freeze()
            if self.code is not None:
                self.code.freeze()
            for obj in self:
                assert isinstance(obj, Transformable)
                obj.freeze()
        super().freeze()

    def _geom(
        self,
        frame: int = 0,
        before: Transform | None = None,
    ) -> shapely.Polygon:
        return self.main_window._geom(frame, before)
