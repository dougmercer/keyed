import sys
from pathlib import Path

from jinja2 import Template

# Set the paths
SCRIPT_DIR = Path(__file__).parent
DOCS_DIR = SCRIPT_DIR / "../../docs/"

# List of all easing functions
# fmt: off
EASING_FUNCTIONS = [
    # Quad family
    "quad_in", "quad_out", "quad_in_out",
    # Cubic family
    "cubic_in", "cubic_out", "cubic_in_out",
    # Quartic family
    "quartic_in", "quartic_out", "quartic_in_out",
    # Quintic family
    "quintic_in", "quintic_out", "quintic_in_out",
    # Sine family
    "sine_in", "sine_out", "sine_in_out",
    # Circular family
    "circular_in", "circular_out", "circular_in_out",
    # Elastic family
    "elastic_in", "elastic_out", "elastic_in_out",
    # Expo family
    "expo_in", "expo_out", "expo_in_out",
    # Back family
    "back_in", "back_out", "back_in_out",
    # Bounce family
    "bounce_in", "bounce_out", "bounce_in_out",
    # Linear
    "linear_in_out",
]
# fmt: on


# Optional: Verify that all webm files exist
def verify_files_exist():
    missing_files = []
    for func in EASING_FUNCTIONS:
        filepath = DOCS_DIR / "media" / "easing" / f"{func}.webm"
        if not filepath.exists():
            missing_files.append(func)

    if missing_files:
        print("Warning: The following easing function animations are missing:", file=sys.stderr)
        for func in missing_files:
            print(f"  - {func}.webm", file=sys.stderr)
        return False
    return True


# Read the template
with open(SCRIPT_DIR / "easing-grid-template.md", "r") as f:
    template = Template(f.read())

# Render the template
output = template.render(easing_functions=EASING_FUNCTIONS)

# Write the output
with open(DOCS_DIR / "easing-grid.md", "w") as f:
    f.write(output)

# Verify files if desired
if verify_files_exist():
    print(f"Successfully generated easing functions documentation with {len(EASING_FUNCTIONS)} functions.")
else:
    print("Documentation generated with warnings. Please check the missing files.")
