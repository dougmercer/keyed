from keyed import Circle, Rectangle, Scene, Selection, Text
from keyed.compositor import BlendMode
from keyed_extras.effects import Blur, ColorAdjust, Invert

# Create the scene
scene = Scene(scene_name="layer_demo", num_frames=60, width=1920, height=1080)

# Create layers
background_layer = scene.create_layer("background", z_index=0)
blurred_layer = scene.create_layer("blurred", z_index=3, blend=BlendMode.SCREEN)
foreground_layer = scene.create_layer("foreground", z_index=2)

# Background layer
background = Rectangle(scene, width=2000, height=2000, fill_color=(0.1, 0.1, 0.2))
background.center()
background_layer.add(background)

# Blurred layer
circle1 = Circle(scene, radius=200, fill_color=(0.5, 0, 0), alpha=0.5)
circle2 = Circle(scene, radius=200, fill_color=(0, 0.5, 0), alpha=0.5)
circle3 = Circle(scene, radius=200, fill_color=(0, 0, 0.5), alpha=0.5)

circle1.translate(-150, -150)
circle3.translate(150, 150)
Selection([circle1, circle2, circle3]).center()

blurred_layer.add(circle1, circle2, circle3)
blurred_layer.apply_effect(Blur(radius=10))
blurred_layer.apply_effect(ColorAdjust(brightness=4, contrast=2, saturation=0.5))
blurred_layer.apply_effect(Invert())

# Animate the circles
circle1.translate(300, 300, start=0, end=30)
circle2.translate(-300, 300, start=15, end=45)
circle3.translate(-300, -300, start=30, end=60)

# Foreground layer
text = Text(scene, text="Layered Animation", size=72)
text.center()
text.translate(0, -200)

rect = Rectangle(scene, width=400, height=100, alpha=0.6, fill_color=(0.6, 0.2, 0.2))
rect.center()
rect.translate(0, 200)

foreground_layer.add(text, rect)

# Animate the text and rectangle
text.scale(1.5, start=0, end=30).scale(1 / 1.5, start=30, end=60)
rect.rotate(360, start=0, end=60)

# Render the scene
