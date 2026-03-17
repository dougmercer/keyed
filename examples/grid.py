from keyed import DR, UP, Animation, Background, Color, Rectangle, Scene, Text
from keyed.grid import Grid

# Create a scene
scene = Scene(num_frames=120, width=1200, height=800)

# Add a background
background = Background(color=(0.1, 0.1, 0.1), fill_color=(0.1, 0.1, 0.1))
scene.add(background)

# Create a 5x5 checker board
grid = Grid(
    width=300,
    height=300,
    rows=5,
    cols=5,
    color=(0.5, 0.5, 0.5),
    line_width=2,
)

# for i in range(5):
#     for j in range(5):
#         if (i + j) % 2 == 0:
#             grid.style_cell(i, j, color=(0.4, 0.4, 0.8))
scene.add(grid)

# Add a title
title = Text(text="Whoa, a grid!", size=18, color=(1, 1, 1)).next_to(scene, direction=UP, offset=-50)
scene.add(title)

# Add stuff to different cells of the grid
t1 = Text("Hey!")
grid.place_in_cell(t1, 3, 4)

rect = Rectangle(
    width=40,
    height=20,
    color=(0.2, 0.8, 0.2),
    fill_color=(0.3, 0.9, 0.3),
)
grid.place_in_cell(rect, 4, 4)

color = Animation(0, 24, Color(1, 0, 0), Color(0, 1, 0))(Color(1, 0, 0), scene.frame)
grid.style_cell(2, 2, color, alpha=0.3)

# Move the grid around
grid.translate(0, 100, 0, 12).translate(100, 0, 12, 24).scale(0.5, 24, 36).rotate(45, 0, 12)
