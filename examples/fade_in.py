from keyed import Animation, Code, Scene, tokenize

with open("examples/_example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="fade_in", num_frames=24, width=1920, height=1080)
code = Code(scene, styled_tokens, font_size=48)

scene.add(code)

# Fade in the first 10 characters
code.chars[:10].set("alpha", 0, 0).fade(1, 0, 24)
