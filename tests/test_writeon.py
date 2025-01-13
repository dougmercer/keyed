import pytest
from hypothesis import given
from hypothesis import strategies as st

from keyed import Scene, Text, TextSelection, lag_animation


@pytest.mark.parametrize("skip_whitespace", [True, False])
@given(delay=st.integers(1, 10), duration=st.integers(1, 10))
@pytest.mark.skip(reason="No longer makes sense. Need to test values instead.")
def test_write_on(delay: int, duration: int, skip_whitespace: bool) -> None:
    scene = Scene("test_scene", num_frames=6, width=100, height=100)
    items = [Text(scene, "a"), Text(scene, " "), Text(scene, "b")]
    text_selection = TextSelection(items)

    lagged_animation = lag_animation(0, 1)

    text_selection.write_on(
        property="alpha",
        lagged_animation=lagged_animation,
        start=0,
        delay=delay,
        duration=duration,
        skip_whitespace=skip_whitespace,
    )

    frame = 0
    for item in items:
        a = item.alpha.animations
        if not (skip_whitespace and item.is_whitespace()):
            assert (a[0].start_frame, a[0].end_frame) == (frame, frame + duration)
            frame += delay
        else:
            assert not a
