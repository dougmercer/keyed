from __future__ import annotations

import sys
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QKeyEvent, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from shapely.affinity import affine_transform
from shapely.geometry import Point

from .quality import Quality, QualitySetting

if TYPE_CHECKING:
    from keyed import Base, Scene

__all__ = ["create_animation_window"]


def get_object_info(
    scene: Scene, quality: QualitySetting, frame: int, point: tuple[float, float]
) -> Base | None:
    scale_x = quality.width / scene._width
    scale_y = quality.height / scene._height

    # Adjust coordinates based on the UI scaling
    x, y = point
    x = x / scale_x
    y = y / scale_y

    # Transform point based on scene's transformation matrix
    matrix = scene.get_matrix(frame)
    if matrix is None or (invert := matrix.invert()) is None:
        scene_x, scene_y = x, y
    else:
        scene_x, scene_y = affine_transform(Point(x, y), invert).coords[0]

    return scene.find(scene_x, scene_y, frame)


class InteractiveLabel(QLabel):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        x, y = event.position().x(), event.position().y()
        info = self.get_object_info(x, y)
        if info:
            QToolTip.showText(event.globalPosition().toPoint(), info, self)
        else:
            QToolTip.hideText()

    def get_object_info(self, x: float, y: float) -> str:
        window = self.window()
        assert isinstance(window, MainWindow)
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
        self.last_frame_time = time.perf_counter()
        self.init_ui()

    def init_ui(self) -> None:
        self.setWindowTitle("Manic Preview")
        self.setGeometry(100, 100, self.quality.width, self.quality.height)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()
        self.central_widget.setLayout(layout)

        # Image display
        self.label = InteractiveLabel()
        self.pixmap = QPixmap(self.quality.width, self.quality.height)
        self.label.setPixmap(self.pixmap)
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

        # Initialize with frame 0 visible
        self.update_canvas(0)
        self.update_frame_counter()

        # Enable looping
        self.toggle_loop()

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
        current_time = time.perf_counter()
        self.last_frame_time = current_time

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
        qimage = QImage(
            img_data, self.scene._width, self.scene._height, QImage.Format.Format_ARGB32
        )
        qpixmap = QPixmap.fromImage(qimage)
        qpixmap = qpixmap.scaled(
            self.quality.width,
            self.quality.height,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.label.setPixmap(qpixmap)

    def update_frame_counter(self) -> None:
        self.frame_counter_label.setText(f"Frame: {self.current_frame}/{self.scene.num_frames - 1}")


def create_animation_window(
    scene: Scene, frame_rate: int = 24, quality: Quality = Quality.high
) -> None:
    app = QApplication(sys.argv)
    window = MainWindow(scene, quality=quality.value, frame_rate=frame_rate)
    window.show()
    sys.exit(app.exec())
