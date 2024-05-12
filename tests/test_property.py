from copy import copy

import pytest

from keyed import Animation, AnimationType, Property


@pytest.mark.parametrize("frame, expected_value", [(0, 0), (5, 50), (10, 100), (15, 100)])
def test_value_with_single_animation(frame: int, expected_value: tuple[float, float]) -> None:
    prop = Property(value=0)
    anim = Animation(start_frame=0, end_frame=10, start_value=0, end_value=100)
    prop.add_animation(anim)
    assert prop.at(frame) == expected_value


def test_multiple_animations() -> None:
    prop = Property(value=0)
    anim1 = Animation(start_frame=0, end_frame=10, start_value=0, end_value=50)
    anim2 = Animation(start_frame=5, end_frame=15, start_value=50, end_value=100)
    prop.add_animation(anim1)
    prop.add_animation(anim2)
    assert prop.at(0) == 0
    assert prop.at(5) == 50
    assert prop.at(10) == 75  # Midway through second animation
    assert prop.at(15) == 100
    assert prop.at(20) == 100  # Beyond all animations


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
    assert prop.at(10) == expected_value


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

    assert prop.at(2) == 25  # Midway through first additive
    assert prop.at(3) == 30  # done with first animation, starting second
    assert prop.at(12) == 60  # Midway, so multiply by 2.
    assert prop.at(21) == 40  # start of absolute
    assert prop.at(22) == 60  # middle of absolute
    assert prop.at(23) == 80  # end of absolute
    assert prop.at(30) == 80  # after of absolute
    assert prop.at(32) == 85  # midway through second add
    assert prop.at(33) == 90  # done with second add


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

    assert prop.at(0) == 10
    assert prop.at(5) == 15 * 2  # Additive halfway, multiplicative starts
    assert prop.at(10) == 40  # Absolute starts
    assert prop.at(15) == 70  # second add starts
    assert prop.at(20) == 90  # animations done


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

    assert prop.at(0) == 1  # All start at 1
    assert prop.at(5) == 3  # Absolute in action, should override others
    assert prop.at(10) == 5  # Absolute ends, should have priority


def test_frame_check() -> None:
    with pytest.raises(ValueError):
        Animation(start_frame=10, end_frame=0, start_value=1, end_value=2)


def test_set() -> None:
    val = 5
    assert Property(10).set(val).at(0) == val


def test_offset() -> None:
    val = 5
    assert Property(10).offset(val).at(0) == 15


def test_is_animated() -> None:
    p = Property(10)
    assert not p.is_animated
    p.offset(5)
    assert p.is_animated


def test_copy() -> None:
    old = Property(10)
    new = copy(old)
    assert id(old) != id(new)
    assert new.following == old
