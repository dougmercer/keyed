import platform
import subprocess
import sys


class DependencyManager:
    """Manages system dependencies for keyed and its extensions."""

    def __init__(self) -> None:
        """Initialize the dependency manager."""
        self.dependencies = {}

    def register_feature(
        self, feature_id: str, import_path: str, import_checks: list[dict], error_message: str | None = None
    ) -> None:
        """Register a feature that depends on system libraries.

        Args:
            feature_id: Unique identifier for the feature
            import_path: Import path to the module providing the feature
            import_checks: List of import checks to verify dependencies
            error_message: Default error message if dependency check fails
        """
        self.dependencies[feature_id] = {
            "available": False,
            "error": error_message or f"{feature_id} not available: Required system dependencies not found",
            "import_path": import_path,
            "import_checks": import_checks,
        }

    def run_isolated_import(self, import_command: str) -> tuple[bool, str | None]:
        """Run an import in an isolated process to avoid conflicts.

        Args:
            import_command: Python code to execute the import

        Returns:
            Tuple of (success, error_message)
        """
        try:
            proc = subprocess.run(
                [sys.executable, "-c", f"{import_command}; print('IMPORT_SUCCESS')"],
                capture_output=True,
                text=True,
            )

            if "IMPORT_SUCCESS" in proc.stdout:
                return True, None
            else:
                return False, proc.stderr.strip() or "Unknown import error"
        except Exception as e:
            return False, str(e)

    def check_dependencies(self) -> dict:
        """Check all registered system dependencies.

        Returns:
            Dict with status of all dependencies
        """
        for feature_id, feature_info in self.dependencies.items():
            # Each feature might require multiple import checks
            available = True
            error_messages = []

            # Run each import check for this feature
            for check in feature_info["import_checks"]:
                success, error = self.run_isolated_import(check["import_command"])
                if not success:
                    available = False
                    error_messages.append(f"{check['name']}: {error}")

            # Update feature availability
            self.dependencies[feature_id]["available"] = available
            if not available and error_messages:
                self.dependencies[feature_id]["error"] = " | ".join(error_messages)
            elif available:
                self.dependencies[feature_id]["error"] = None

        return self.dependencies

    def check_dependency(self, feature_id):
        if feature_id not in self.dependencies:
            raise KeyError(f"Feature {feature_id} has not been registered ({self.dependencies.keys()}).")

        feature_info = self.dependencies[feature_id]

        # Each feature might require multiple import checks
        available = True
        error_messages = []

        # Run each import check for this feature
        for check in feature_info["import_checks"]:
            success, error = self.run_isolated_import(check["import_command"])
            if not success:
                available = False
                error_messages.append(f"{check['name']}: {error}")

        # Update feature availability
        self.dependencies[feature_id]["available"] = available
        if not available and error_messages:
            self.dependencies[feature_id]["error"] = " | ".join(error_messages)
        elif available:
            self.dependencies[feature_id]["error"] = None

    def load_modules(self) -> dict[str, str]:
        """Get import paths for available features.

        Returns:
            Dict mapping feature IDs to import paths
        """
        self.check_dependencies()

        exports = {}
        for feature_id, feature_info in self.dependencies.items():
            if feature_info["available"]:
                exports[feature_id] = feature_info["import_path"]

        return exports

    def get_available_features(self) -> dict:
        """Get information about available features.

        Returns:
            Dict with availability status of each feature
        """
        self.check_dependencies()
        return self.dependencies

    def get_detailed_system_info(self) -> dict:
        """Get detailed system information for debugging."""
        info = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "system": platform.system(),
        }

        for feature_id, feature_info in self.dependencies.items():
            if feature_info["available"]:
                for check in feature_info["import_checks"]:
                    if "version_command" in check:
                        try:
                            # Run in isolated process to safely get version
                            proc = subprocess.run(
                                [sys.executable, "-c", check["version_command"]],
                                capture_output=True,
                                text=True,
                            )
                            if proc.returncode == 0 and proc.stdout.strip():
                                info[f"{check['name']}_version"] = proc.stdout.strip()
                        except Exception:
                            pass

        return info

    def is_feature_available(self, feature_id: str) -> bool:
        """Check if a specific feature is available.

        Args:
            feature_id: The identifier of the feature to check

        Returns:
            True if the feature is available, False otherwise
        """
        self.check_dependency(feature_id)

        # Get feature info (safely)
        feature_info = self.dependencies.get(feature_id, {})

        # Return availability status
        return feature_info.get("available", False)

    def get_feature_error(self, feature_id: str) -> str:
        """Get the error message for a feature if it's not available.

        Args:
            feature_id: The identifier of the feature to check

        Returns:
            Error message if feature is unavailable, empty string otherwise
        """
        self.check_dependency(feature_id)

        # Get feature info (safely)
        feature_info = self.dependencies.get(feature_id, {})

        # Return error if feature is unavailable
        if not feature_info.get("available", False):
            return feature_info.get("error", "Unknown error")

        return ""

    def assert_feature_available(self, feature_id):
        if not self.is_feature_available(feature_id):
            error_msg = self.get_feature_error(feature_id)
            raise ImportError(
                f"{feature_id} feature is not available: {error_msg}\n"
                "For installation instructions, visit: https://extras.keyed.dev/install"
            )


dependency_manager = DependencyManager()

dependency_manager.register_feature(
    feature_id="previewer",
    import_path="keyed.previewer",
    import_checks=[
        {
            "name": "PySide6",
            "import_command": "import PySide6",
            "version_command": "import PySide6; print(PySide6.__version__)",
        },
        {
            "name": "watchdog",
            "import_command": "import watchdog",
            "version_command": "import watchdog.version; print(watchdog.version.VERSION_STRING)",
        },
    ],
    error_message="Previewer not available. Install with: pip install 'keyed[previewer]'",
)
