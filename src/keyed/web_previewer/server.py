"""HTTP server for the browser previewer."""

from __future__ import annotations

import json
import logging
import queue
import shutil
import tempfile
import threading
import webbrowser
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from PIL import Image

from ..config import get_web_previewer_config
from ..parser import SceneEvaluator
from .filewatch import WebFileWatcher

if TYPE_CHECKING:
    from ..scene import Scene


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RenderSnapshot:
    status: str
    version: int
    scene_name: str | None
    width: int
    height: int
    num_frames: int
    frame_rate: int
    error: str | None
    session_id: str

    def to_payload(self) -> dict[str, object]:
        return {
            "status": self.status,
            "version": self.version,
            "scene_name": self.scene_name,
            "width": self.width,
            "height": self.height,
            "num_frames": self.num_frames,
            "frame_rate": self.frame_rate,
            "error": self.error,
            "frame_base_url": f"/frames/{self.session_id}/{self.version}",
        }


class PreviewState:
    """Manage scene state and on-demand frame rendering."""

    def __init__(self, scene: Scene, frame_rate: int) -> None:
        self.scene = scene
        self.frame_rate = frame_rate
        self._state_lock = threading.Lock()
        self._render_lock = threading.Lock()
        self._tempdir = Path(tempfile.mkdtemp(prefix="keyed-web-preview-")).resolve()
        self._session_id = uuid4().hex
        self._version = 1
        self._status = "ready"
        self._error: str | None = None
        self._prefetch_queue: queue.Queue[tuple[int, int]] = queue.Queue()
        self._queued_frames: set[tuple[int, int]] = set()
        self._queue_lock = threading.Lock()
        self._stop_event = threading.Event()
        self._worker = threading.Thread(target=self._prefetch_worker, daemon=True)
        self._worker.start()
        self._frame_dir(self._version).mkdir(parents=True, exist_ok=True)

    def snapshot(self) -> RenderSnapshot:
        with self._state_lock:
            scene = self.scene
            return RenderSnapshot(
                status=self._status,
                version=self._version,
                scene_name=scene.scene_name,
                width=scene._width,
                height=scene._height,
                num_frames=scene.num_frames,
                frame_rate=self.frame_rate,
                error=self._error,
                session_id=self._session_id,
            )

    def set_scene(self, scene: Scene) -> None:
        with self._state_lock:
            self.scene = scene
            self._version += 1
            self._status = "ready"
            self._error = None
            self._frame_dir(self._version).mkdir(parents=True, exist_ok=True)
        with self._queue_lock:
            self._queued_frames.clear()

    def set_error(self, error: str) -> None:
        with self._state_lock:
            self._status = "error"
            self._error = error

    def get_frame_path(self, version: int, frame_index: int) -> Path | None:
        """Return a rendered frame, rendering it synchronously if needed."""
        with self._state_lock:
            if version != self._version:
                return None
            scene = self.scene
            if frame_index < 0 or frame_index >= scene.num_frames:
                return None
            frame_path = self._frame_path(version, frame_index)

        if frame_path.exists():
            return frame_path

        with self._render_lock:
            if frame_path.exists():
                return frame_path
            try:
                rgba = Image.frombytes(
                    "RGBA",
                    (scene._width, scene._height),
                    scene.asarray(frame_index).tobytes(),
                    "raw",
                    "BGRA",
                )
                rgba.save(frame_path, format="PNG")
            except Exception as exc:
                logger.exception("Failed to render frame %s", frame_index)
                self.set_error(str(exc))
                return None

        return frame_path

    def schedule_prefetch(self, version: int, start: int, end: int) -> None:
        """Schedule a batch of frames to render in the background."""
        with self._state_lock:
            if version != self._version:
                return
            num_frames = self.scene.num_frames

        clamped_start = max(0, start)
        clamped_end = min(num_frames - 1, end)
        if clamped_end < clamped_start:
            return

        for frame_index in range(clamped_start, clamped_end + 1):
            frame_key = (version, frame_index)
            if self._frame_path(version, frame_index).exists():
                continue
            with self._queue_lock:
                if frame_key in self._queued_frames:
                    continue
                self._queued_frames.add(frame_key)
            self._prefetch_queue.put(frame_key)

    def cleanup(self) -> None:
        self._stop_event.set()
        self._worker.join(timeout=1)
        shutil.rmtree(self._tempdir, ignore_errors=True)

    def _prefetch_worker(self) -> None:
        while not self._stop_event.is_set():
            try:
                version, frame_index = self._prefetch_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            try:
                self.get_frame_path(version, frame_index)
            finally:
                with self._queue_lock:
                    self._queued_frames.discard((version, frame_index))
                self._prefetch_queue.task_done()

    def _frame_dir(self, version: int) -> Path:
        return self._tempdir / f"frames-v{version}"

    def _frame_path(self, version: int, frame_index: int) -> Path:
        return self._frame_dir(version) / f"{frame_index}.png"


