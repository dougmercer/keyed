"""Configuration handling for Keyed."""

import os
import subprocess
import warnings
from pathlib import Path
from typing import Any, Dict

import tomllib

from .renderer import RenderEngine


def is_ffmpeg_available() -> bool:
    """Check if ffmpeg is available on the system."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def get_config_paths() -> list[Path]:
    """Get potential configuration file paths in order of precedence."""
    paths = []

    # Check for config in current directory first
    paths.append(Path(".keyed.toml"))

    # Then check user's config directory
    if os.name == "nt":  # Windows
        if app_data := os.environ.get("APPDATA"):
            paths.append(Path(app_data) / "keyed" / "config.toml")
    else:  # macOS, Linux, etc.
        if xdg_config := os.environ.get("XDG_CONFIG_HOME"):
            paths.append(Path(xdg_config) / "keyed" / "config.toml")
        paths.append(Path.home() / ".config" / "keyed" / "config.toml")

    # Finally check home directory
    paths.append(Path.home() / ".keyed.toml")

    return paths


def load_config() -> Dict[str, Any]:
    """Load configuration from TOML file."""
    for config_path in get_config_paths():
        if config_path.exists():
            try:
                with open(config_path, "rb") as f:
                    return tomllib.load(f)
            except Exception as e:
                warnings.warn(f"Error loading config from {config_path}: {e}")

    return {}


def get_default_render_engine() -> RenderEngine:
    """Determine the default render engine based on configuration and availability.

    The function checks in the following order:
    1. Environment variable KEYED_RENDER_ENGINE
    2. Configuration file setting
    3. Auto-detect based on availability

    Returns:
        The default render engine to use
    """
    # First check environment variable (highest precedence)
    env_value = os.environ.get("KEYED_RENDER_ENGINE", "").upper()

    # Handle explicit environment variable setting
    if env_value == "FFMPEG":
        if is_ffmpeg_available():
            return RenderEngine.FFMPEG
        else:
            warnings.warn(
                "FFMPEG requested via KEYED_RENDER_ENGINE but not found on system. "
                "Falling back to PyAV. Install ffmpeg or set KEYED_RENDER_ENGINE=PYAV "
                "to suppress this warning."
            )
            return RenderEngine.PYAV
    elif env_value == "PYAV":
        return RenderEngine.PYAV

    # Check configuration file
    config = load_config()
    config_value = config.get("render_engine", "").upper()

    # Handle explicit config file setting
    if config_value == "FFMPEG":
        if is_ffmpeg_available():
            return RenderEngine.FFMPEG
        else:
            warnings.warn(
                "FFMPEG requested in configuration file but not found on system. "
                "Falling back to PyAV. Install ffmpeg or set render_engine = 'PYAV' "
                "in your config file to suppress this warning."
            )
            return RenderEngine.PYAV
    elif config_value == "PYAV":
        return RenderEngine.PYAV

    # Auto-detect if no explicit setting (lowest precedence)
    return RenderEngine.FFMPEG if is_ffmpeg_available() else RenderEngine.PYAV
