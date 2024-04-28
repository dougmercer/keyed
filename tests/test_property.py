import pytest

from keyed import Animation, AnimationType, Property


@pytest.mark.parametrize("frame, expected_value", [(0, 0), (5, 50), (10, 100), (15, 100)])
def test_value_with_single_animation(frame: int, expected_value: tuple[float, float]) -> None:
    prop = Property(value=0)
    anim = Animation(start_frame=0, end_frame=10, start_value=0, end_value=100)
    prop.add_animation(anim)
    assert prop.get_value_at_frame(frame) == expected_value


def test_multiple_animations() -> None:
    prop = Property(value=0)
    anim1 = Animation(start_frame=0, end_frame=10, start_value=0, end_value=50)
    anim2 = Animation(start_frame=5, end_frame=15, start_value=50, end_value=100)
    prop.add_animation(anim1)
    prop.add_animation(anim2)
    assert prop.get_value_at_frame(0) == 0
    assert prop.get_value_at_frame(5) == 50
    assert prop.get_value_at_frame(10) == 75  # Midway through second animation
    assert prop.get_value_at_frame(15) == 100
    assert prop.get_value_at_frame(20) == 100  # Beyond all animations


@pytest.mark.parametrize(
    "animation_type, expected_value",
    [
        (AnimationType.ABSOLUTE, 30),
        (AnimationType.ADDITIVE, 30 + 10),
        (AnimationType.MULTIPLICATIVE, 10 * 30),
    ],
)
def test_animation_types(animation_type: AnimationType, expected_value: float) -> None:
    prop = Property(value=10)
    anim = Animation(
        start_frame=0, end_frame=10, start_value=10, end_value=30, animation_type=animation_type
    )
    prop.add_animation(anim)
    assert prop.get_value_at_frame(10) == expected_value


def test_sequential_different_types() -> None:
    prop = Property(value=10)
    add_anim = Animation(
        start_frame=1,
        end_frame=3,
        start_value=10,
        end_value=20,
        animation_type=AnimationType.ADDITIVE,
    )
    mul_anim = Animation(
        start_frame=11,
        end_frame=13,
        start_value=1,
        end_value=3,
        animation_type=AnimationType.MULTIPLICATIVE,
    )
    abs_anim = Animation(
        start_frame=21,
        end_frame=23,
        start_value=40,
        end_value=80,
        animation_type=AnimationType.ABSOLUTE,
    )
    second_add_anim = Animation(
        start_frame=31,
        end_frame=33,
        start_value=0,
        end_value=10,
        animation_type=AnimationType.ADDITIVE,
    )

    prop.add_animation(add_anim)
    prop.add_animation(mul_anim)
    prop.add_animation(abs_anim)
    prop.add_animation(second_add_anim)

    assert prop.get_value_at_frame(2) == 25  # Midway through first additive
    assert prop.get_value_at_frame(3) == 30  # done with first animation, starting second
    assert prop.get_value_at_frame(12) == 60  # Midway, so multiply by 2.
    assert prop.get_value_at_frame(21) == 40  # start of absolute
    assert prop.get_value_at_frame(22) == 60  # middle of absolute
    assert prop.get_value_at_frame(23) == 80  # end of absolute
    assert prop.get_value_at_frame(30) == 80  # after of absolute
    assert prop.get_value_at_frame(32) == 85  # midway through second add
    assert prop.get_value_at_frame(33) == 90  # done with second add


def test_overlapping_different_types() -> None:
    prop = Property(value=10)
    add_anim = Animation(
        start_frame=0,
        end_frame=10,
        start_value=0,
        end_value=10,
        animation_type=AnimationType.ADDITIVE,
    )
    mul_anim = Animation(
        start_frame=5,
        end_frame=15,
        start_value=2,
        end_value=2,
        animation_type=AnimationType.MULTIPLICATIVE,
    )
    abs_anim = Animation(
        start_frame=10,
        end_frame=20,
        start_value=40,
        end_value=80,
        animation_type=AnimationType.ABSOLUTE,
    )
    second_add_anim = Animation(
        start_frame=15,
        end_frame=15,
        start_value=10,
        end_value=10,
        animation_type=AnimationType.ADDITIVE,
    )

    prop.add_animation(add_anim)
    prop.add_animation(mul_anim)
    prop.add_animation(abs_anim)
    prop.add_animation(second_add_anim)

    assert prop.get_value_at_frame(0) == 10
    assert prop.get_value_at_frame(5) == 15 * 2  # Additive halfway, multiplicative starts
    assert prop.get_value_at_frame(10) == 40  # Absolute starts
    assert prop.get_value_at_frame(15) == 70  # second add starts
    assert prop.get_value_at_frame(20) == 90  # animations done


def test_interwoven_animations() -> None:
    prop = Property(value=1)
    add_anim = Animation(
        start_frame=0,
        end_frame=10,
        start_value=1,
        end_value=2,
        animation_type=AnimationType.ADDITIVE,
    )
    mul_anim = Animation(
        start_frame=0,
        end_frame=10,
        start_value=1,
        end_value=2,
        animation_type=AnimationType.MULTIPLICATIVE,
    )
    abs_anim = Animation(
        start_frame=0,
        end_frame=10,
        start_value=1,
        end_value=5,
        animation_type=AnimationType.ABSOLUTE,
    )

    prop.add_animation(add_anim)
    prop.add_animation(mul_anim)
    prop.add_animation(abs_anim)

    assert prop.get_value_at_frame(0) == 1  # All start at 1
    assert prop.get_value_at_frame(5) == 3  # Absolute in action, should override others
    assert prop.get_value_at_frame(10) == 5  # Absolute ends, should have priority
