from signified import Signal

from keyed.animation import Animation, PingPong


def test_pingpong_animation() -> None:
    frame = Signal(0)
    prop = Signal(0)
    base_anim = Animation(start=0, end=2, start_value=0, end_value=2)
    pingpong_anim = PingPong(animation=base_anim, n=2)
    prop = pingpong_anim(prop, frame)

    expected = [0, 1, 2, 1, 0, 1, 2, 1, 0, 0]

    for frame_num, exp in enumerate(expected):
        with frame.at(frame_num):
            assert prop.value == exp, frame_num

    # assert prop.at(0) == 0
    # assert prop.at(1) == 1
    # assert prop.at(2) == 2
    # assert prop.at(3) == 1
    # assert prop.at(4) == 0
    # assert prop.at(5) == 1
    # assert prop.at(6) == 2
    # assert prop.at(7) == 1
    # assert prop.at(8) == 0
    # assert prop.at(9) == 0
