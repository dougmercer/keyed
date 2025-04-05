"""PySide6 Previewer."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

from shapely.affinity import affine_transform
from shapely.geometry import Point

from .constants import Quality, QualitySetting
from .renderer import VideoFormat

if TYPE_CHECKING:
    from keyed import Base, Scene


__all__ = ["create_animation_window"]

# Check if PySide6 is available
PREVIEW_AVAILABLE = importlib.util.find_spec("PySide6") is not None and importlib.util.find_spec("watchdog") is not None

if PREVIEW_AVAILABLE:
    from PySide6.QtCore import QRect, Qt, QThread, QTimer, Signal
    from PySide6.QtGui import QAction, QImage, QKeyEvent, QMouseEvent, QPainter, QPixmap, QResizeEvent
    from PySide6.QtWidgets import (
        QApplication,
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
    from watchdog.events import FileSystemEvent, FileSystemEventHandler
    from watchdog.observers import Observer

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
            self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            # Add this to ensure the label keeps its aspect ratio
            self.setMinimumSize(400, 225)  # Minimum 16:9 size

        def set_coordinates_label(self, label: QLabel) -> None:
            self.coordinates_label = label

        def mousePressEvent(self, ev: QMouseEvent) -> None:
            # Calculate scale factor based on current widget size vs original quality size
            scale_x = self.width() / self.quality.width
            scale_y = self.height() / self.quality.height

            # Get the raw position in widget coordinates
            raw_x, raw_y = ev.position().x(), ev.position().y()

            # Convert widget coordinates to scene quality coordinates
            scene_x = raw_x / scale_x
            scene_y = raw_y / scale_y

            # Get object info using the scaled coordinates
            info = self.get_object_info(scene_x, scene_y)
            if info:
                QToolTip.showText(ev.globalPosition().toPoint(), info, self)
            else:
                QToolTip.hideText()

        # Fixed InteractiveLabel.mouseMoveEvent method
        def mouseMoveEvent(self, ev: QMouseEvent) -> None:
            # Calculate scale factor based on current widget size vs original quality size
            scale_x = self.width() / self.quality.width
            scale_y = self.height() / self.quality.height

            # Get the raw position and convert to scene coordinates
            x, y = ev.position().x(), ev.position().y()
            scene_x = x / scale_x
            scene_y = y / scale_y

            if self.coordinates_label:
                self.coordinates_label.setText(f"({scene_x:.1f}, {scene_y:.1f})")

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

            # Create a QPixmap sized to fit the label while maintaining aspect ratio
            qpixmap = QPixmap(label_width, label_height)
            qpixmap.fill(Qt.GlobalColor.black)

            # Use QPainter to draw the QImage onto the QPixmap
            with QPainter(qpixmap) as painter:
                # Enable high-quality antialiasing for smoother scaling
                painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
                painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

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

                painter.drawImage(
                    QRect(x_offset, y_offset, draw_width, draw_height),
                    qimage,
                    QRect(0, 0, qimage.width(), qimage.height()),
                )

            self.label.setPixmap(qpixmap)

        def update_frame_counter(self) -> None:
            self.frame_counter_label.setText(f"Frame: {self.current_frame}/{self.scene.num_frames - 1}")

    def create_animation_window(scene: Scene, frame_rate: int = 24, quality: Quality = Quality.very_high) -> NoReturn:
        """Create the animation preview window for the provided scene.

        Args:
            scene: Scene to preview
            frame_rate: Playback frame rate
            quality: Size of the preview window

        Raises:
            ImportError: If PySide6 is not installed
        """
        if not PREVIEW_AVAILABLE:
            raise ImportError(
                "PySide6 is required for preview functionality. Install it with: pip install keyed[preview]"
            )
        app = QApplication(sys.argv)
        window = MainWindow(scene, quality=quality.value, frame_rate=frame_rate)
        window.show()
        sys.exit(app.exec())

    class FileWatcher(QThread):
        """Watch for file changes and notify when updates occur."""

        file_changed = Signal()

        def __init__(self, file_path: Path):
            super().__init__()
            self.file_path = file_path
            self.observer = Observer()
            self.running = True

        def run(self):
            """Start watching the file for changes."""
            event_handler = SceneFileHandler(self.file_path, self.file_changed)  # type: ignore
            self.observer.schedule(event_handler, str(self.file_path.parent), recursive=False)
            self.observer.start()

            while self.running:
                self.observer.join(1)

        def stop(self):
            """Stop watching for file changes."""
            self.running = False
            self.observer.stop()
            self.observer.join()

    class SceneFileHandler(FileSystemEventHandler):
        """Handle file system events for the scene file."""

        def __init__(self, file_path: Path, callback: Signal):
            self.file_path = file_path
            self.callback = callback

        def on_modified(self, event: FileSystemEvent):
            """Called when the watched file is modified."""
            if not event.is_directory and Path(event.src_path).resolve() == self.file_path.resolve():  # type: ignore
                self.callback.emit()  # type: ignore

    class LiveReloadWindow(MainWindow):
        """MainWindow that can update its scene without reloading."""

        def update_scene(self, new_scene: Scene):
            """Update the window with a new scene instance.

            Args:
                new_scene: The new Scene instance to display
            """
            # Preserve current state
            current_frame = self.current_frame
            was_playing = self.playing

            # Update scene
            self.scene = new_scene

            # Update UI for new scene
            self.slider.setMaximum(new_scene.num_frames - 1)
            if current_frame >= new_scene.num_frames:
                current_frame = 0

            # Update display
            self.current_frame = current_frame
            self.update_canvas(current_frame)
            self.update_frame_counter()

            # Restore playback if it was playing
            if was_playing and not self.playing:
                self.toggle_play()


def create_animation_window(scene: Scene, frame_rate: int = 24, quality: Quality = Quality.very_high) -> NoReturn:
    """Create the animation preview window for the provided scene.

    Args:
        scene: Scene to preview
        frame_rate: Playback frame rate
        quality: Size of the preview window

    Raises:
        ImportError: If required preview dependencies are not installed
    """
    if not PREVIEW_AVAILABLE:
        raise ImportError(
            "PySide6 and watchdog are required for preview functionality. Install them with: pip install keyed[preview]"
        )

    app = QApplication(sys.argv)  # type: ignore
    window = MainWindow(scene, quality=quality.value, frame_rate=frame_rate)
    window.show()
    sys.exit(app.exec())
