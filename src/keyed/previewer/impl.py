"""PySide6 Previewer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QAction, QImage, QKeyEvent, QMouseEvent, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSlider,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from shapely.affinity import affine_transform
from shapely.geometry import Point

from ..constants import QualitySetting
from ..renderer import VideoFormat

if TYPE_CHECKING:
    from keyed import Base, Scene


def get_object_info(scene: Scene, quality: QualitySetting, frame: int, point: tuple[float, float]) -> Base | None:
    # Scale factor between quality and scene dimensions
    scale_x = quality.width / scene._width
    scale_y = quality.height / scene._height

    # Incoming coordinates are already in quality space, convert to scene space
    x, y = point
    scene_x = x / scale_x
    scene_y = y / scale_y

    # Transform point based on scene's transformation matrix
    matrix = scene.controls.matrix.value
    if matrix is None or (invert := matrix.invert()) is None:
        transformed_x, transformed_y = scene_x, scene_y
    else:
        # fmt: off
        transformed_x, transformed_y = affine_transform(Point(scene_x, scene_y), invert).coords[0]  # pyright: ignore[reportArgumentType] # noqa: E501

    return scene.find(transformed_x, transformed_y, frame)


class InteractiveLabel(QLabel):
    def __init__(
        self,
        quality: QualitySetting,
        scene: Scene,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setStyleSheet("border: 2px solid white;")
        self.coordinates_label: QLabel | None = None
        self.quality = quality
        self.scene = scene
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 225)  # Minimum 16:9 size
        self.drawing_params = {
            "x_offset": 0,
            "y_offset": 0,
            "draw_width": quality.width,
            "draw_height": quality.height,
        }

    def set_coordinates_label(self, label: QLabel) -> None:
        self.coordinates_label = label

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        # Get mouse position in widget coordinates
        mouse_x = ev.position().x()
        mouse_y = ev.position().y()

        # Check if the click is within the actual scene area (accounting for letterboxing)
        x_offset = self.drawing_params["x_offset"]
        y_offset = self.drawing_params["y_offset"]
        draw_width = self.drawing_params["draw_width"]
        draw_height = self.drawing_params["draw_height"]

        # If the click is outside the drawn scene area, ignore it
        if (
            mouse_x < x_offset
            or mouse_x >= x_offset + draw_width
            or mouse_y < y_offset
            or mouse_y >= y_offset + draw_height
        ):
            return

        # Convert to scene coordinates
        # 1. Adjust for letterboxing offset
        adjusted_x = mouse_x - x_offset
        adjusted_y = mouse_y - y_offset

        # 2. Scale from display size to scene quality size
        scene_quality_x = adjusted_x * (self.quality.width / draw_width)
        scene_quality_y = adjusted_y * (self.quality.height / draw_height)

        # Get object info
        info = self.get_object_info(scene_quality_x, scene_quality_y)
        if info:
            QToolTip.showText(ev.globalPosition().toPoint(), info, self)
        else:
            QToolTip.hideText()

    # Add resizeEvent to handle window resizing
    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        # When resized, tell the parent window to update the canvas
        window = self.window()
        if isinstance(window, MainWindow) and hasattr(window, "current_frame"):
            window.update_canvas(window.current_frame)

    # Fixed InteractiveLabel.get_object_info method
    def get_object_info(self, x: float, y: float) -> str:
        window = self.window()
        assert isinstance(window, MainWindow)
        # Pass the scene coordinates directly - x and y are already scaled
        nearest = get_object_info(window.scene, window.quality, window.current_frame, (x, y))
        return repr(nearest)


class MainWindow(QMainWindow):
    def __init__(self, scene: Scene, quality: QualitySetting, frame_rate: int = 24):
        super().__init__()
        self.scene = scene
        self.quality = quality
        self.frame_rate = frame_rate
        self.current_frame = 0
        self.playing = False
        self.looping = False
        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("Keyed Previewer")
        self.setGeometry(100, 100, self.quality.width, self.quality.height)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()
        self.central_widget.setLayout(layout)

        # Menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        # Adding actions to the File menu
        save_images_action = QAction("Save As Images", self)
        save_images_action.triggered.connect(self.save_as_images)
        file_menu.addAction(save_images_action)

        save_layers_action = QAction("Save Layers As Images", self)
        save_layers_action.triggered.connect(self.save_layers_as_images)
        file_menu.addAction(save_layers_action)

        save_video_action = QAction("Save as Video", self)
        save_video_action.triggered.connect(self.save_as_video)
        file_menu.addAction(save_video_action)

        # Image display
        self.label = InteractiveLabel(self.quality, self.scene)
        self.pixmap = None
        # self.pixmap = QPixmap(self.quality.width, self.quality.height)
        # self.label.setPixmap(self.pixmap)
        layout.addWidget(self.label)

        # Frame slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMaximum(self.scene.num_frames - 1)
        self.slider.valueChanged.connect(self.slider_changed)
        layout.addWidget(self.slider)

        # Control and display area (Horizontal Layout)
        control_layout = QHBoxLayout()
        layout.addLayout(control_layout)

        # Play button
        self.play_button = QPushButton("▶️")
        self.play_button.clicked.connect(self.toggle_play)
        control_layout.addWidget(self.play_button)

        # Loop button
        self.loop_button = QPushButton("➡️")
        self.loop_button.clicked.connect(self.toggle_loop)
        control_layout.addWidget(self.loop_button)

        # Frame Counter label
        self.frame_counter_label = QLabel("Frame: 0")
        control_layout.addWidget(self.frame_counter_label)
        control_layout.addStretch()

        # FPS Label
        self.fps_label = QLabel("")
        layout.addWidget(self.fps_label)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.play_animation)

        # Object information display
        self.object_info = QLabel("")
        layout.addWidget(self.object_info)

        # Coordinates display
        self.coordinates_label = QLabel("(0, 0)")
        layout.addWidget(self.coordinates_label)
        self.label.set_coordinates_label(self.coordinates_label)

        # Initialize with frame 0 visible
        self.update_canvas(0)
        self.update_frame_counter()

        # Enable looping
        self.toggle_loop()

    def save_as_images(self) -> None:
        self.scene.draw(open_dir=True)

    def save_layers_as_images(self) -> None:
        self.scene.draw_as_layers(open_dir=True)

    def save_as_video(self) -> None:
        self.scene.render(format=VideoFormat.MOV_PRORES, frame_rate=self.frame_rate)
        self.scene._open_folder()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Right:
            self.increment_frame()
        elif event.key() == Qt.Key.Key_Left:
            self.decrement_frame()
        elif event.key() == Qt.Key.Key_Space:
            self.toggle_play()

    def increment_frame(self) -> None:
        if self.current_frame < self.scene.num_frames - 1:
            self.current_frame += 1
            self.update_canvas(self.current_frame)
            self.slider.setValue(self.current_frame)

    def decrement_frame(self) -> None:
        if self.current_frame > 0:
            self.current_frame -= 1
            self.update_canvas(self.current_frame)
            self.slider.setValue(self.current_frame)

    def toggle_play(self) -> None:
        self.playing = not self.playing
        if self.playing:
            self.play_button.setText("⏸️")
            self.update_timer.start(1000 // self.frame_rate)
        else:
            self.play_button.setText("▶️")
            self.update_timer.stop()

    def toggle_loop(self) -> None:
        self.looping = not self.looping
        self.loop_button.setText("🔁" if self.looping else "➡️")

    def slider_changed(self, value: int) -> None:
        if not self.playing:
            self.update_canvas(value)
            self.update_frame_counter()

    def play_animation(self) -> None:
        self.current_frame += 1
        if self.current_frame >= self.scene.num_frames:
            if self.looping:
                self.current_frame = 0
            else:
                self.toggle_play()
                return

        self.slider.setValue(self.current_frame)
        self.update_canvas(self.current_frame)
        self.update_frame_counter()

    def update_canvas(self, frame_number: int) -> None:
        self.current_frame = frame_number
        img_data = self.scene.rasterize(frame_number).get_data()
        qimage = QImage(img_data, self.scene._width, self.scene._height, QImage.Format.Format_ARGB32)

        # Get the current size of the label for scaling
        label_width = self.label.width()
        label_height = self.label.height()

        # Calculate letterboxing offsets and drawing dimensions
        scene_aspect = self.scene._width / self.scene._height
        label_aspect = label_width / label_height

        if scene_aspect > label_aspect:
            # Width limited
            draw_width = label_width
            draw_height = int(label_width / scene_aspect)
            y_offset = (label_height - draw_height) // 2
            x_offset = 0
        else:
            # Height limited
            draw_height = label_height
            draw_width = int(label_height * scene_aspect)
            x_offset = (label_width - draw_width) // 2
            y_offset = 0

        # Store the drawing parameters for coordinate conversion
        self.label.drawing_params = {
            "x_offset": x_offset,
            "y_offset": y_offset,
            "draw_width": draw_width,
            "draw_height": draw_height,
        }

        # Create a QPixmap and draw the scene
        qpixmap = QPixmap(label_width, label_height)
        qpixmap.fill(Qt.GlobalColor.black)

        with QPainter(qpixmap) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
            painter.drawImage(
                QRect(x_offset, y_offset, draw_width, draw_height),
                qimage,
                QRect(0, 0, qimage.width(), qimage.height()),
            )

        self.label.setPixmap(qpixmap)

    def update_frame_counter(self) -> None:
        self.frame_counter_label.setText(f"Frame: {self.current_frame}/{self.scene.num_frames - 1}")
