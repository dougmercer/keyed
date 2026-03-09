import importlib
import os
import subprocess
import sys
from pathlib import Path

import shapely
from signified import Signal

from keyed import Base, Scene
from keyed.cli import _load_keyed_extras_feature_registrations


class _Leaf(Base):
    def __init__(self, scene: Scene) -> None:
        super().__init__(scene)
        self.alpha = Signal(1.0)

    def draw(self) -> None:
        return None

    @property
    def _raw_geom_now(self) -> shapely.Polygon:
        return shapely.box(100, 100, 110, 110)


class _NestedFinder(Base):
    def __init__(self, scene: Scene, target: Base) -> None:
        super().__init__(scene)
        self.alpha = Signal(1.0)
        self.target = target

    def draw(self) -> None:
        return None

    @property
    def _raw_geom_now(self) -> shapely.Polygon:
        return shapely.box(1_000, 1_000, 1_010, 1_010)

    def find(self, x: float, y: float, frame: int) -> tuple[Base, float]:
        return self.target, 0.0


def test_import_keyed_does_not_eagerly_import_keyed_extras(tmp_path: Path) -> None:
    keyed_extras_pkg = tmp_path / "keyed_extras"
    keyed_extras_pkg.mkdir()
    (keyed_extras_pkg / "__init__.py").write_text("raise RuntimeError('keyed_extras should not be imported')\n")

    src_path = Path(__file__).resolve().parents[1] / "src"
    env = os.environ.copy()
    pythonpath = [str(tmp_path), str(src_path)]
    if existing := env.get("PYTHONPATH"):
        pythonpath.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)

    proc = subprocess.run([sys.executable, "-c", "import keyed"], capture_output=True, text=True, env=env)

    assert proc.returncode == 0, proc.stderr


def test_scene_find_supports_nested_findable_objects() -> None:
    scene = Scene()
    leaf = _Leaf(scene)
    nested = _NestedFinder(scene, leaf)

    scene.add(nested)

    assert scene.find(5.0, 6.0) is leaf


def test_load_keyed_extras_feature_registrations_prefers_private_module(monkeypatch) -> None:
    calls: list[str] = []

    def fake_import_module(name: str):
        calls.append(name)
        if name == "keyed_extras._dependencies":
            return object()
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    assert _load_keyed_extras_feature_registrations() is None
    assert calls == ["keyed_extras._dependencies"]


def test_load_keyed_extras_feature_registrations_falls_back_to_legacy_module(monkeypatch) -> None:
    calls: list[str] = []

    def fake_import_module(name: str):
        calls.append(name)
        if name == "keyed_extras._dependencies":
            exc = ModuleNotFoundError("No module named 'keyed_extras._dependencies'")
            exc.name = name
            raise exc
        if name == "keyed_extras.dependencies":
            return object()
        raise AssertionError(f"Unexpected import: {name}")

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    assert _load_keyed_extras_feature_registrations() is None
    assert calls == ["keyed_extras._dependencies", "keyed_extras.dependencies"]
