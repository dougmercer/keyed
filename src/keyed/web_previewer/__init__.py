"""Browser-based previewer for Keyed scenes."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from keyed import Scene


WEB_PREVIEW_AVAILABLE = importlib.util.find_spec("watchdog") is not None

__all__ = ["WEB_PREVIEW_AVAILABLE", "serve_scene", "serve_scene_file"]


def _raise_unavailable() -> None:
    raise ImportError(
        "watchdog is required for web preview functionality. Install it with: "
        "pip install 'keyed[web-previewer]'"
    )


def serve_scene(
    scene: Scene,
    frame_rate: int = 24,
    host: str | None = None,
    port: int | None = None,
    open_browser: bool | None = None,
) -> None:
    """Serve a scene preview in the browser."""
    if not WEB_PREVIEW_AVAILABLE:
        _raise_unavailable()

    from .server import WebPreviewServer

    WebPreviewServer(
        scene=scene,
        frame_rate=frame_rate,
        host=host,
        port=port,
        open_browser=open_browser,
    ).serve()


def serve_scene_file(
    file_path: Path,
    frame_rate: int = 24,
    host: str | None = None,
    port: int | None = None,
    open_browser: bool | None = None,
) -> None:
    """Serve a live-reloading preview for a scene file."""
    if not WEB_PREVIEW_AVAILABLE:
        _raise_unavailable()

    from .server import WebPreviewServer

    WebPreviewServer.from_file(
        file_path=file_path,
        frame_rate=frame_rate,
        host=host,
        port=port,
        open_browser=open_browser,
    ).serve()
