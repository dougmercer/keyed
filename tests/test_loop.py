from signified import Signal

from keyed import Scene
from keyed.animation import Animation, Loop


def test_loop_animation() -> None:
    frame = Signal(0)
    prop = Signal(0)
    base_anim = Animation(start=0, end=2, start_value=0, end_value=2)
    loop_anim = Loop(animation=base_anim, n=3)
    prop = loop_anim(prop, frame)

    expected = [0, 1, 2, 0, 1, 2, 0, 1, 2, 2]

    for frame_num, exp in enumerate(expected):
        with frame.at(frame_num):
            assert prop.value == exp, frame_num


def test_loop_uses_active_scene_frame_by_default() -> None:
    scene = Scene(num_frames=5, width=100, height=100)
    loop_anim = Loop(Animation(start=1, end=2, start_value=3, end_value=5), n=2)(9)

    scene.frame.value = 0
    assert loop_anim.value == 9

    scene.frame.value = 1
    assert loop_anim.value == 3

    scene.frame.value = 2
    assert loop_anim.value == 5
