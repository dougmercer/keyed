import ast
from pathlib import Path

from .scene import Scene

__all__ = ["SceneEvaluator"]


class SceneEvaluator:
    """Evaluates Python files and extracts Scene objects."""

    def __init__(self, globals_dict: dict | None = None):
        from keyed import Scene

        self.globals = globals_dict or {}
        # Add necessary imports to globals
        self.globals.update(
            {
                "Scene": Scene,
            }
        )

    def evaluate_file(self, file_path: Path) -> Scene:
        """Evaluate a Python file and return the first Scene object found.

        Args:
            file_path: Path to the Python file to evaluate

        Returns:
            The first Scene object found in the file, or None if no scene is found

        Raises:
            RuntimeError: When a scene object is not found.
        """
        from keyed import Scene

        with open(file_path) as f:
            file_content = f.read()

        # Parse the AST to look for Scene assignments
        tree = ast.parse(file_content)

        # Execute the file in our controlled globals
        exec(compile(tree, filename=str(file_path), mode="exec"), self.globals)

        # Look for Scene instances in the globals
        for var_value in self.globals.values():
            if isinstance(var_value, Scene):
                return var_value
        else:
            raise RuntimeError("Scene not found.")
