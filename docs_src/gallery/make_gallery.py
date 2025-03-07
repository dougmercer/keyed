from pathlib import Path

import yaml
from jinja2 import Template

HERE = Path(__file__).parent

# Load scenes from YAML file
with open(HERE / "gallery.yml", "r") as f:
    config = yaml.safe_load(f)
    scenes = config["scenes"]

# Create docs gallery directory if it doesn't exist
gallery_dir = HERE / "../../docs/gallery"
gallery_dir.mkdir(exist_ok=True)

# Generate gallery page
with open(HERE / "gallery_template.md", "r") as f:
    gallery_template = Template(f.read())

gallery_content = gallery_template.render(scenes=scenes)

with open(gallery_dir / "index.md", "w") as f:
    f.write(gallery_content)

# Generate individual scene pages
with open(HERE/ "scene_template.md", "r") as f:
    scene_template = Template(f.read())

for scene in scenes:
    scene_content = scene_template.render(scene=scene)
    
    with open(gallery_dir / f"{scene['name']}.md", "w") as f:
        f.write(scene_content)

print(f"Generated gallery with {len(scenes)} examples.")
