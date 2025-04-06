"""PySide6 Previewer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QAction, QImage, QKeyEvent, QMouseEvent, QPainter, QPen, QPixmap, QResizeEvent
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
    """Find an object at the given point in the scene.

    Args:
        scene: The scene to search in
        quality: Quality settings to help with coordinate conversion
        frame: Current frame
        point: (x, y) coordinates in the quality-specific space

    Returns:
        The found object or None
    """
    # Convert coordinates from display space to scene space
    x, y = point
    scene_x = x
    scene_y = y

    # Transform point based on scene's transformation matrix
    matrix = scene.controls.matrix.value
    if matrix is None or (invert := matrix.invert()) is None:
        transformed_x, transformed_y = scene_x, scene_y
    else:
        transformed_x, transformed_y = affine_transform(Point(scene_x, scene_y), invert).coords[0]

    return scene.find(transformed_x, transformed_y, frame)


class InteractiveLabel(QLabel):
    """An interactive label that displays the scene and handles mouse events."""

    def __init__(
        self,
        quality: QualitySetting,
        scene: Scene,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setStyleSheet("border: 2px solid #333; background-color: #222;")
        self.coordinates_label: QLabel | None = None
        self.quality = quality
        self.scene = scene
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(400, 225)  # Minimum viable size

        # Initialize drawing parameters
        self.drawing_params = {
            "x_offset": 0,
            "y_offset": 0,
            "draw_width": self.scene._width,
            "draw_height": self.scene._height,
            "scale_x": 1.0,
            "scale_y": 1.0,
        }

    def set_coordinates_label(self, label: QLabel) -> None:
        """Set the label that will display coordinates."""
        self.coordinates_label = label

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        """Handle mouse press events to show object information."""
        # Get mouse position in widget coordinates
        mouse_x = ev.position().x()
        mouse_y = ev.position().y()

        # Check if the click is within the actual scene area
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

        # 2. Scale from display size to scene size
        scale_x = self.drawing_params["scale_x"]
        scale_y = self.drawing_params["scale_y"]
        scene_x = adjusted_x / scale_x
        scene_y = adjusted_y / scale_y

        # Get object info
        info = self.get_object_info(scene_x, scene_y)
        if info:
            QToolTip.showText(ev.globalPosition().toPoint(), info, self)
        else:
            QToolTip.hideText()

    def mouseMoveEvent(self, ev: QMouseEvent) -> None:
        """Track mouse movements to update the coordinates display."""
        if not self.coordinates_label:
            return

        # Get mouse position
        mouse_x = ev.position().x()
        mouse_y = ev.position().y()

        # Check if inside drawing area
        x_offset = self.drawing_params["x_offset"]
        y_offset = self.drawing_params["y_offset"]
        draw_width = self.drawing_params["draw_width"]
        draw_height = self.drawing_params["draw_height"]

        if (
            mouse_x < x_offset
            or mouse_x >= x_offset + draw_width
            or mouse_y < y_offset
            or mouse_y >= y_offset + draw_height
        ):
            self.coordinates_label.setText("Outside scene")
            return

        # Convert to scene coordinates
        adjusted_x = mouse_x - x_offset
        adjusted_y = mouse_y - y_offset

        scale_x = self.drawing_params["scale_x"]
        scale_y = self.drawing_params["scale_y"]
        scene_x = adjusted_x / scale_x
        scene_y = adjusted_y / scale_y

        self.coordinates_label.setText(f"({scene_x:.1f}, {scene_y:.1f})")

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle resize events to update the canvas."""
        super().resizeEvent(event)
        window = self.window()
        if isinstance(window, MainWindow) and hasattr(window, "current_frame"):
            window.update_canvas(window.current_frame)

    def get_object_info(self, x: float, y: float) -> str:
        """Get information about an object at the given coordinates."""
        window = self.window()
        assert isinstance(window, MainWindow)
        nearest = get_object_info(window.scene, window.quality, window.current_frame, (x, y))
        return repr(nearest) if nearest else "No object found"