class PreviewRequestHandler(BaseHTTPRequestHandler):
    server: "PreviewHttpServer"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)

        if parsed.path in {"/", "/index.html"}:
            self._send_html(self.server.preview_server.index_html)
            return

        if parsed.path == "/state":
            payload = self.server.preview_server.state.snapshot().to_payload()
            self._send_json(payload)
            return

        if parsed.path == "/prefetch":
            self._handle_prefetch(parsed)
            return

        if parsed.path.startswith("/frames/"):
            self._handle_frame_request(parsed.path)
            return

        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        logger.debug(format, *args)

    def _handle_frame_request(self, path: str) -> None:
        parts = path.strip("/").split("/")
        snapshot = self.server.preview_server.state.snapshot()
        if len(parts) != 4 or parts[1] != snapshot.session_id:
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        if not parts[2].isdigit() or not parts[3].endswith(".png"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        version = int(parts[2])
        frame_stem = parts[3][:-4]
        if not frame_stem.isdigit():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        frame_index = int(frame_stem)
        frame_path = self.server.preview_server.state.get_frame_path(version, frame_index)
        if frame_path is None or not frame_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        self._send_file(frame_path, "image/png")

    def _handle_prefetch(self, parsed) -> None:
        query = parse_qs(parsed.query)
        try:
            version = int(query.get("version", ["0"])[0])
            start = int(query.get("start", ["0"])[0])
            end = int(query.get("end", [str(start)])[0])
        except ValueError:
            self.send_error(HTTPStatus.BAD_REQUEST)
            return

        self.server.preview_server.state.schedule_prefetch(version, start, end)
        self._send_json({"status": "queued", "version": version, "start": start, "end": end})

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class PreviewHttpServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], preview_server: "WebPreviewServer") -> None:
        super().__init__(server_address, PreviewRequestHandler)
        self.preview_server = preview_server


class WebPreviewServer:
    def __init__(
        self,
        scene: Scene,
        frame_rate: int = 24,
        host: str | None = None,
        port: int | None = None,
        open_browser: bool | None = None,
        file_path: Path | None = None,
    ) -> None:
        config = get_web_previewer_config()
        self.state = PreviewState(scene, frame_rate=frame_rate)
        self.host = host or config["host"]
        self.port = int(port if port is not None else config["port"])
        self.open_browser = config["open_browser"] if open_browser is None else open_browser
        self.poll_interval_ms = int(config["poll_interval_ms"])
        self.file_path = file_path.resolve() if file_path is not None else None
        self._watcher: WebFileWatcher | None = None
        self._evaluator = SceneEvaluator() if self.file_path is not None else None
        self._shutdown_lock = threading.Lock()
        self._is_closed = False

        if self.file_path is not None and self._evaluator is None:
            raise RuntimeError("Web preview server was created without a scene evaluator.")

        self.http_server = PreviewHttpServer((self.host, self.port), self)

    @property
    def index_html(self) -> str:
        template = (Path(__file__).parent / "static" / "index.html").read_text("utf-8")
        return template.replace("__POLL_INTERVAL_MS__", str(self.poll_interval_ms))

    @classmethod
    def from_file(
        cls,
        file_path: Path,
        frame_rate: int = 24,
        host: str | None = None,
        port: int | None = None,
        open_browser: bool | None = None,
    ) -> "WebPreviewServer":
        evaluator = SceneEvaluator()
        try:
            scene = evaluator.evaluate_file(file_path)
        except Exception as exc:
            raise RuntimeError(f"Failed to evaluate {file_path}: {exc}") from exc

        server = cls(
            scene=scene,
            frame_rate=frame_rate,
            host=host,
            port=port,
            open_browser=open_browser,
            file_path=file_path,
        )
        server._evaluator = evaluator
        return server

    def serve(self) -> None:
        self.state.schedule_prefetch(self.state.snapshot().version, 0, 8)

        if self.file_path is not None:
            self._watcher = WebFileWatcher(self.file_path, self._reload_scene)
            self._watcher.start()

        url = f"http://{self.host}:{self.port}"
        logger.info("Serving web preview at %s", url)
        print(f"Serving web preview at {url}")

        if self.open_browser:
            webbrowser.open(url)

        try:
            self.http_server.serve_forever(poll_interval=0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.close()

    def close(self) -> None:
        """Release all resources owned by the preview server."""
        with self._shutdown_lock:
            if self._is_closed:
                return
            self._is_closed = True

        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None
        self.http_server.server_close()
        self.state.cleanup()

    def _reload_scene(self) -> None:
        if self.file_path is None or self._evaluator is None:
            return

        try:
            new_scene = self._evaluator.evaluate_file(self.file_path)
        except Exception as exc:
            self.state.set_error(f"Failed to evaluate {self.file_path.name}: {exc}")
            return

        self.state.set_scene(new_scene)
        self.state.schedule_prefetch(self.state.snapshot().version, 0, 8)
