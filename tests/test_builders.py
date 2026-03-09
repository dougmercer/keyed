"""Tests for Cues, Keys, and Flow animation builders."""

import pytest
from signified import Signal

from keyed import Animation
from keyed.builders import Cues, Flow, Keys


@pytest.fixture
def frame():
    return Signal(0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def evaluate(value, frame_signal, frames):
    """Step through a list of frame values and collect results."""
    results = []
    for f in frames:
        frame_signal.value = f
        try:
            results.append(value.value)
        except AttributeError:
            results.append(value)
    return results


def reference_colors(frame_signal):
    """The hand-rolled original from graph_of_computation.py (adapted to floats)."""
    black = 0.0
    yellow = 1.0
    x_color = Animation(120, 120 + 12, black, yellow)(black, frame_signal)
    x_color = Animation(120 + 36, 120 + 48, yellow, black)(x_color, frame_signal)
    return x_color


# ---------------------------------------------------------------------------
# Cues tests
# ---------------------------------------------------------------------------


class TestCues:
    def test_before_first_cue_returns_initial(self, frame):
        result = Cues(0.0).at(10, 1.0, over=5).build(frame)
        assert evaluate(result, frame, [0, 5, 9]) == [0.0, 0.0, 0.0]

    def test_transition_reaches_target(self, frame):
        result = Cues(0.0).at(10, 1.0, over=10).build(frame)
        frame.value = 20
        assert result.value == pytest.approx(1.0)

    def test_holds_after_transition(self, frame):
        result = Cues(0.0).at(10, 1.0, over=10).build(frame)
        assert evaluate(result, frame, [20, 50, 100]) == [1.0, 1.0, 1.0]

    def test_two_cues_matches_hand_rolled(self, frame):
        black, yellow = 0.0, 1.0
        result = Cues(black).at(120, yellow, over=12).at(120 + 36, black, over=12).build(frame)
        ref = reference_colors(frame)

        probe_frames = list(range(0, 200, 5))
        assert evaluate(result, frame, probe_frames) == pytest.approx(evaluate(ref, frame, probe_frames))

    def test_cues_inserted_out_of_order_are_sorted(self, frame):
        """Cues should be applied in chronological order regardless of insertion order."""
        black, yellow = 0.0, 1.0
        result_ordered = Cues(black).at(120, yellow, over=12).at(156, black, over=12).build(frame)
        result_unordered = Cues(black).at(156, black, over=12).at(120, yellow, over=12).build(frame)
        probe_frames = list(range(0, 200, 5))
        assert evaluate(result_ordered, frame, probe_frames) == pytest.approx(
            evaluate(result_unordered, frame, probe_frames)
        )

    def test_snap_is_instant(self, frame):
        result = Cues(0.0).snap(50, 1.0).build(frame)
        assert evaluate(result, frame, [49, 50, 51]) == [0.0, 1.0, 1.0]

    def test_no_cues_returns_initial(self, frame):
        result = Cues(42.0).build(frame)
        assert evaluate(result, frame, [0, 100]) == [42.0, 42.0]


# ---------------------------------------------------------------------------
# Flow tests
# ---------------------------------------------------------------------------


class TestFlow:
    def test_before_start_holds_initial(self, frame):
        result = Flow(0.0, at=50).tween(10, 1.0).build(frame)
        assert evaluate(result, frame, [0, 30, 49]) == pytest.approx([0.0, 0.0, 0.0])

    def test_tween_reaches_target(self, frame):
        result = Flow(0.0, at=10).tween(10, 1.0).build(frame)
        frame.value = 20
        assert result.value == pytest.approx(1.0)

    def test_matches_hand_rolled(self, frame):
        black, yellow = 0.0, 1.0
        result = Flow(black, at=120).tween(12, yellow).hold(24).tween(12, black).build(frame)
        ref = reference_colors(frame)
        probe = list(range(0, 200, 5))
        assert evaluate(result, frame, probe) == pytest.approx(evaluate(ref, frame, probe))

    def test_hold_defers_next_tween(self, frame):
        no_hold = Flow(0.0, at=10).tween(10, 1.0).tween(10, 0.0).build(frame)
        with_hold = Flow(0.0, at=10).tween(10, 1.0).hold(5).tween(10, 0.0).build(frame)
        frame.value = 22
        assert no_hold.value != pytest.approx(1.0)  # already animating back
        assert with_hold.value == pytest.approx(1.0)  # still holding

    def test_snap_is_instant(self, frame):
        result = Flow(0.0, at=10).snap(1.0).build(frame)
        assert evaluate(result, frame, [9, 10, 11]) == pytest.approx([0.0, 1.0, 1.0])

    def test_snap_does_not_advance_cursor(self):
        s = Flow(0.0, at=10)
        assert s._cursor == 10
        s.snap(1.0)
        assert s._cursor == 10

    def test_cursor_advances_correctly(self):
        s = Flow(0.0, at=0)
        s.tween(12, 1.0)
        assert s._cursor == 12
        s.hold(8)
        assert s._cursor == 20
        s.tween(5, 0.0)
        assert s._cursor == 25

    def test_default_at_is_zero(self, frame):
        result = Flow(0.0).tween(10, 1.0).build(frame)
        frame.value = 10
        assert result.value == pytest.approx(1.0)

    def test_no_segments_returns_initial(self, frame):
        result = Flow(7.0, at=0).build(frame)
        assert evaluate(result, frame, [0, 100]) == pytest.approx([7.0, 7.0])


# ---------------------------------------------------------------------------
# Keys tests
# ---------------------------------------------------------------------------


class TestKeys:
    def test_snap_snaps_at_frame(self, frame):
        """snap() holds initial value, then snaps at the named frame."""
        result = Keys(0.0).snap(120, 1.0).build(frame)
        assert evaluate(result, frame, [0, 119]) == pytest.approx([0.0, 0.0])
        frame.value = 120
        assert result.value == pytest.approx(1.0)

    def test_snap_holds_after_snap(self, frame):
        result = Keys(0.0).snap(120, 1.0).build(frame)
        assert evaluate(result, frame, [120, 200, 500]) == pytest.approx([1.0, 1.0, 1.0])

    def test_tween_fills_full_gap(self, frame):
        """tween() interpolates over the entire gap between previous mark and this one."""
        result = Keys(0.0).tween(120, 1.0).build(frame)
        frame.value = 0
        assert result.value == pytest.approx(0.0)
        frame.value = 120
        assert result.value == pytest.approx(1.0)

    def test_snap_then_tween(self, frame):
        """snap sets an anchor; subsequent tween fills only the remaining gap."""
        result = Keys(0.0).snap(108, 0.0).tween(120, 1.0).build(frame)
        assert evaluate(result, frame, [0, 107]) == pytest.approx([0.0, 0.0])
        frame.value = 108
        assert result.value == pytest.approx(0.0)
        frame.value = 120
        assert result.value == pytest.approx(1.0)

    def test_hold_then_tween(self, frame):
        """hold is cleaner sugar for the same-value anchor pattern."""
        result_explicit = Keys(0.0).snap(108, 0.0).tween(120, 1.0).build(frame)
        result_sugar = Keys(0.0).hold(108).tween(120, 1.0).build(frame)
        probe = list(range(0, 130, 1))
        assert evaluate(result_explicit, frame, probe) == pytest.approx(evaluate(result_sugar, frame, probe))

    def test_hold_tracks_sorted_previous_value(self, frame):
        """hold resolves its value from the sorted sequence, not call order."""
        result = Keys(0.0).snap(50, 1.0).hold(108).tween(120, 0.0).build(frame)
        frame.value = 108
        assert result.value == pytest.approx(1.0)
        frame.value = 120
        assert result.value == pytest.approx(0.0)

    def test_hold_works_out_of_order(self, frame):
        """hold inserted before an earlier tween still resolves correctly."""
        ordered = Keys(0.0).hold(100).tween(200, 1.0).tween(300, 0.0).build(frame)
        unordered = Keys(0.0).tween(200, 1.0).hold(100).tween(300, 0.0).build(frame)
        probe = list(range(0, 350, 10))
        assert evaluate(ordered, frame, probe) == pytest.approx(evaluate(unordered, frame, probe))

    def test_tween_then_snap(self, frame):
        """tween followed by snap: smooth first, then instant jump."""
        black, yellow, red = 0.0, 1.0, 0.5
        result = Keys(black).tween(120, yellow).snap(200, red).build(frame)
        frame.value = 120
        assert result.value == pytest.approx(yellow)
        assert evaluate(result, frame, [120, 150, 199]) == pytest.approx([yellow, yellow, yellow])
        frame.value = 200
        assert result.value == pytest.approx(red)

    def test_two_tweens(self, frame):
        """Consecutive tweens each span their own gap."""
        result = Keys(0.0).tween(100, 1.0).tween(200, 0.0).build(frame)
        frame.value = 0
        assert result.value == pytest.approx(0.0)
        frame.value = 100
        assert result.value == pytest.approx(1.0)
        frame.value = 200
        assert result.value == pytest.approx(0.0)
        frame.value = 150
        assert 0.0 < result.value < 1.0

    def test_matches_hand_rolled(self, frame):
        """snap+tween should match manually constructed Animations."""
        black, yellow = 0.0, 1.0
        result = Keys(black).snap(120, yellow).tween(168, black).build(frame)
        ref_snap = Animation(120, 120, yellow, yellow)(black, frame)
        ref_tween = Animation(120, 168, yellow, black)(ref_snap, frame)
        probe = list(range(0, 220, 4))
        assert evaluate(result, frame, probe) == pytest.approx(evaluate(ref_tween, frame, probe))

    def test_no_marks_returns_initial(self, frame):
        result = Keys(42.0).build(frame)
        assert evaluate(result, frame, [0, 100]) == pytest.approx([42.0, 42.0])

    def test_marks_out_of_order_are_sorted(self, frame):
        ordered = Keys(0.0).snap(100, 1.0).tween(200, 0.0).build(frame)
        unordered = Keys(0.0).tween(200, 0.0).snap(100, 1.0).build(frame)
        probe = list(range(0, 250, 5))
        assert evaluate(ordered, frame, probe) == pytest.approx(evaluate(unordered, frame, probe))
