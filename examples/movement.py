from manic.animation import Animation, Character, Scene

scene = Scene(scene_name="fade_in_example", num_frames=24, width=1920, height=1080)

runner = Character(
    scene.ctx, "hello", size=64, font="Anonymous Pro", color=(0.5, 0.5, 0.5), x=10, y=10
)
runner.x.add_animation(Animation(start_frame=0, end_frame=24, start_value=10, end_value=500))
runner.y.add_animation(Animation(start_frame=0, end_frame=24, start_value=10, end_value=500))
