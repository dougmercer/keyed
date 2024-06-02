from typing import Self

from .animation import LambdaFollower
from .base import Selection
from .code import Code, Line, Text, Token
from .constants import DR, LEFT, UP
from .scene import Scene
from .shapes import Circle, Rectangle

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
        width: float = 1920,
        height: float = 1080,
        menu_height: float = 40,
        scroll_width: float = 40,
        radius: float = 20,
        window_color: tuple[float, float, float] = WINDOW_COLOR,
        bar_color: tuple[float, float, float] = BAR_COLOR,
        scroll_color: tuple[float, float, float] = SCROLL_COLOR,
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

        def font_size(frame: int) -> float:
            return menu_text.max_containing_font_size(
                0.75 * (self._width.at(frame) - 3 * self.menu_height.at(frame)),
                0.75 * self.menu_height.at(frame),
            )

        menu_text.size.follow(LambdaFollower(font_size))

        circles = self._make_circles(scene)
        scroll_bar = Rectangle(
            scene,
            x=0,
            y=0,
            width=scroll_width,
            height=0,  # height - menu_height
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

        # The top bar's width should always match the window's width
        top_bar._width.follow(main_window._width)

        # The top bar should always be on aligned on top of the window.
        top_bar.lock_on(main_window, direction=UP, start_frame=-5)

        # Center the menu text in the menu bar
        menu_text.lock_on(top_bar, start_frame=-4)

        # Align the circles to the left of the menu bar. Translate over by
        circle_offset = menu_height / 2
        circles.lock_on(top_bar, start_frame=-3, direction=LEFT).translate(circle_offset, 0, -2, -2)
        scroll_bar._height.follow(main_window._height).offset(-menu_height, frame=-10)
        scroll_bar.lock_on(main_window, start_frame=-1, direction=DR)

        self.extend([main_window, scroll_bar, top_bar, circles, menu_text])

        self.translate(x, y, -1, -1)

    def add_text(self, text: Code | Line | Token | Text) -> Self:
        self.text = text
        return self

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
