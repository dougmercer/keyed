from typing import Any, assert_type, cast

import pytest
from signified import Computed, Signal

from keyed import Animation, AnimationType, Line, Scene
from keyed.animation import step


@pytest.mark.parametrize("frame, expected_value", [(0, 0), (5, 50), (10, 100), (15, 100)])
def test_value_with_single_animation(frame: int, expected_value: tuple[float, float]) -> None:
    prop = Signal(0)
    anim = Animation(start=0, end=10, start_value=0, end_value=100)(prop, Signal(frame))
    assert anim.value == expected_value


def test_multiple_animations() -> None:
    frame = Signal(0)
    prop = Signal(0)
    prop = Animation(start=0, end=10, start_value=0, end_value=50)(prop, frame)
    prop = Animation(start=5, end=15, start_value=50, end_value=100)(prop, frame)
    for frame_val, expected in [(0, 0), (5, 50), (10, 75), (15, 100), (20, 100)]:
        with frame.at(frame_val):
            assert prop.value == expected


@pytest.mark.parametrize(
    "animation_type, expected_value",
    [
        (AnimationType.ABSOLUTE, 30),
        (AnimationType.ADD, 30 + 10),
        (AnimationType.MULTIPLY, 10 * 30),
    ],
)
def test_animation_types(animation_type: AnimationType, expected_value: float) -> None:
    frame = Signal(0)
    prop = Signal(10)
    prop = Animation(start=0, end=10, start_value=10, end_value=30, animation_type=animation_type)(prop, frame)
    frame.value = 10
    assert prop.value == expected_value


def test_sequential_different_types() -> None:
    frame = Signal(0)
    prop = Signal(10)
    add_anim = Animation(
        start=1,
        end=3,
        start_value=10,
        end_value=20,
        animation_type=AnimationType.ADD,
    )
    mul_anim = Animation(
        start=11,
        end=13,
        start_value=1,
        end_value=3,
        animation_type=AnimationType.MULTIPLY,
    )
    abs_anim = Animation(
        start=21,
        end=23,
        start_value=40,
        end_value=80,
        animation_type=AnimationType.ABSOLUTE,
    )
    second_add_anim = Animation(
        start=31,
        end=33,
        start_value=0,
        end_value=10,
        animation_type=AnimationType.ADD,
    )

    prop = add_anim(prop, frame)
    prop = mul_anim(prop, frame)
    prop = abs_anim(prop, frame)
    prop = second_add_anim(prop, frame)

    frame.value = 2
    assert prop.value == 25  # Midway through first additive
    frame.value = 3
    assert prop.value == 30  # done with first animation, starting second
    frame.value = 12
    assert prop.value == 60  # Midway, so multiply by 2.
    frame.value = 21
    assert prop.value == 40  # start of absolute
    frame.value = 22
    assert prop.value == 60  # middle of absolute
    frame.value = 23
    assert prop.value == 80  # end of absolute
    frame.value = 30
    assert prop.value == 80  # after of absolute
    frame.value = 32
    assert prop.value == 85  # midway through second add
    frame.value = 33
    assert prop.value == 90  # done with second add


def test_overlapping_different_types() -> None:
    frame = Signal(0)
    prop = Signal(10)
    add_anim = Animation(
        start=0,
        end=10,
        start_value=0,
        end_value=10,
        animation_type=AnimationType.ADD,
    )
    mul_anim = Animation(
        start=5,
        end=15,
        start_value=2,
        end_value=2,
        animation_type=AnimationType.MULTIPLY,
    )
    abs_anim = Animation(
        start=10,
        end=20,
        start_value=40,
        end_value=80,
        animation_type=AnimationType.ABSOLUTE,
    )
    second_add_anim = Animation(
        start=15,
        end=15,
        start_value=10,
        end_value=10,
        animation_type=AnimationType.ADD,
    )

    prop = add_anim(prop, frame)
    prop = mul_anim(prop, frame)
    prop = abs_anim(prop, frame)
    prop = second_add_anim(prop, frame)

    frame.value = 0
    assert prop.value == 10
    frame.value = 5
    assert prop.value == 15 * 2  # Additive halfway, multiplicative starts
    frame.value = 10
    assert prop.value == 40  # Absolute starts
    frame.value = 15
    assert prop.value == 70  # second add starts
    frame.value = 20
    assert prop.value == 90  # animations done


