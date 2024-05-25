from __future__ import annotations

import sys
from typing import TYPE_CHECKING
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QSlider, QPushButton
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
import time
from shapely.geometry import Point
from shapely.affinity import affine_transform

from .previewer import Quality, QualitySetting

if TYPE_CHECKING:
    from keyed import Scene

class MainWindow(QMainWindow):
    def __init__(self, scene: Scene, quality: QualitySetting, frame_rate: int=24):
        super().__init__()
        self.scene = scene
        self.quality = quality
        self.frame_rate = frame_rate
        self.current_frame = 0
        self.playing = False
        self.looping = False
        self.last_frame_time = time.perf_counter()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Manic Preview")
        self.setGeometry(100, 100, self.quality.width, self.quality.height)

        # Main widget and layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout()
        self.central_widget.setLayout(self.layout)

        # Image display
        self.label = QLabel()
        self.pixmap = QPixmap(self.quality.width, self.quality.height)
        self.label.setPixmap(self.pixmap)
        self.layout.addWidget(self.label)

        # Frame slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMaximum(self.scene.num_frames - 1)
        self.slider.valueChanged.connect(self.slider_changed)
        self.layout.addWidget(self.slider)

        # Control buttons
        self.play_button = QPushButton("▶️")
        self.play_button.clicked.connect(self.toggle_play)
        self.layout.addWidget(self.play_button)

        self.loop_button = QPushButton("Loop")
        self.loop_button.clicked.connect(self.toggle_loop)
        self.layout.addWidget(self.loop_button)

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.play_animation)

    def toggle_play(self):
        self.playing = not self.playing
        if self.playing:
            self.play_button.setText("⏸️")
            self.update_timer.start(1000 // self.frame_rate)
        else:
            self.play_button.setText("▶️")
            self.update_timer.stop()

    def toggle_loop(self):
        self.looping = not self.looping
        self.loop_button.setText("🔁" if self.looping else "Loop")

    def slider_changed(self, value):
        if not self.playing:
            self.update_canvas(value)

    def play_animation(self):
        current_time = time.perf_counter()
        frame_duration = current_time - self.last_frame_time
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

    def update_canvas(self, frame_number):
        self.current_frame = frame_number
        img_data = self.scene.rasterize(frame_number).get_data()
        qimage = QImage(img_data, self.scene.width, self.scene.height, QImage.Format_ARGB32)
        qpixmap = QPixmap.fromImage(qimage)
        qpixmap = qpixmap.scaled(self.quality.width, self.quality.height, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.label.setPixmap(qpixmap)

def create_animation_window(
    scene: Scene, frame_rate: int = 24, quality: Quality = Quality.low
) -> None:
    app = QApplication(sys.argv)
    window = MainWindow(scene, quality=quality.value, frame_rate=frame_rate)
    window.show()
    sys.exit(app.exec())
