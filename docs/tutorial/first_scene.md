# Creating Your First Scene

Let's create a simple animation of a bouncing ball with a title. This tutorial will walk you through creating scenes, adding objects, and applying animations in Keyed.

## The Complete Code

Here's the complete code - feel free to run it now. After, we'll break down how it works.

```python title="examples/first_scene.py"
--8<-- "examples/first_scene.py"
```

<video controls>
<source src="../../media/bouncing_ball.webm" type="video/webm">
</video>

## Breaking It Down

### Creating the Scene
```python
scene = Scene(width=1920, height=1080, num_frames=120)
```
We start by creating a [Scene][keyed.scene.Scene] object, which serves as our canvas. Here we:

- Set the dimensions to 1920x1080 (Full HD resolution)
- Specify 120 frames for the animation (at 24 frames per second, this gives us a 5-second animation)

### Creating the Ball
```python
ball = (
    Circle(scene, x=200, y=200, radius=50)
    .center()
    .translate(0, 300, start=0, end=24, easing=easing.bounce_out)
    .scale(2, start=24, end=48, direction=DOWN)
    .translate(0, -300, start=60, end=110, easing=easing.elastic_out)
)
```
Here we create and animate the most interesting thing in the animation - a [Circle][keyed.shapes.Circle]. We apply a few key framed transformations to the object.

- `.center()` - Centers the circle in the scene
- First `.translate()` - Moves the ball down by 300 pixels with a bouncy easing
- `.scale()` - Doubles the size of the ball, scaling from the bottom [DOWN][keyed.constants.DOWN]
- Second `.translate()` - Moves the ball up with a snappy elastic easing

Notice how we specify start and end frames for each animation. The ball will:

- Drop and bounce (frames 0-24)
- Scale up (frames 24-48)
- Rest briefly (frames 48-60)
- Elastically snap back up to it's initial position (frames 60-110)

### Adding the Floor

```python
floor = Line(scene, x0=0, x1=scene.nx(1), y0=scene.ny(0.75), y1=scene.ny(0.75), line_width=5)
```

The floor is a simple [Line][keyed.line.Line] that:

- Spans the width of the scene. Here, we used the helper `[Scene.nx(...)][keyed.scene.Scene.nx]` to convert from a normalized value of 1 (100%) along the x direction to the true pixel value of 1920 (100% of the width of our scene).
- Is positioned far enough from the bottom of the scene that it kind of looks like the ball is bouncing on a floor.

Note that our Scene's cooridinate system is such that the top left corner of the scene is at coordinates `(0, 0)`, so when we specify `scene.ny(0.75)`, we're saying we should draw the line 75% of the height of the scene measured downwards from the top edge of the scene.

### Adding the Title
```python
title = Text(scene, "Thanks for dropping by!", size=100).move_to(scene.nx(0.5), scene.ny(0.2))
```

We create a [Text][keyed.code.Text] object that:

- Contains our message
- Has font size 100
- Is moved to the center of the scene horizontally and 20% downward vertically

### Rendering the Animation
```python
scene.add(floor, ball, title)
scene.preview()
```

Finally, we:

- Add all our objects to the scene
- Preview the animation in a window

## What did we learn?
This simple example demonstrates several key concepts in Keyed:

- Scene creation and object management
- Basic shapes and text
- Transformations and animations
- Easing functions
- Scene composition and rendering

Try modifying the code to:

- Change the timing of animations
- Use different easing functions
- Add more objects
- Modify the colors and styles
- Change the text message

<!-- ## What's next?

Next, let's take a closer look at the transformations available. -->
