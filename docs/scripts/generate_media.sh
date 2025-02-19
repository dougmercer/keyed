#!/bin/bash

# Call from root directory of repository

python docs/scripts/generate_easing_animations.py
keyed render examples/first_scene.py docs/media/bouncing_ball.webm -f webm
