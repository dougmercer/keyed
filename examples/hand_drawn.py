from keyed import Circle, Rectangle, Scene

scene = Scene(scene_name="rect", num_frames=90, width=3840, height=2160, freehand=True)

rect = Rectangle(scene, width=1000, height=1000, x=1000, y=1000, draw_fill=False, line_width=10)
circle = Circle(scene, x=2000, y=1000, radius=500, draw_fill=False, line_width=10)

rect.translate(1000, 0, 0, 90)

scene.add(rect, circle)

scene.preview()
