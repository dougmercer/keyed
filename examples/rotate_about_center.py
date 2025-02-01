from keyed import Circle, Scene, easing

scene = Scene(width=1920, height=1080)
x0 = scene._width / 2
y0 = scene._height / 2
delta = 100
center = Circle(scene, x=x0, y=y0, radius=1)
g = center.geom
not_center = Circle(scene, x=x0, y=y0 + delta, radius=1)
not_center.rotate(start=0, end=6, amount=90, easing=easing.cubic_in_out, center=g)
not_center.rotate(start=6, end=12, amount=90, easing=easing.cubic_in_out, center=g)
not_center.rotate(start=12, end=18, amount=90, easing=easing.cubic_in_out, center=g)
not_center.rotate(start=18, end=24, amount=90, easing=easing.cubic_in_out, center=g)
not_center.rotate(start=32, end=48, amount=360, easing=easing.cubic_in_out, center=g)

scene.add(not_center, center)
