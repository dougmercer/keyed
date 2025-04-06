from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Signal
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from .impl import MainWindow

if TYPE_CHECKING:
    from ..scene import Scene


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
