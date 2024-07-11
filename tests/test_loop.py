from signified import Signal

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
