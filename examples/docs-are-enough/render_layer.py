from keyed import Circle, Color, Scene

scene = Scene(scene_name="render_layers", num_frames=48, width=1920, height=1080)

c1 = Circle(scene, 100, 100, radius=20)
c1.fill_color = Color(1, 0, 0)


c1.translate(100, 0, 0, 12)
c2 = c1.clone()
c2.fill_color = Color(0, 1, 0)
c2.translate(0, 100, 0, 12)
c2.translate(100, 0, 12, 24)
c3 = c2.clone()
c3.fill_color = Color(0, 0, 1)
c3.translate(0, 100, 0, 12)
c3.translate(100, 0, 12, 24)

scene.add(c1, c2, c3)

scene.draw_as_layers(True)
