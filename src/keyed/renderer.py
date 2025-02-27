from __future__ import annotations

import subprocess
from enum import Enum, auto
from pathlib import Path
from subprocess import PIPE, Popen
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .scene import Scene


__all__ = ["Renderer", "VideoFormat", "RenderEngine"]


class VideoFormat(Enum):
    """Enumeration of supported video formats."""

    MOV_PRORES = auto()
    GIF = auto()
    WEBM = auto()


class RenderEngine(Enum):
    """Enumeration of supported rendering engines."""

    FFMPEG = auto()
    PYAV = auto()


class Renderer:
    """Video rendering abstraction that supports multiple formats and engines.

    Supports rendering animations to different video formats using either FFmpeg or PyAV.
    """

    def __init__(self, scene: Scene):
        """Initialize the video renderer.

        Args:
            scene: The animation scene object with frame retrieval method
        """
        self.scene = scene

    def _create_output_directory(self, output_path: Path | None = None) -> Path:
        """Create output directory if not specified.

        Args:
            output_path: Optional specific output path

        Returns:
            Resolved output path
        """
        if output_path is None:
            # Assuming scene has similar method to create output folder
            self.scene._create_folder()  # type: ignore
            return self.scene.full_output_dir / f"{self.scene.scene_name}"  # type: ignore
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            return output_path

    def render(
        self,
        format: VideoFormat,
        engine: RenderEngine,
        frame_rate: int = 24,
        open_dir: bool = False,
        output_path: Path | None = None,
        **kwargs,
    ) -> None:
        """Render the animation to a video file.

        Args:
            format: Desired video format (MOV, GIF, WebM)
            engine: Rendering engine to use (FFmpeg or PyAV)
            frame_rate: Frames per second (default 24)
            open_dir: Whether to open output directory after rendering
            output_path: Optional specific output path
            **kwargs: Additional format-specific parameters
        """
        # Determine file extension based on format
        extensions = {VideoFormat.MOV_PRORES: ".mov", VideoFormat.GIF: ".gif", VideoFormat.WEBM: ".webm"}
        ext = extensions[format]

        # Create output path
        output_path = self._create_output_directory(output_path)
        full_output_path = output_path.with_suffix(ext)

        # Render based on selected engine and format
        if engine == RenderEngine.FFMPEG:
            self._render_ffmpeg(full_output_path, format, frame_rate, **kwargs)
        elif engine == RenderEngine.PYAV:
            self._render_pyav(full_output_path, format, frame_rate, **kwargs)

        # Open directory if requested
        if open_dir:
            subprocess.run(["open", str(full_output_path.parent)])

    def _render_ffmpeg(self, output_path: Path, format: VideoFormat, frame_rate: int, **kwargs) -> None:
        """Render video using FFmpeg.

        Args:
            output_path: Path to save the video
            format: Video format to render
            frame_rate: Frames per second
            **kwargs: Additional format-specific parameters
        """
        # Base FFmpeg command setup
        base_command = [
            "ffmpeg",
            "-y",
            "-f",
            "rawvideo",
            "-vcodec",
            "rawvideo",
            "-s",
            f"{self.scene._width}x{self.scene._height}",
            "-pix_fmt",
            "bgra",
            "-r",
            str(frame_rate),
            "-i",
            "-",
        ]

        # Format-specific configurations
        if format == VideoFormat.MOV_PRORES:
            command = base_command + [
                "-vcodec",
                "prores_ks",
                "-profile:v",
                "4444",
                "-pix_fmt",
                "yuva444p10le",
                str(output_path),
            ]
        elif format == VideoFormat.GIF:
            command = base_command + [
                "-vf",
                "split[s0][s1];[s0]palettegen=stats_mode=full[p];[s1][p]paletteuse=dither=sierra2_4a",
                "-loop",
                str(kwargs.get("loop", 0)),
                str(output_path),
            ]
        elif format == VideoFormat.WEBM:
            command = base_command + [
                "-c:v",
                "libvpx-vp9",
                "-pix_fmt",
                "yuva420p",
                "-crf",
                str(kwargs.get("quality", 40)),
                "-b:v",
                "0",
                "-row-mt",
                "1",
                str(output_path),
            ]
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Render frames
        with Popen(command, stdin=PIPE) as ffmpeg:
            for frame in range(self.scene.num_frames):
                ffmpeg.stdin.write(self.scene.asarray(frame).tobytes())  # type: ignore

    def _render_pyav(self, output_path: Path, format: VideoFormat, frame_rate: int, **kwargs) -> None:
        """Render video using PyAV.

        Args:
            output_path: Path to save the video
            format: Video format to render
            frame_rate: Frames per second
            **kwargs: Additional format-specific parameters
        """
        import av

        # Open output container
        container = av.open(str(output_path), mode="w")

        # Format-specific configurations
        if format == VideoFormat.MOV_PRORES:
            stream = container.add_stream("prores_ks", rate=frame_rate)
            stream.pix_fmt = "yuv444p10le"  # type: ignore
            stream.width = self.scene._width  # type: ignore
            stream.height = self.scene._height  # type: ignore
        elif format == VideoFormat.WEBM:
            stream = container.add_stream("libvpx-vp9", rate=frame_rate)
            stream.pix_fmt = "yuva420p"  # type: ignore
            stream.width = self.scene._width  # type: ignore
            stream.height = self.scene._height  # type: ignore
            stream.options = {"crf": str(kwargs.get("quality", 40)), "b:v": "0"}  # type: ignore
        elif format == VideoFormat.GIF:
            raise NotImplementedError("GIF rendering with PyAV is not supported. Use FFmpeg.")
        else:
            raise ValueError(f"Unsupported format: {format}")

        # Write frames
        for frame_idx in range(self.scene.num_frames):
            # Create frame
            frame = av.VideoFrame.from_ndarray(self.scene.asarray(frame_idx), format="bgra")

            # Encode and write the frame
            for packet in stream.encode(frame):  # type: ignore
                container.mux(packet)

        # Flush remaining packets
        for packet in stream.encode():  # type: ignore
            container.mux(packet)

        # Close container
        container.close()
