import ast
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .scene import Scene

__all__ = ["SceneEvaluator"]


class SceneEvaluator:
    """Evaluates Python files and extracts Scene objects."""

    def __init__(self, globals_dict: dict[str, object] | None = None):
        self.base_globals: dict[str, object] = {"Scene": Scene}
        if globals_dict is not None:
            self.base_globals.update(globals_dict)
        self.globals: dict[str, object] = dict(self.base_globals)

    @staticmethod
    @contextmanager
    def _scene_sys_path(scene_dir: Path) -> Iterator[None]:
        scene_dir_str = str(scene_dir)
        sys.path.insert(0, scene_dir_str)
        try:
            yield
        finally:
            if sys.path and sys.path[0] == scene_dir_str:
                sys.path.pop(0)
            else:
                try:
                    sys.path.remove(scene_dir_str)
                except ValueError:
                    pass

    def _build_globals(self, file_path: Path) -> dict[str, object]:
        globals_dict = dict(self.base_globals)
        globals_dict.update(
            {
                "__cached__": None,
                "__doc__": None,
                "__file__": str(file_path),
                "__loader__": None,
                "__name__": file_path.stem,
                "__package__": "",
                "__spec__": None,
            }
        )
        return globals_dict

    def evaluate_file(self, file_path: Path) -> Scene:
        """Evaluate a Python file and return the first Scene object found.

        Args:
            file_path: Path to the Python file to evaluate

        Returns:
            The first Scene object found in the file, or None if no scene is found

        Raises:
            RuntimeError: When a scene object is not found.
        """
        file_path = file_path.resolve()

        with open(file_path) as f:
            file_content = f.read()

        tree = ast.parse(file_content, filename=str(file_path))
        exec_globals = self._build_globals(file_path)

        with self._scene_sys_path(file_path.parent):
            exec(compile(tree, filename=str(file_path), mode="exec"), exec_globals)

        self.globals = exec_globals

        # Look for Scene instances in the globals from the current evaluation.
        for var_value in exec_globals.values():
            if isinstance(var_value, Scene):
                return var_value
        else:
            raise RuntimeError("Scene not found.")
