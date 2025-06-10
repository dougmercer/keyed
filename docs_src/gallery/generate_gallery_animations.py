import os
import subprocess
from pathlib import Path

import yaml


def generate_animations():
    """Parse gallery.yml and generate webm animations for each scene."""
    # Load gallery configuration
    with open(Path(__file__).parent / "gallery.yml", "r") as f:
        gallery_config = yaml.safe_load(f)

    # Create output directory if it doesn't exist
    output_dir = Path("docs/media/gallery")
    output_dir.mkdir(exist_ok=True, parents=True)

    print(f"Found {len(gallery_config['scenes'])} scenes in gallery.yml")

    # Process each scene
    for scene in gallery_config["scenes"]:
        scene_name = scene["name"]
        src_path = scene["src_path"]
        output_path = output_dir / f"{scene_name}.webm"

        print(f"Processing scene: {scene_name}")
        print(f"  Source: {src_path}")
        print(f"  Output: {output_path}")

        # Check if the source file exists
        if not os.path.exists(src_path):
            print(f"  ERROR: Source file not found: {src_path}")
            continue

        try:
            print(f"  Running: python {src_path} {output_path}")

            subprocess.run(
                ["keyed", "render", "-f", "webm", src_path, str(output_path)],
                check=True,
                capture_output=True,
                text=True,
            )

        except subprocess.CalledProcessError as e:
            print(f"  ERROR: Failed to run {src_path}")
            print(f"  Output: {e.stdout}")
            print(f"  Error: {e.stderr}")
        except Exception as e:
            print(f"  ERROR: Failed to process {scene_name}: {str(e)}")

    print("Animation generation complete!")


if __name__ == "__main__":
    generate_animations()
