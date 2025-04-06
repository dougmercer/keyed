"""PySide6 Previewer."""

from __future__ import annotations

import importlib.util
import sys
from typing import TYPE_CHECKING, NoReturn

from ..constants import Quality

if TYPE_CHECKING:
    from keyed import Scene


# Check if PySide6 is available
PREVIEW_AVAILABLE = importlib.util.find_spec("PySide6") is not None and importlib.util.find_spec("watchdog") is not None


__all__ = ["create_animation_window", "PREVIEW_AVAILABLE"]


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

    from PySide6.QtWidgets import QApplication

    from .impl import MainWindow

    app = QApplication(sys.argv)  # type: ignore
    window = MainWindow(scene, quality=quality.value, frame_rate=frame_rate)
    window.show()
    sys.exit(app.exec())


if PREVIEW_AVAILABLE:
    from .filewatch import FileWatcher, LiveReloadWindow  # noqa: F401
