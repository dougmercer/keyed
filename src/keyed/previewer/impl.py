"""PySide6 Previewer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QImage, QKeyEvent, QMouseEvent, QPainter, QPixmap, QResizeEvent
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

from ..constants import Quality
from ..renderer import VideoFormat

if TYPE_CHECKING:
    from keyed import Base, Scene


def get_object_info(scene: Scene, x: float, y: float, frame: int) -> Base | None:
    """Find an object at the given point in the scene.

    Args:
        scene: The scene to search in
        x: X coordinate in scene space
        y: Y coordinate in scene space
        frame: Current frame

    Returns:
        The found object or None
    """
    # Transform point based on scene's transformation matrix
    matrix = scene.controls.matrix.value
    if matrix is None or (invert := matrix.invert()) is None:
        transformed_x, transformed_y = x, y
    else:
        transformed_x, transformed_y = affine_transform(Point(x, y), invert).coords[0]  # type: ignore

    return scene.find(transformed_x, transformed_y, frame)


class InteractiveLabel(QLabel):
    """An interactive label that displays the scene and handles mouse events."""

    def __init__(
        self,
        scene: Scene,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: transparent;")  # Transparent background
        self.coordinates_label: QLabel | None = None
        self.scene = scene
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 100)  # Minimum viable size

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
        # 1. Adjust for centering offset
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
        nearest = get_object_info(window.scene, x, y, window.current_frame)
        return repr(nearest) if nearest else "No object found"


class MainWindow(QMainWindow):
    """Main window for the previewer application."""

    def __init__(self, scene: Scene, quality: Quality = Quality.high, frame_rate: int = 24):
        super().__init__()
        self.scene = scene
        self.quality = quality
        self.frame_rate = frame_rate
        self.current_frame = 0
        self.playing = False
        self.looping = False

        # Calculate the display dimensions based on the quality scale factor
        self.display_width, self.display_height = quality.get_scaled_dimensions(scene._width, scene._height)

        self.init_ui()

    def init_ui(self) -> None:
        """Initialize the user interface."""
        self.setWindowTitle(f"Keyed Previewer - {self.scene.scene_name or 'Untitled'}")

        # Set initial window size based on the scaled dimensions plus some margin for controls
        window_width = self.display_width + 40  # Add margin for window borders
        window_height = self.display_height + 120  # Add space for controls
        self.resize(window_width, window_height)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()
        self.central_widget.setLayout(layout)

        # Menu bar setup
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        view_menu = menu_bar.addMenu("View")

        # File menu actions
        save_images_action = QAction("Save As Images", self)
        save_images_action.triggered.connect(self.save_as_images)
        file_menu.addAction(save_images_action)

        save_layers_action = QAction("Save Layers As Images", self)
        save_layers_action.triggered.connect(self.save_layers_as_images)
        file_menu.addAction(save_layers_action)

        save_video_action = QAction("Save as Video", self)
        save_video_action.triggered.connect(self.save_as_video)
        file_menu.addAction(save_video_action)

        # View menu for quality options
        quality_group = QActionGroup(self)
        quality_group.setExclusive(True)

        for q in Quality:
            action = QAction(f"{q.name.replace('_', ' ').title()} ({int(q.value * 100)}%)", self)
            action.setCheckable(True)
            action.setChecked(q == self.quality)
            action.triggered.connect(lambda checked, q=q: self.set_quality(q))
            quality_group.addAction(action)
            view_menu.addAction(action)

        # Scene info in status bar
        self.statusBar().showMessage(
            f"Scene: {self.scene._width}x{self.scene._height} px, {self.scene.num_frames} frames"
        )

        # Image display
        self.label = InteractiveLabel(self.scene)
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

        # Display info label
        self.display_info_label = QLabel(
            f"{self.display_width}x{self.display_height} ({int(self.quality.value * 100)}%)"
        )
        bottom_layout.addWidget(self.display_info_label)

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

    def set_quality(self, quality: Quality) -> None:
        """Change the display quality/scale.

        Args:
            quality: The new quality setting to use
        """
        self.quality = quality

        # Recalculate display dimensions
        self.display_width, self.display_height = quality.get_scaled_dimensions(self.scene._width, self.scene._height)

        # Update the display info label
        self.display_info_label.setText(
            f"{self.display_width}x{self.display_height} ({int(self.quality.value * 100)}%)"
        )

        # Update the display with current frame
        self.update_canvas(self.current_frame)

        # Optionally resize the window to better fit the new dimensions
        window_width = self.display_width + 40
        window_height = self.display_height + 120
        self.resize(window_width, window_height)

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

        # Calculate the target size for rendering the scene (based on our quality setting)
        target_width = self.display_width
        target_height = self.display_height

        # Fit the target size within the label while preserving aspect ratio
        scene_aspect = target_width / target_height
        label_aspect = label_width / label_height

        if scene_aspect > label_aspect:
            # Width constrained
            draw_width = label_width
            scale = draw_width / target_width
            draw_height = target_height * scale
            x_offset = 0
            y_offset = (label_height - draw_height) // 2
        else:
            # Height constrained
            draw_height = label_height
            scale = draw_height / target_height
            draw_width = target_width * scale
            x_offset = (label_width - draw_width) // 2
            y_offset = 0

        # Calculate scale factors from scene coordinates to display coordinates
        scale_x = draw_width / self.scene._width
        scale_y = draw_height / self.scene._height

        # Store drawing parameters for mouse coordinate conversion
        self.label.drawing_params = {
            "x_offset": x_offset,
            "y_offset": y_offset,
            "draw_width": draw_width,
            "draw_height": draw_height,
            "scale_x": scale_x,
            "scale_y": scale_y,
        }

        # Create a pixmap exactly the size of the draw area (not the entire label)
        # This way the black rectangle will only be as big as the scene
        qpixmap = QPixmap(int(draw_width), int(draw_height))
        qpixmap.fill(Qt.GlobalColor.black)

        with QPainter(qpixmap) as painter:
            # Set rendering quality
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

            # Draw scene onto pixmap - now filling the entire pixmap
            painter.drawImage(
                QRect(0, 0, int(draw_width), int(draw_height)),
                qimage,
                QRect(0, 0, self.scene._width, self.scene._height),
            )

        # Create a full-size pixmap for the label with transparent background
        label_pixmap = QPixmap(label_width, label_height)
        label_pixmap.fill(Qt.GlobalColor.transparent)

        # Draw the scene pixmap onto the label pixmap at the correct position
        with QPainter(label_pixmap) as painter:
            painter.drawPixmap(int(x_offset), int(y_offset), qpixmap)

        self.label.setPixmap(label_pixmap)

    def update_frame_counter(self) -> None:
        """Update the frame counter display."""
        self.frame_counter_label.setText(f"Frame: {self.current_frame}/{self.scene.num_frames - 1}")
