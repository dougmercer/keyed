from pathlib import Path

import pytest

from keyed import Scene
from keyed.web_previewer.server import PreviewState


def test_scene_preview_uses_native_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Scene, int]] = []

    monkeypatch.setattr(
        "keyed.previewer.create_animation_window",
        lambda scene, frame_rate=24: calls.append((scene, frame_rate)),
    )

    scene = Scene(scene_name="native", num_frames=1, output_dir=Path("/tmp"), width=100, height=100)
    scene.preview(frame_rate=30)

    assert calls == [(scene, 30)]


def test_scene_preview_uses_web_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[Scene, int, str | None, int | None, bool | None]] = []

    monkeypatch.setattr(
        "keyed.web_previewer.serve_scene",
        lambda scene, frame_rate=24, host=None, port=None, open_browser=None: calls.append(
            (scene, frame_rate, host, port, open_browser)
        ),
    )

    scene = Scene(scene_name="web", num_frames=1, output_dir=Path("/tmp"), width=100, height=100)
    scene.preview(frame_rate=12, backend="web", host="0.0.0.0", port=9000, open_browser=False)

    assert calls == [(scene, 12, "0.0.0.0", 9000, False)]


def test_scene_preview_rejects_unknown_backend() -> None:
    scene = Scene(scene_name="bad", num_frames=1, output_dir=Path("/tmp"), width=100, height=100)

    with pytest.raises(ValueError, match="Unknown preview backend: bad-backend"):
        scene.preview(backend="bad-backend")


def test_web_preview_state_resolves_tempdir_symlinks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    real_tempdir = tmp_path / "real-tempdir"
    real_tempdir.mkdir()
    symlink_tempdir = tmp_path / "symlink-tempdir"
    symlink_tempdir.symlink_to(real_tempdir, target_is_directory=True)

    monkeypatch.setattr("tempfile.mkdtemp", lambda prefix="": str(symlink_tempdir))

    scene = Scene(scene_name="web", num_frames=1, output_dir=tmp_path, width=100, height=100)
    state = PreviewState(scene, frame_rate=24)
    version = state.snapshot().version

    frame_path = state.get_frame_path(version, 0)

    assert frame_path is not None
    assert frame_path.exists()
    assert frame_path.parent == state._tempdir / f"frames-v{version}"


def test_web_preview_state_rejects_stale_version(tmp_path: Path) -> None:
    scene = Scene(scene_name="web", num_frames=2, output_dir=tmp_path, width=100, height=100)
    state = PreviewState(scene, frame_rate=24)

    assert state.get_frame_path(state.snapshot().version + 1, 0) is None


def test_web_preview_state_uses_session_scoped_frame_urls(tmp_path: Path) -> None:
    scene_a = Scene(scene_name="web-a", num_frames=2, output_dir=tmp_path, width=100, height=100)
    scene_b = Scene(scene_name="web-b", num_frames=2, output_dir=tmp_path, width=100, height=100)

    state_a = PreviewState(scene_a, frame_rate=24)
    state_b = PreviewState(scene_b, frame_rate=24)

    payload_a = state_a.snapshot().to_payload()
    payload_b = state_b.snapshot().to_payload()

    assert payload_a["frame_base_url"].startswith("/frames/")
    assert payload_a["frame_base_url"].endswith("/1")
    assert payload_a["frame_base_url"] != payload_b["frame_base_url"]
