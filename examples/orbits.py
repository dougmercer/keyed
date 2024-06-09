from keyed import Circle, Orbit, Rectangle, Scene

s = Scene()
sun = Circle(s, radius=50, x=500, y=500)
planet = Rectangle(s, width=50, height=50)
moon = Rectangle(s, width=10, height=10, fill_color=(1, 0, 0))


# planet.controls.delta_x.add_animation(Animation(0, 60, 10, 1000))
# planet.controls.scale.add_animation(Animation(0, 60, 1, 2))

sun.translate(1920, 0, 0, 60)
planet.add_transform(Orbit(planet, 200, rotation_speed=10, initial_angle=90, center=sun))
moon.add_transform(Orbit(moon, 100, rotation_speed=20, center=planet, start_frame=10, end_frame=40))

s.add(sun, planet, moon)

s.preview()