class MainWindow(QMainWindow):
    """Main window for the previewer application."""

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
        """Initialize the user interface."""
        self.setWindowTitle(f"Keyed Previewer - {self.scene.scene_name or 'Untitled'}")

        # Set initial window size based on quality but with some reasonable limits
        max_width = min(1600, self.quality.width)
        max_height = min(900, self.quality.height)
        self.resize(max_width, max_height)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()
        self.central_widget.setLayout(layout)

        # Menu bar
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")

        # Actions
        save_images_action = QAction("Save As Images", self)
        save_images_action.triggered.connect(self.save_as_images)
        file_menu.addAction(save_images_action)

        save_layers_action = QAction("Save Layers As Images", self)
        save_layers_action.triggered.connect(self.save_layers_as_images)
        file_menu.addAction(save_layers_action)

        save_video_action = QAction("Save as Video", self)
        save_video_action.triggered.connect(self.save_as_video)
        file_menu.addAction(save_video_action)

        # Scene info in status bar
        self.statusBar().showMessage(
            f"Scene: {self.scene._width}x{self.scene._height} px, {self.scene.num_frames} frames"
        )

        # Image display
        self.label = InteractiveLabel(self.quality, self.scene)
        layout.addWidget(self.label)

        # Frame slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMaximum(self.scene.num_frames - 1)
        self.slider.valueChanged.connect(self.slider_changed)
        layout.addWidget(self.slider)

        # Control area
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

        # Bottom info area
        bottom_layout = QHBoxLayout()
        layout.addLayout(bottom_layout)

        # Coordinates display
        self.coordinates_label = QLabel("(0, 0)")
        self.coordinates_label.setMinimumWidth(100)
        bottom_layout.addWidget(self.coordinates_label)
        self.label.set_coordinates_label(self.coordinates_label)

        # Object info display
        self.object_info = QLabel("")
        bottom_layout.addWidget(self.object_info)
        bottom_layout.addStretch()

        # FPS info
        self.fps_label = QLabel(f"{self.frame_rate} fps")
        bottom_layout.addWidget(self.fps_label)

        # Animation timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.play_animation)

        # Initialize display
        self.update_canvas(0)
        self.update_frame_counter()
        self.toggle_loop()  # Enable looping by default

    def save_as_images(self) -> None:
        """Save the scene as a sequence of image files."""
        self.scene.draw(open_dir=True)

    def save_layers_as_images(self) -> None:
        """Save each layer of the scene as a sequence of image files."""
        self.scene.draw_as_layers(open_dir=True)

    def save_as_video(self) -> None:
        """Save the scene as a video file."""
        self.scene.render(format=VideoFormat.MOV_PRORES, frame_rate=self.frame_rate)
        self.scene._open_folder()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard events."""
        if event.key() == Qt.Key.Key_Right:
            self.increment_frame()
        elif event.key() == Qt.Key.Key_Left:
            self.decrement_frame()
        elif event.key() == Qt.Key.Key_Space:
            self.toggle_play()
        elif event.key() == Qt.Key.Key_Home:
            self.current_frame = 0
            self.update_canvas(self.current_frame)
            self.slider.setValue(self.current_frame)
        elif event.key() == Qt.Key.Key_End:
            self.current_frame = self.scene.num_frames - 1
            self.update_canvas(self.current_frame)
            self.slider.setValue(self.current_frame)

    def increment_frame(self) -> None:
        """Go to the next frame."""
        if self.current_frame < self.scene.num_frames - 1:
            self.current_frame += 1
            self.update_canvas(self.current_frame)
            self.slider.setValue(self.current_frame)

    def decrement_frame(self) -> None:
        """Go to the previous frame."""
        if self.current_frame > 0:
            self.current_frame -= 1
            self.update_canvas(self.current_frame)
            self.slider.setValue(self.current_frame)

    def toggle_play(self) -> None:
        """Start or stop playback."""
        self.playing = not self.playing
        if self.playing:
            self.play_button.setText("⏸️")
            self.update_timer.start(1000 // self.frame_rate)
        else:
            self.play_button.setText("▶️")
            self.update_timer.stop()

    def toggle_loop(self) -> None:
        """Toggle between looping and non-looping playback."""
        self.looping = not self.looping
        self.loop_button.setText("🔁" if self.looping else "➡️")

    def slider_changed(self, value: int) -> None:
        """Handle slider value changes."""
        if not self.playing:
            self.current_frame = value
            self.update_canvas(value)
            self.update_frame_counter()

    def play_animation(self) -> None:
        """Advance to the next frame in animation playback."""
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
        """Update the display with the specified frame.

        Args:
            frame_number: The frame to display
        """
        self.current_frame = frame_number

        # Get frame data from scene
        img_data = self.scene.rasterize(frame_number).get_data()
        qimage = QImage(img_data, self.scene._width, self.scene._height, QImage.Format.Format_ARGB32)

        # Get current label dimensions
        label_width = self.label.width()
        label_height = self.label.height()

        # Calculate scaling to fit the scene while preserving aspect ratio
        scene_aspect = self.scene._width / self.scene._height
        label_aspect = label_width / label_height

        if scene_aspect > label_aspect:
            # Width constrained
            draw_width = label_width
            scale = draw_width / self.scene._width
            draw_height = self.scene._height * scale
            x_offset = 0
            y_offset = (label_height - draw_height) // 2
        else:
            # Height constrained
            draw_height = label_height
            scale = draw_height / self.scene._height
            draw_width = self.scene._width * scale
            x_offset = (label_width - draw_width) // 2
            y_offset = 0

        # Store drawing parameters for mouse coordinate conversion
        self.label.drawing_params = {
            "x_offset": x_offset,
            "y_offset": y_offset,
            "draw_width": draw_width,
            "draw_height": draw_height,
            "scale_x": scale,
            "scale_y": scale,
        }

        # Create a pixmap for drawing
        qpixmap = QPixmap(label_width, label_height)
        qpixmap.fill(Qt.GlobalColor.black)

        with QPainter(qpixmap) as painter:
            # Set rendering quality
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            # Draw scene onto pixmap with letterboxing
            painter.drawImage(
                QRect(int(x_offset), int(y_offset), int(draw_width), int(draw_height)),
                qimage,
                QRect(0, 0, self.scene._width, self.scene._height),
            )

            # Draw guidelines indicating scene boundaries
            if x_offset > 0 or y_offset > 0:
                # Use a semi-transparent gray for the guidelines
                painter.setPen(QPen(Qt.GlobalColor.darkGray, 1, Qt.PenStyle.DashLine))

                # Draw scene dimension text
                # painter.drawText(int(x_offset + 5), int(y_offset + 15), f"{self.scene._width}x{self.scene._height}")

                # Draw guidelines around scene area
                painter.drawRect(int(x_offset), int(y_offset), int(draw_width), int(draw_height))

        self.label.setPixmap(qpixmap)

    def update_frame_counter(self) -> None:
        """Update the frame counter display."""
        self.frame_counter_label.setText(f"Frame: {self.current_frame}/{self.scene.num_frames - 1}")
