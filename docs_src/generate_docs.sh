#!/bin/bash
set -eo pipefail

# Call this script from the root of the repository

# Easing API docs
python docs_src/easing/generate_easing_animations.py

# Tutorial
mkdir -p docs/media/tutorial
keyed render examples/first_scene.py docs/media/tutorial/bouncing_ball.webm -f webm
keyed render docs_src/tutorial/easing/moving_circle.py docs/media/tutorial/moving_circle.webm -f webm
python docs_src/easing/make_easing_grid.py

# Gallery
keyed render examples/code_replace_complex.py docs/media/gallery/code_replace_complex.webm -f webm
keyed render examples/curve_interp.py docs/media/gallery/curve_interp.webm -f webm
keyed render examples/first_scene.py docs/media/gallery/first_scene.webm -f webm
python docs_src/gallery/make_gallery.py
python docs_src/gallery/generate_gallery_animations.py
