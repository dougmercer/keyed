from keyed import Code, Scene, TextSelection, tokenize

with open("examples/_example.py", "r") as f:
    content = f.read()
styled_tokens = tokenize(content)

scene = Scene(scene_name="trace", num_frames=60, width=800, height=800)
code = Code(scene, styled_tokens, font_size=40, alpha=1, x=100, y=100).center()

curve = (
    # Select specific charaters for the highlight to pass through
    # But if you want a noisier look, could just do ...
    # code.chars[:39]
    TextSelection([code.chars[0], code.chars[10], code.chars[11], code.chars[30], code.chars[39]])
    # Create the curve
    .highlight(alpha=0.5, line_width=5, tension=0.5)
    # Start the curve completely undrawn, and animate it being drawn
    .set("end", 0).write_on(1, 0, 24)
)

scene.add(code, curve)
