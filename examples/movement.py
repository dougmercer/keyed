from keyed import Scene, Text

scene = Scene(scene_name="movement", num_frames=24, width=1920, height=1080)

runner = Text(scene, "hello", size=64, font="Anonymous Pro", color=(0.5, 0.5, 0.5), x=50, y=50)
runner.translate(490, 490, 0, 24)
scene.add(runner)

scene.preview()
