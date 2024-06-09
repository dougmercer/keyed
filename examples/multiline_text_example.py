from keyed import Code, Scene, tokenize

scene = Scene("hello", num_frames=60, width=1920, height=1080)


with open("testing/multiline_string.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

code = Code(scene, styled_tokens, font_size=36)

scene.add(code)

scene.preview()
