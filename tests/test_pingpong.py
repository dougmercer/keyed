from keyed import Animation, PingPong, Property


def test_pingpong_animation() -> None:
    prop = Property(value=0)
    base_anim = Animation(start_frame=0, end_frame=2, start_value=0, end_value=2)
    pingpong_anim = PingPong(animation=base_anim, n=2)
    prop.add_animation(pingpong_anim)

    assert prop.get_value_at_frame(0) == 0
    assert prop.get_value_at_frame(1) == 1
    assert prop.get_value_at_frame(2) == 2
    assert prop.get_value_at_frame(3) == 1
    assert prop.get_value_at_frame(4) == 0
    assert prop.get_value_at_frame(5) == 1
    assert prop.get_value_at_frame(6) == 2
    assert prop.get_value_at_frame(7) == 1
    assert prop.get_value_at_frame(8) == 0
    assert prop.get_value_at_frame(9) == 0
