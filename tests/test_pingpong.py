from keyed import Animation, PingPong, Property


def test_pingpong_animation() -> None:
    prop = Property(value=0)
    base_anim = Animation(start_frame=0, end_frame=2, start_value=0, end_value=2)
    pingpong_anim = PingPong(animation=base_anim, n=2)
    prop.add_animation(pingpong_anim)

    assert prop.at(0) == 0
    assert prop.at(1) == 1
    assert prop.at(2) == 2
    assert prop.at(3) == 1
    assert prop.at(4) == 0
    assert prop.at(5) == 1
    assert prop.at(6) == 2
    assert prop.at(7) == 1
    assert prop.at(8) == 0
    assert prop.at(9) == 0