def test_interwoven_animations() -> None:
    frame = Signal(0)
    prop = Signal(1)
    add_anim = Animation(
        start=0,
        end=10,
        start_value=1,
        end_value=2,
        animation_type=AnimationType.ADD,
    )
    mul_anim = Animation(
        start=0,
        end=10,
        start_value=1,
        end_value=2,
        animation_type=AnimationType.MULTIPLY,
    )
    abs_anim = Animation(
        start=0,
        end=10,
        start_value=1,
        end_value=5,
        animation_type=AnimationType.ABSOLUTE,
    )

    prop = add_anim(prop, frame)
    prop = mul_anim(prop, frame)
    prop = abs_anim(prop, frame)

    frame.value = 0
    assert prop.value == 1  # All start at 1
    frame.value = 5
    assert prop.value == 3  # Absolute in action, should override others
    frame.value = 10
    assert prop.value == 5  # Absolute ends, should have priority


def test_frame_check() -> None:
    with pytest.raises(ValueError):
        Animation(start=10, end=0, start_value=1, end_value=2)


def test_set() -> None:
    frame = Signal(0)
    val = 5
    prop = Signal(10)

    prop = step(val)(prop, frame)
    assert prop.value == val


def test_offset() -> None:
    frame = Signal(0)
    val = 5
    prop = Signal(10)

    prop = step(val, animation_type=AnimationType.ADD)(prop, frame)
    assert prop.value == val + 10


def test_set_rebinds_geometry_dependencies() -> None:
    scene = Scene(num_frames=3, width=100, height=100)
    line = Line(scene=scene, x0=0, y0=0, x1=10, y1=0)

    line.set("x1", 20, frame=1)
    scene.frame.value = 0
    assert line.geom_now.coords[1][0] == 10

    scene.frame.value = 1
    assert line.geom_now.coords[1][0] == 20

    line.set("x1", 30, frame=2)
    scene.frame.value = 2
    assert line.geom_now.coords[1][0] == 30


def test_set_rebinds_geometry_dependencies_from_computed() -> None:
    scene = Scene(num_frames=4, width=100, height=100)
    base_x = Signal(10.0)
    line = Line(scene=scene, x0=0, y0=0, x1=base_x + 0.0, y1=0)

    line.set("x1", 20, frame=1)
    scene.frame.value = 1
    assert line.geom_now.coords[1][0] == 20

    line.set("x1", 30, frame=2)
    scene.frame.value = 2
    assert line.geom_now.coords[1][0] == 30


def test_animation_uses_active_scene_frame_by_default() -> None:
    scene = Scene(num_frames=4, width=100, height=100)
    prop = Signal(5)
    anim = Animation(start=1, end=3, start_value=10, end_value=30)(prop)

    scene.frame.value = 0
    assert anim.value == 5

    scene.frame.value = 2
    assert anim.value == 20

    scene.frame.value = 3
    assert anim.value == 30


def test_animation_requires_value_argument() -> None:
    anim = cast(Any, Animation(start=1, end=3, start_value=10, end_value=30))

    with pytest.raises(TypeError):
        anim()


def test_animation_explicit_frame_override_still_works() -> None:
    Scene(num_frames=4, width=100, height=100)
    other_frame = Signal(0)
    anim = Animation(
        start=1,
        end=3,
        start_value=10,
        end_value=30,
        animation_type=AnimationType.ADD,
    )(5, other_frame)

    other_frame.value = 0
    assert anim.value == 5

    other_frame.value = 2
    assert anim.value == 25


def test_animation_call_type_hints() -> None:
    scene = Scene(num_frames=4, width=100, height=100)

    inferred_frame_anim = Animation(start=1, end=3, start_value=10, end_value=30)(Signal(10))
    explicit_anim = Animation(start=1, end=3, start_value=10, end_value=30)(Signal(10), scene.frame)
    mixed_anim = Animation(start=1, end=3, start_value=10, end_value=30)("before-start")

    assert_type(inferred_frame_anim, Computed[int])
    assert_type(explicit_anim, Computed[int])
    assert_type(mixed_anim, Computed[str | int])
