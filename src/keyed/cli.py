"""Command line interface for Keyed animations."""

import sys
from enum import Enum
from pathlib import Path

import typer

from keyed.constants import Quality, QualitySetting
from keyed.parser import SceneEvaluator

app = typer.Typer()


def main():
    cli()


class QualityChoices(str, Enum):
    very_low = "very_low"
    low = "low"
    medium = "medium"
    high = "high"
    very_high = "very_high"


class OutputFormat(str, Enum):
    WEBM = "webm"
    MOV = "mov"
    GIF = "gif"


def cli():
    """Entry point for the CLI that handles direct file paths."""
    if len(sys.argv) > 1 and sys.argv[1] not in ["preview", "render", "--help"]:
        sys.argv[1:1] = ["preview"]  # Insert 'preview' command before the file path
    return app()


@app.callback(no_args_is_help=True)
def callback(ctx: typer.Context):
    """Keyed animation preview and rendering tool."""
    if ctx.invoked_subcommand is None:
        ctx.get_help()
        ctx.exit()


@app.command()
def preview(
    file: Path = typer.Argument(..., help="Python file containing a Scene definition"),
    frame_rate: int = typer.Option(24, "--frame-rate", "-f", help="Frame rate for playback"),
    quality: QualityChoices = typer.Option(
        "high", "--quality", "-q", help="Render quality: very_low, low, medium, high, very_high"
    ),
) -> None:
    """Preview a scene in a live-reloading window."""
    from PySide6.QtWidgets import QApplication

    from keyed.previewer import FileWatcher, LiveReloadWindow

    if not file.exists():
        typer.echo(f"File not found: {file}", err=True)
        raise typer.Exit(1)
    q: QualitySetting = getattr(Quality, quality).value

    # Initialize scene evaluator
    evaluator = SceneEvaluator()

    # Get initial scene
    scene = evaluator.evaluate_file(file)
    if not scene:
        typer.echo(f"No Scene object found in {file}", err=True)
        raise typer.Exit(1)

    # Create application and window
    app = QApplication(sys.argv)
    window = LiveReloadWindow(scene, quality=q, frame_rate=frame_rate)
    window.show()

    # Setup file watcher
    watcher = FileWatcher(file)

    def handle_file_changed():
        """Handle updates to the scene file."""
        if new_scene := evaluator.evaluate_file(file):
            window.update_scene(new_scene)

    watcher.file_changed.connect(handle_file_changed)
    watcher.start()

    try:
        exit_code = app.exec()
    finally:
        watcher.stop()

    raise typer.Exit(exit_code)


@app.command()
def render(
    file: Path = typer.Argument(..., help="Python file containing a Scene definition"),
    output: Path = typer.Argument(..., help="Output file path"),
    format: OutputFormat = typer.Option(OutputFormat.WEBM, "--format", "-f", help="Output format"),
    frame_rate: int = typer.Option(24, "--frame-rate", "-r", help="Frame rate for output"),
    quality: int = typer.Option(40, "--quality", "-q", help="Quality setting (for WebM)"),
) -> None:
    """Render a scene to a video file."""
    if not file.exists():
        typer.echo(f"File not found: {file}", err=True)
        raise typer.Exit(1)

    # Initialize scene evaluator
    evaluator = SceneEvaluator()

    # Get scene
    scene = evaluator.evaluate_file(file)
    if not scene:
        typer.echo(f"No Scene object found in {file}", err=True)
        raise typer.Exit(1)

    # Render based on format
    if format == OutputFormat.WEBM:
        scene.to_webm(frame_rate=frame_rate, quality=quality, output_path=output)
    elif format == OutputFormat.MOV:
        scene.to_video(frame_rate=frame_rate, output_path=output)
    elif format == OutputFormat.GIF:
        scene.to_gif(frame_rate=frame_rate, output_path=output)


if __name__ == "__main__":
    app()
