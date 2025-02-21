import io
import os
import uuid
from typing import List, Optional

import numpy as np
from hypothesis import settings
from PIL import Image
from syrupy.assertion import SnapshotAssertion

settings.register_profile("ci", deadline=1000)
settings.load_profile("ci")

# Generate a unique ID for this test run
TEST_RUN_ID = str(uuid.uuid4())


def generate_ascii_diff(diff_mask: np.ndarray) -> List[str]:
    """Generate ASCII art representation of the diff mask, maintaining aspect ratio."""
    target_width = 80
    # Calculate height that maintains aspect ratio
    aspect_ratio = diff_mask.shape[0] / diff_mask.shape[1]
    target_height = int(target_width * aspect_ratio / 2)  # Divide by 2 as characters are roughly twice as tall as wide

    # Calculate scale factors
    scale_y = diff_mask.shape[0] // target_height
    scale_x = diff_mask.shape[1] // target_width
    scale_factor = max(scale_y, scale_x, 1)

    # Downsample the mask
    small_mask = diff_mask[::scale_factor, ::scale_factor]

    # Trim to target size if needed
    small_mask = small_mask[:target_height, :target_width]

    # Convert to ASCII
    lines = ["Diff visualization (■ = different, · = same):"]
    ascii_art = []
    for row in small_mask:
        ascii_art.append("".join("■" if x else "·" for x in row))
    lines.extend(ascii_art)

    return lines


def generate_image_diff_report(img1: Image.Image, img2: Image.Image, snapshot_name: str) -> Optional[list[str]]:
    """Generate a detailed diff report between two images."""
    lines = ["Image comparison failed:"]

    # Check dimensions
    if img1.size != img2.size:
        lines.extend(["Size mismatch:", f"  Left:  {img1.size}", f"  Right: {img2.size}"])
        return lines

    # Convert to RGBA arrays for comparison
    arr1 = np.array(img1.convert("RGBA"))
    arr2 = np.array(img2.convert("RGBA"))

    # Find differences
    diff_mask = np.any(arr1 != arr2, axis=2)
    if not np.any(diff_mask):
        return None

    # Calculate overall difference stats
    total_pixels = diff_mask.size
    diff_pixels = np.count_nonzero(diff_mask)
    diff_percentage = (diff_pixels / total_pixels) * 100

    lines.append(f"Different pixels: {diff_pixels:,} ({diff_percentage:.2f}%)")

    # Create a binary diff image - white for differences, black for same
    diff_img = np.zeros((arr1.shape[0], arr1.shape[1], 3), dtype=np.uint8)
    diff_img[diff_mask] = [255, 255, 255]  # White for differences

    # Save diff image with test run ID and snapshot name
    diff_dir = os.path.join("/tmp", "image_diffs", TEST_RUN_ID)
    os.makedirs(diff_dir, exist_ok=True)
    sanitized_name = snapshot_name.replace("/", "_")  # Ensure safe filename
    diff_path = os.path.join(diff_dir, f"{sanitized_name}.png")
    Image.fromarray(diff_img).save(diff_path)
    lines.append(f"Diff image saved to: {diff_path}")

    # Generate ASCII art representation
    lines.extend(generate_ascii_diff(diff_mask))

    return lines


def pytest_assertrepr_compare(op, left, right):
    if op == "==":
        if not isinstance(right, SnapshotAssertion):
            return None

        # Collect all diff reports from failed assertions
        all_diff_lines = ["Snapshot comparison failed:"]
        all_diff_lines.append(f"Test run ID: {TEST_RUN_ID}")

        for execution in right.executions.values():
            # Skip successful comparisons
            if execution.success:
                continue

            # Skip if we don't have both pieces of data
            if execution.asserted_data is None or execution.recalled_data is None:
                continue

            try:
                # Convert both to images
                asserted_img = Image.open(io.BytesIO(bytes(execution.asserted_data)))
                recalled_img = Image.open(io.BytesIO(bytes(execution.recalled_data)))

                # Generate diff report for this snapshot
                diff_report = generate_image_diff_report(asserted_img, recalled_img, execution.snapshot_name)
                if diff_report:
                    all_diff_lines.extend(
                        [
                            f"\nSnapshot: {execution.snapshot_name}",
                            f"Location: {execution.snapshot_location}",
                            *diff_report,
                        ]
                    )
            except Exception as e:
                all_diff_lines.extend([f"\nError analyzing diff for {execution.snapshot_name}:", f"  {str(e)}"])

        return all_diff_lines if len(all_diff_lines) > 1 else None
    return None
