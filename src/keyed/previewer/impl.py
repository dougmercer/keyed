"""PySide6 Previewer."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QRect, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QImage, QKeyEvent, QMouseEvent, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QSlider,
    QStatusBar,
    QStyle,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from shapely.affinity import affine_transform
from shapely.geometry import Point

from ..config import get_previewer_config
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
            self.coordinates_label.setText("Cursor Outside scene")
            return

        # Convert to scene coordinates
        adjusted_x = mouse_x - x_offset
        adjusted_y = mouse_y - y_offset

        scale_x = self.drawing_params["scale_x"]
        scale_y = self.drawing_params["scale_y"]
        scene_x = adjusted_x / scale_x
        scene_y = adjusted_y / scale_y

        self.coordinates_label.setText(f"Cursor Position in Scene: ({scene_x:.1f}, {scene_y:.1f})")

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

    def __init__(self, scene: Scene, frame_rate: int = 24):
        super().__init__()
        self.scene = scene
        self.frame_rate = frame_rate
        self.current_frame = 0
        self.playing = False
        self.looping = False

        # Get previewer configuration
        self.config = get_previewer_config()

        # Calculate initial display dimensions
        self.calculate_display_dimensions()

        self.init_ui()

    def calculate_display_dimensions(self) -> None:
        """Calculate appropriate display dimensions based on scene size and config."""
        # Get scene dimensions
        scene_width = self.scene._width
        scene_height = self.scene._height
        scene_aspect = scene_width / scene_height

        # Get config values
        default_width = self.config.get("default_width", 1280)
        default_height = self.config.get("default_height", 720)
        min_width = self.config.get("min_width", 640)
        min_height = self.config.get("min_height", 360)

        # Target dimensions - use default size from config
        target_width = max(min_width, default_width)
        target_height = max(min_height, default_height)

        # Adjust dimensions to maintain aspect ratio
        if scene_aspect > target_width / target_height:
            # Width is the constraint
            self.display_width = target_width
            self.display_height = int(target_width / scene_aspect)
        else:
            # Height is the constraint
            self.display_height = target_height
            self.display_width = int(target_height * scene_aspect)

        # Make sure we're respecting minimum dimensions
        self.display_width = max(min_width, self.display_width)
        self.display_height = max(min_height, self.display_height)

    def init_ui(self) -> None:
        """Initialize the user interface with improved controls."""
        self.setWindowTitle(f"Keyed Previewer - {self.scene.scene_name or 'Untitled'}")

        # Set initial window size
        window_width = self.display_width + 40
        window_height = self.display_height + 100
        self.resize(window_width, window_height)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        self.central_widget.setLayout(layout)

        # Menu bar setup
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        playback_menu = menu_bar.addMenu("Playback")

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

        # View menu for frame rate options
        framerate_menu = playback_menu.addMenu("Frame Rate")
        framerate_group = QActionGroup(self)
        framerate_group.setExclusive(True)

        for rate in [24, 30, 60]:
            action = QAction(f"{rate} fps", self)
            action.setCheckable(True)
            action.setChecked(rate == self.frame_rate)
            action.triggered.connect(lambda checked, r=rate: self.set_frame_rate(r))
            framerate_group.addAction(action)
            framerate_menu.addAction(action)

        # Scene info in status bar
        status_bar = self.statusBar()
        status_bar.showMessage(f"Scene: {self.scene._width}x{self.scene._height} px, {self.scene.num_frames} frames")
        self.fps_label = QLabel(f"Playback: {self.frame_rate} fps")
        status_bar.addPermanentWidget(self.fps_label)

        # Scene display
        self.label = InteractiveLabel(self.scene)
        layout.addWidget(self.label)

        # Timeline slider container
        slider_container = QFrame()
        slider_container.setFrameShape(QFrame.Shape.StyledPanel)
        slider_container.setStyleSheet("QFrame { background-color: #333; border-radius: 4px; }")

        slider_layout = QHBoxLayout()
        slider_layout.setContentsMargins(8, 4, 8, 4)
        slider_container.setLayout(slider_layout)

        # Improved timeline slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMaximum(self.scene.num_frames - 1)
        self.slider.valueChanged.connect(self.slider_changed)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #555;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                border: 2px solid #2980b9;
                width: 18px;
                height: 18px;
                margin: -6px 0;
                border-radius: 9px;
            }
            QSlider::sub-page:horizontal {
                background: #2980b9;
                border-radius: 4px;
            }
        """)
        self.slider.setMinimumHeight(24)
        slider_layout.addWidget(self.slider, 1)

        # Frame counter - now placed to the right of slider
        self.frame_counter_label = QLabel("0/119")
        self.frame_counter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # Calculate max width needed for largest possible frame count
        max_frame_text = f"{self.scene.num_frames - 1}/{self.scene.num_frames - 1}"
        self.frame_counter_label.setMinimumWidth(self.fontMetrics().horizontalAdvance(max_frame_text) + 24)
        self.frame_counter_label.setStyleSheet("""
            QLabel {
                background-color: #2c2c2c;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 10px;
                font-family: monospace;
                font-size: 14px;
                font-weight: bold;
                color: white;
            }
        """)
        slider_layout.addWidget(self.frame_counter_label)

        layout.addWidget(slider_container)

        # Playback controls in a horizontal layout
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the controls

        # Create combined container for playback controls
        play_controls_container = QWidget()
        play_controls_layout = QHBoxLayout()
        play_controls_layout.setContentsMargins(0, 0, 0, 0)
        play_controls_layout.setSpacing(4)
        play_controls_container.setLayout(play_controls_layout)

        # Skip to start button
        self.start_button = QPushButton()
        self.start_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.start_button.clicked.connect(self.jump_to_start)
        self.start_button.setFixedSize(36, 36)
        self.start_button.setIconSize(QSize(16, 16))
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #444;
                border-radius: 18px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        play_controls_layout.addWidget(self.start_button)

        # Play/Pause button
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_button.clicked.connect(self.toggle_play)
        self.play_button.setFixedSize(48, 48)
        self.play_button.setIconSize(QSize(24, 24))
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border-radius: 24px;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        play_controls_layout.addWidget(self.play_button)

        # Skip to end button
        self.end_button = QPushButton()
        self.end_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self.end_button.clicked.connect(self.jump_to_end)
        self.end_button.setFixedSize(36, 36)
        self.end_button.setIconSize(QSize(16, 16))
        self.end_button.setStyleSheet("""
            QPushButton {
                background-color: #444;
                border-radius: 18px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #555;
            }
        """)
        play_controls_layout.addWidget(self.end_button)

        control_layout.addWidget(play_controls_container)
        control_layout.addSpacing(24)

        # Loop button separate from media controls
        self.loop_button = QPushButton()
        self.loop_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.loop_button.clicked.connect(self.toggle_loop)
        self.loop_button.setFixedSize(36, 36)
        self.loop_button.setIconSize(QSize(16, 16))
        self.loop_button.setCheckable(True)
        self.loop_button.setStyleSheet("""
            QPushButton {
                background-color: #444;
                border-radius: 18px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:checked {
                background-color: #2980b9;
            }
        """)
        control_layout.addWidget(self.loop_button)

        layout.addLayout(control_layout)

        # Enhanced status bar with cursor position
        status_bar = QStatusBar()
        status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #2c2c2c;
                color: #aaa;
            }
            QStatusBar::item {
                border: none;
            }
        """)

        # Left side status message
        status_bar.showMessage(f"Scene: {self.scene._width}x{self.scene._height} px, {self.scene.num_frames} frames")

        # Middle section for cursor position
        self.coordinates_label = QLabel("Cursor Outside scene")
        self.coordinates_label.setStyleSheet("color: #aaa; padding-right: 15px;")
        status_bar.addPermanentWidget(self.coordinates_label)

        # Right side for fps display
        self.fps_label = QLabel(f"Playback: {self.frame_rate} fps")
        self.fps_label.setStyleSheet("color: #aaa;")
        status_bar.addPermanentWidget(self.fps_label)

        self.setStatusBar(status_bar)
        self.label.set_coordinates_label(self.coordinates_label)

        # Animation timer
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.play_animation)

        # Initialize display
        self.update_canvas(0)
        self.update_frame_counter()
        self.toggle_loop()  # Enable looping by default

    def set_frame_rate(self, rate: int) -> None:
        """Change the playback frame rate.

        Args:
            rate: The new frame rate to use (frames per second)
        """
        self.frame_rate = rate
        self.fps_label.setText(f"{self.frame_rate} fps")

        # Update the timer if currently playing
        if self.playing:
            self.update_timer.start(1000 // self.frame_rate)

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

    def jump_to_start(self):
        """Jump to the first frame."""
        self.current_frame = 0
        self.update_canvas(self.current_frame)
        self.slider.setValue(self.current_frame)

    def jump_to_end(self):
        """Jump to the last frame."""
        self.current_frame = self.scene.num_frames - 1
        self.update_canvas(self.current_frame)
        self.slider.setValue(self.current_frame)

    def toggle_play(self) -> None:
        """Start or stop playback."""
        self.playing = not self.playing
        if self.playing:
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
            self.update_timer.start(1000 // self.frame_rate)
        else:
            self.play_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
            self.update_timer.stop()

    def toggle_loop(self) -> None:
        """Toggle between looping and non-looping playback."""
        self.looping = not self.looping
        self.loop_button.setChecked(self.looping)
        if self.looping:
            self.loop_button.setStyleSheet("""
                QPushButton {
                    background-color: #2980b9;
                    border-radius: 18px;
                    padding: 6px;
                }
                QPushButton:hover {
                    background-color: #3498db;
                }
            """)
        else:
            self.loop_button.setStyleSheet("""
                QPushButton {
                    background-color: #444;
                    border-radius: 18px;
                    padding: 6px;
                }
                QPushButton:hover {
                    background-color: #555;
                }
            """)

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

        # Calculate scaling
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
        """Update the frame counter display with improved formatting."""
        self.frame_counter_label.setText(f"{self.current_frame}/{self.scene.num_frames - 1}")
