"""File watching helpers for the browser previewer."""

from __future__ import annotations

from pathlib import Path
from threading import Lock, Timer
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class WebFileWatcher:
    """Watch a single scene file and invoke a callback on changes."""

    def __init__(self, file_path: Path, callback: Callable[[], None], debounce_seconds: float = 0.2) -> None:
        self.file_path = file_path.resolve()
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self.observer = Observer()
        self._timer: Timer | None = None
        self._lock = Lock()

    def start(self) -> None:
        """Start watching the scene file."""
        handler = _SceneFileHandler(self.file_path, self._trigger_callback)
        self.observer.schedule(handler, str(self.file_path.parent), recursive=False)
        self.observer.start()

    def stop(self) -> None:
        """Stop watching the scene file."""
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        self.observer.stop()
        self.observer.join()

    def _trigger_callback(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = Timer(self.debounce_seconds, self.callback)
            self._timer.daemon = True
            self._timer.start()


class _SceneFileHandler(FileSystemEventHandler):
    def __init__(self, file_path: Path, callback: Callable[[], None]) -> None:
        self.file_path = file_path
        self.callback = callback

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and Path(event.src_path).resolve() == self.file_path:
            self.callback()

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and Path(event.src_path).resolve() == self.file_path:
            self.callback()
