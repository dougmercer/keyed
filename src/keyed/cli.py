import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .constants import Quality
from .previewer import FileWatcher, LiveReloadWindow, SceneEvaluator


def main():
    """Main entry point for the scene viewer CLI."""
    parser = argparse.ArgumentParser(description="Live-reloading scene viewer")
    parser.add_argument("file", type=Path, help="Python file containing a Scene definition")
    parser.add_argument("--frame-rate", type=int, default=24, help="Frame rate for playback")
    parser.add_argument(
        "--quality", type=str, choices=["low", "medium", "high", "very_high"], default="high", help="Render quality"
    )
    args = parser.parse_args()

    if not args.file.exists():
        print(f"File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    # Initialize scene evaluator
    evaluator = SceneEvaluator()

    # Get initial scene
    scene = evaluator.evaluate_file(args.file)
    if not scene:
        print(f"No Scene object found in {args.file}", file=sys.stderr)
        sys.exit(1)

    # Create application and window
    app = QApplication(sys.argv)
    quality = getattr(Quality, args.quality).value
    window = LiveReloadWindow(scene, quality=quality, frame_rate=args.frame_rate)
    window.show()

    # Setup file watcher
    watcher = FileWatcher(args.file)

    def handle_file_changed():
        """Handle updates to the scene file."""
        if new_scene := evaluator.evaluate_file(args.file):
            window.update_scene(new_scene)

    watcher.file_changed.connect(handle_file_changed)
    watcher.start()

    try:
        exit_code = app.exec()
    finally:
        watcher.stop()

    sys.exit(exit_code)
