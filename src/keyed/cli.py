"""Command line interface for Keyed animations."""

import os
import sys
import tempfile
from enum import Enum
from pathlib import Path

import typer

from keyed.constants import Quality, QualitySetting
from keyed.parser import SceneEvaluator
from keyed.renderer import RenderEngine, VideoFormat

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
    if len(sys.argv) > 1 and sys.argv[1] not in ["preview", "render", "iostream", "--help"]:
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
    frame_rate: int = typer.Option(24, "--frame-rate", "-r", help="Frame rate for playback"),
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
        scene.render(format=VideoFormat.WEBM, frame_rate=frame_rate, output_path=output, quality=quality)
    elif format == OutputFormat.MOV:
        scene.render(format=VideoFormat.MOV_PRORES, frame_rate=frame_rate, output_path=output)
    elif format == OutputFormat.GIF:
        scene.render(format=VideoFormat.GIF, frame_rate=frame_rate, output_path=output)


@app.command()
def iostream(
    format: OutputFormat = typer.Option(OutputFormat.MOV, "--format", "-f", help="Output format"),
    frame_rate: int = typer.Option(24, "--frame-rate", "-r", help="Frame rate for output"),
    quality: int = typer.Option(40, "--quality", "-q", help="Quality setting (for WebM)"),
) -> None:
    """
    Render a scene from stdin to stdout or file.

    This command reads Python code from stdin, renders the animation,
    and outputs the video data to stdout.

    Example:
        cat myscene.py | keyed iostream > output.mp4
    """
    # Read Python code from stdin
    code = sys.stdin.read()

    if not code:
        typer.echo("No input received from stdin", err=True)
        raise typer.Exit(1)

    # Create a context manager to suppress all stdout during scene evaluation
    class SuppressStdout:
        def __enter__(self):
            self.original_stdout = sys.stdout
            sys.stdout = open(os.devnull, "w")
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            sys.stdout.close()
            sys.stdout = self.original_stdout

    # Save the code to a temporary file
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w") as tmp_file:
        tmp_file.write(code)
        tmp_file.flush()
        tmp_path = Path(tmp_file.name)

        # Suppress all stdout during evaluation and rendering
        with SuppressStdout():
            # Initialize scene evaluator
            evaluator = SceneEvaluator()

            # Get scene
            scene = evaluator.evaluate_file(tmp_path)
            if not scene:
                typer.echo("No Scene object found in input", err=True)
                raise typer.Exit(1)

            # Create a temporary output file
            with tempfile.NamedTemporaryFile(suffix=f".{format.value}", delete=False) as tmp_output:
                tmp_output_path = Path(tmp_output.name)

            # Render based on format
            if format == OutputFormat.WEBM:
                scene.render(
                    format=VideoFormat.WEBM,
                    engine=RenderEngine.PYAV,
                    frame_rate=frame_rate,
                    output_path=tmp_output_path,
                    quality=quality,
                )
            elif format == OutputFormat.MOV:
                scene.render(
                    format=VideoFormat.MOV_PRORES,
                    engine=RenderEngine.PYAV,
                    frame_rate=frame_rate,
                    output_path=tmp_output_path,
                )
            elif format == OutputFormat.GIF:
                scene.render(format=VideoFormat.GIF, frame_rate=frame_rate, output_path=tmp_output_path)

        # Read the output file and write to stdout as binary
        with open(tmp_output_path, "rb") as f:
            # Write directly to stdout as binary
            sys.stdout.buffer.write(f.read())

        # Clean up the temporary output file if it was sent to stdout
        tmp_output_path.unlink()
