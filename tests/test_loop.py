from keyed import Animation, Loop, Property


def test_loop_animation() -> None:
    prop = Property(value=0)
    base_anim = Animation(start_frame=0, end_frame=2, start_value=0, end_value=2)
    loop_anim = Loop(animation=base_anim, n=3)
    prop.add_animation(loop_anim)

    assert prop.at(0) == 0, 0
    assert prop.at(1) == 1, 1
    assert prop.at(2) == 2, 2
    assert prop.at(3) == 0, 3
    assert prop.at(4) == 1, 4
    assert prop.at(5) == 2, 5
    assert prop.at(6) == 0, 6
    assert prop.at(7) == 1, 7
    assert prop.at(8) == 2, 8
    assert prop.at(9) == 2, 9
