import shapely

from .animation import Animation, LambdaFollower
from .base import Selection
from .code import Code, Text
from .constants import DOWN, DR, LEFT, UL, UP
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
        window_color: tuple[float, float, float] = WINDOW_COLOR,
        bar_color: tuple[float, float, float] = BAR_COLOR,
        scroll_color: tuple[float, float, float] = SCROLL_COLOR,
        draw_scroll_bar: bool = True,
    ):
        if 2 * radius > menu_height:
            raise ValueError(
                f"Corner radius must be less than 1/2 menu height ({radius=}, {menu_height})"
            )
        super().__init__()
        self.title = title
        self.window_color = window_color
        self.bar_color = bar_color
        self.scroll_color = scroll_color
        self.code = code

        main_window = Rectangle(
            scene,
            x=0,
            y=0,
            width=width,
            height=height,
            fill_color=window_color,
            color=WHITE,
            radius=radius,
        )
        self._width = main_window._width
        self._height = main_window._height
        self.radius = main_window.radius

        top_bar = Rectangle(
            scene,
            x=0,
            y=0,
            width=width,
            height=menu_height,
            fill_color=bar_color,
            color=WHITE,
            radius=radius,
            round_bl=False,
            round_br=False,
        )
        self.menu_height = top_bar._height

        menu_text = Text(scene, x=0, y=0, text=title, color=WHITE)

        circles = self._make_circles(scene)
        if draw_scroll_bar:
            scroll_bar = self._make_scroll_bar(
                scene,
                scroll_width=scroll_width,
                scroll_color=scroll_color,
                radius=radius,
                main_window=main_window,
                top_bar=top_bar,
            )

        # The top bar's width should always match the window's width
        top_bar._width.follow(main_window._width)

        # The top bar should always be on aligned on top of the window.
        top_bar.lock_on(main_window, direction=UP, start_frame=-5)

        # Center the menu text in the menu bar
        menu_text.lock_on(top_bar, start_frame=-1)

        # Express font size relative to the menu_bar.
        # Note: this can technically overflow into the circles, but it looks weird to
        # center in the non-circles_container space.
        def font_size(frame: int) -> float:
            return menu_text.max_containing_font_size(
                0.75 * self._width.at(frame) - 3 * self.menu_height.at(frame),
                0.75 * self.menu_height.at(frame),
            )

        menu_text.size.follow(LambdaFollower(font_size))

        # Position the circles within a non-visible container in the top bar.
        circles_container = Rectangle(scene, x=0, y=0, alpha=0.5, fill_color=(1, 0, 0))
        circles_container._width.follow(
            LambdaFollower(lambda frame: 3 * self.menu_height.at(frame))
        )
        circles_container._height.follow(LambdaFollower(lambda frame: self.menu_height.at(frame)))
        circles_container.lock_on(top_bar, start_frame=-3, direction=LEFT)
        circles.lock_on(circles_container, start_frame=-2)

        # Put the objects into Self
        self.extend([main_window, top_bar, circles, menu_text])
        self.scroll_bar = scroll_bar

        if self.code is not None:
            text_extents = Rectangle(
                scene,
                round_tl=False,
                round_tr=False,
                round_bl=main_window.round_bl,
                round_br=main_window.round_br,
                alpha=0.5,
                fill_color=(1, 0, 0),
            )
            text_extents._height.follow(scroll_bar._height)
            text_extents._width.follow(main_window._width)
            text_extents.radius = main_window.radius
            text_extents.lock_on(main_window, direction=DOWN)
            buffer = min(radius, 20)
            buffered_text_extents = Rectangle(scene)
            buffered_text_extents._height.follow(text_extents._height).offset(-buffer)
            buffered_text_extents._width.follow(text_extents._width).offset(-buffer)
            buffered_text_extents.lock_on(text_extents, direction=DOWN)

            # Make all text objects share a common context
            # NOTE: Maybe they should already share a context?
            ctx = scene.get_context()
            for char in self.code.chars:
                char.ctx = ctx
            text_extents.ctx = ctx
            self.text_extents = text_extents
            self.code.lock_on(buffered_text_extents, direction=UL)

        # Apply x/y offset.
        self.translate(x, y, -1, -1)

    def _make_circles(self, scene: Scene) -> Selection[Circle]:
        def radius(frame: int) -> float:
            return self.menu_height.at(frame) / 4

        def x_offset(frame: int) -> float:
            return self.menu_height.at(frame) / 2

        def yellow_offset(frame: int) -> float:
            return x_offset(frame) + 3 * radius(frame)

        def green_offset(frame: int) -> float:
            return x_offset(frame) + 6 * radius(frame)

        red = Circle(scene, x=0, y=0, fill_color=MAC_RED)
        red.controls.delta_x.follow(LambdaFollower(x_offset))
        red.radius.follow(LambdaFollower(radius))

        yellow = Circle(scene, x=0, y=0, fill_color=MAC_YELLOW)
        yellow.controls.delta_x.follow(LambdaFollower(yellow_offset))
        yellow.radius.follow(LambdaFollower(radius))

        green = Circle(scene, x=0, y=0, fill_color=MAC_GREEN)
        green.controls.delta_x.follow(LambdaFollower(green_offset))
        green.radius.follow(LambdaFollower(radius))
        return Selection([red, yellow, green])

    def draw(self, frame: int = 0) -> None:
        # Define the clipping region to the bounds of the editor window
        super().draw(frame)
        self.scroll_bar.draw(frame)
        if self.code:
            with self.text_extents.clip(frame):
                self.code.draw(frame)

    def add_transform(self, transform: Transform) -> None:
        super().add_transform(transform)
        if self.code is not None:
            self.code.add_transform(transform)
            self.scroll_bar.add_transform(transform)
            self.text_extents.add_transform(transform)

    def animate(self, property: str, animation: Animation) -> None:
        super().animate(property, animation)
        if self.code is not None:
            self.code.animate(property, animation)
            self.scroll_bar.animate(property, animation)
            self.text_extents.animate(property, animation)

    def _make_scroll_bar(
        self,
        scene: Scene,
        scroll_width: float,
        scroll_color: tuple[float, float, float],
        radius: float,
        main_window: Rectangle,
        top_bar: Rectangle,
    ) -> Rectangle:
        scroll_bar = Rectangle(
            scene,
            x=0,
            y=0,
            width=scroll_width,
            height=0,
            fill_color=scroll_color,
            color=WHITE,
            round_bl=False,
            round_tl=False,
            round_tr=False,
            round_br=True,
            radius=radius,
        )

        self.scroll_width = scroll_bar._width
        scroll_bar._height.follow(
            LambdaFollower(lambda frame: main_window._height.at(frame) - top_bar._height.at(frame))
        )

        # Position the scrollbar.
        scroll_bar.lock_on(main_window, start_frame=-1, direction=DR)
        return scroll_bar

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
        main_window: Rectangle = self[0]
        return main_window._geom(frame, before)
