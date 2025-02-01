from keyed import DL, DOWN, LEFT, RIGHT, Code, Scene, tokenize

scene = Scene(scene_name="code_replace_complex", num_frames=48, width=3840, height=2160)

styled_tokens1 = tokenize(r"x = 1 + 2 + 3")
code1 = Code(scene, styled_tokens1, font_size=36, x=200, y=200)

styled_tokens2 = tokenize(r"x = 1 + get_two() + 3")
code2 = Code(scene, styled_tokens2, font_size=36, x=400, y=600)

scene.add(code1, code2)

code2.align_to(code1.chars[0], from_=code2.chars[0].geom, start=0, lock=6, end=6, direction=LEFT)
code2.align_to(code1.chars[0], from_=code2.chars[0].geom, start=12, end=18, direction=DOWN)
code2.align_to(code1.chars[-1], from_=code2.chars[-1].geom, start=24, end=30, direction=RIGHT)
code2.translate(x=300, y=300, start=36, end=42)
code2.align_to(code1.chars[-1], from_=code2.chars[-1].geom, start=48, end=54, direction=DL)
