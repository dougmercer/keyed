from keyed import Code, Scene, tokenize

scene = Scene(scene_name="code_replace_complex", num_frames=90, width=3840, height=2160)

styled_tokens1 = tokenize(r"x = 1 + 2 + 3")
code = Code(scene, styled_tokens1, font_size=36, x=200, y=200)

h = code.highlight(line_width=40, fill_color=(1, 0, 0), color=(1, 0, 0), alpha=0.5)
h.shift(0, 10, 0, 6)

scene.add(code, h)

scene.preview()
