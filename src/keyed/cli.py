"""Command line interface for Keyed animations."""

import os
import sys
import tempfile
from enum import Enum
from pathlib import Path

import typer

from keyed.constants import Quality, QualitySetting
from keyed.debug import dependency_manager
from keyed.parser import SceneEvaluator
from keyed.renderer import VideoFormat

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
    if len(sys.argv) > 1 and sys.argv[1] not in ["info", "preview", "render", "iostream", "--help"]:
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
                    frame_rate=frame_rate,
                    output_path=tmp_output_path,
                    quality=quality,
                )
            elif format == OutputFormat.MOV:
                scene.render(
                    format=VideoFormat.MOV_PRORES,
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


@app.command()
def info():
    """Check system dependencies and installation status for keyed and keyed-extras."""
    try:
        # Basic keyed information
        typer.echo("keyed info: Diagnostic tool for keyed and keyed-extras")
        typer.echo("======================================================")

        from importlib.metadata import PackageNotFoundError, version

        typer.echo(f"\nkeyed version: {version('keyed')}")

        # Check for keyed-extras
        try:
            import importlib.metadata

            extras_version = importlib.metadata.version("keyed-extras")
            typer.echo(f"keyed-extras version: {extras_version}")
        except (ImportError, PackageNotFoundError):
            typer.echo("keyed-extras: Not installed")
            typer.echo("\nTo install keyed-extras: pip install keyed-extras")
            return

        # Check system dependencies

        # Display feature availability
        features = dependency_manager.get_available_features()
        if features:
            typer.echo("\nFeature availability:")
            for feature_id, info in features.items():
                status = "✓ Available" if info["available"] else "✗ Not available"
                typer.echo(f"  {feature_id}: {status}")
                if not info["available"] and info.get("error"):
                    typer.echo(f"    Error: {info['error']}")

        # Display system information
        sys_info = dependency_manager.get_detailed_system_info()
        typer.echo("\nSystem information:")
        typer.echo(f"  Platform: {sys_info.get('platform', 'Unknown')}")
        typer.echo(f"  Python: {sys_info.get('python_version', 'Unknown')}")

        # Display library versions from sys_info
        library_versions = [k for k in sys_info.keys() if k.endswith("_version")]
        if library_versions:
            typer.echo("\nDetected libraries:")
            for key in library_versions:
                name = key.replace("_version", "")
                typer.echo(f"  {name}: {sys_info[key]}")

        # Display help information
        typer.echo("\nFor installation help: https://dougmercer.github.io/keyed-extras-docs/install")
        typer.echo("To report issues: https://github.com/dougmercer-yt/keyed-extras/issues")

    except Exception as e:
        typer.echo(f"Error running diagnostics: {str(e)}", err=True)
