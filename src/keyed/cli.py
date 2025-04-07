"""Command line interface for Keyed animations."""

import os
import sys
import tempfile
from enum import Enum
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from keyed.debug import dependency_manager
from keyed.parser import SceneEvaluator
from keyed.previewer import PREVIEW_AVAILABLE
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


def print_error(message: str):
    console = Console(stderr=True)
    console.print(Panel(f"[bold red]{message}[/bold red]", title="Error", border_style="red"))


def print_success(message: str):
    console = Console(stderr=True)
    console.print(Panel(f"[bold green]{message}[/bold green]", title="Success", border_style="green"))


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
) -> None:
    """Preview a scene in a live-reloading window."""
    if not PREVIEW_AVAILABLE:
        from rich.console import Console
        from rich.panel import Panel
        from rich.text import Text

        console = Console(stderr=True)

        error_text = Text()
        error_text.append("Previewer unavailable!", style="bold red")
        error_text.append("\nInstall with: ", style="dim")
        error_text.append("pip install 'keyed[previewer]'", style="bold green")

        console.print(Panel(error_text, title="Error", border_style="red"))
        raise typer.Exit(1)

    from PySide6.QtWidgets import QApplication

    from keyed.previewer import FileWatcher, LiveReloadWindow

    if not file.exists():
        print_error(f"File not found: {file}")
        raise typer.Exit(1)

    # Initialize scene evaluator
    evaluator = SceneEvaluator()

    # Get initial scene
    scene = evaluator.evaluate_file(file)
    if not scene:
        print_error(f"No Scene object found in {file}")
        raise typer.Exit(1)

    # Create application and window
    app = QApplication(sys.argv)
    window = LiveReloadWindow(scene, frame_rate=frame_rate)
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
        print_error(f"File not found: {file.resolve()}")
        raise typer.Exit(1)

    # Initialize scene evaluator
    evaluator = SceneEvaluator()

    # Get scene
    scene = evaluator.evaluate_file(file)
    if not scene:
        print_error(f"No Scene object found in {file.resolve()}")
        raise typer.Exit(1)

    # Render based on format
    if format == OutputFormat.WEBM:
        scene.render(format=VideoFormat.WEBM, frame_rate=frame_rate, output_path=output, quality=quality)
    elif format == OutputFormat.MOV:
        scene.render(format=VideoFormat.MOV_PRORES, frame_rate=frame_rate, output_path=output)
    elif format == OutputFormat.GIF:
        scene.render(format=VideoFormat.GIF, frame_rate=frame_rate, output_path=output)

    print_success(f"Successfully rendered scene to {output.resolve()}")


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
        print_error("No input received from stdin")
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
                print_error("No Scene object found in input")
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
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table

        console = Console()

        console.print(
            Panel.fit(
                "[bold blue]keyed info[/bold blue]: Diagnostic tool for keyed and keyed-extras", border_style="blue"
            )
        )

        from importlib.metadata import PackageNotFoundError, version

        # Create a table for package versions
        version_table = Table(show_header=False, box=None)
        version_table.add_column("Package", style="dim")
        version_table.add_column("Version", style="green")

        version_table.add_row("keyed version", version("keyed"))

        # Check for keyed-extras
        try:
            import importlib.metadata

            extras_version = importlib.metadata.version("keyed-extras")
            version_table.add_row("keyed-extras version", extras_version)
        except (ImportError, PackageNotFoundError):
            version_table.add_row("keyed-extras", "[red]Not installed[/red]")
            console.print(version_table)
            console.print("\nTo install keyed-extras: [bold green]pip install keyed-extras[/bold green]")
            return

        console.print(version_table)

        # Check system dependencies
        # Display feature availability
        features = dependency_manager.get_available_features()
        if features:
            console.print("\n[bold]Feature availability:[/bold]")
            feature_table = Table(show_header=False, box=None, padding=(0, 1, 0, 1))
            feature_table.add_column("Feature")
            feature_table.add_column("Status")

            for feature_id, info in features.items():
                status = "[green]✓ Available[/green]" if info["available"] else "[red]✗ Not available[/red]"
                feature_table.add_row(feature_id, status)
                if not info["available"] and info.get("error"):
                    feature_table.add_row("", f"[dim italic]Error: {info['error']}[/dim italic]")

            console.print(feature_table)

        # Display system information
        sys_info = dependency_manager.get_detailed_system_info()
        console.print("\n[bold]System information:[/bold]")
        sys_table = Table(show_header=False, box=None, padding=(0, 1, 0, 1))
        sys_table.add_column("Property", style="dim")
        sys_table.add_column("Value")

        sys_table.add_row("Platform", sys_info.get("platform", "Unknown"))
        sys_table.add_row("Python", sys_info.get("python_version", "Unknown"))

        console.print(sys_table)

        # Display library versions from sys_info
        library_versions = [k for k in sys_info.keys() if k.endswith("_version")]
        if library_versions:
            console.print("\n[bold]Detected libraries:[/bold]")
            lib_table = Table(show_header=False, box=None, padding=(0, 1, 0, 1))
            lib_table.add_column("Library", style="dim")
            lib_table.add_column("Version")

            for key in library_versions:
                name = key.replace("_version", "")
                lib_table.add_row(name, sys_info[key])

            console.print(lib_table)

        # Display help information
        help_panel = Panel(
            "[dim]For installation help:[/dim] [blue]https://dougmercer.github.io/keyed-extras-docs/install[/blue]\n"
            "[dim]To report issues:[/dim] [blue]https://github.com/dougmercer-yt/keyed-extras/issues[/blue]",
            title="Help Resources",
            border_style="green",
        )
        console.print(help_panel)

    except Exception as e:
        from rich.console import Console

        console = Console(stderr=True)
        console.print(f"[bold red]Error running diagnostics:[/bold red] {str(e)}")
