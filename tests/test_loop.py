from manic.animation import Animation, Loop, Property


def test_loop_animation():
    prop = Property(value=0)
    base_anim = Animation(start_frame=0, end_frame=2, start_value=0, end_value=2)
    loop_anim = Loop(animation=base_anim, n=3)
    prop.add_animation(loop_anim)

    assert prop.get_value_at_frame(0) == 0, 0
    assert prop.get_value_at_frame(1) == 1, 1
    assert prop.get_value_at_frame(2) == 2, 2
    assert prop.get_value_at_frame(3) == 0, 3
    assert prop.get_value_at_frame(4) == 1, 4
    assert prop.get_value_at_frame(5) == 2, 5
    assert prop.get_value_at_frame(6) == 0, 6
    assert prop.get_value_at_frame(7) == 1, 7
    assert prop.get_value_at_frame(8) == 2, 8
    assert prop.get_value_at_frame(9) == 2, 9
