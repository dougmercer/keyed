import pytest

from keyed.helpers import ExtendedList, Freezeable, guard_frozen


def test_guard_frozen():
    class Blah:
        is_frozen = False

        @guard_frozen
        def blah(self):
            pass

    b = Blah()

    # This shouldn't fail...
    b.blah()

    # but this should.
    b.is_frozen = True
    with pytest.raises(ValueError):
        b.blah()


def test_extended_list():
    a = [0, 1, 2, 3]
    b = ExtendedList(a)
    b.append(5)
    b.append(6)
    b.append(7)
    a.append(4)

    assert list(range(8)) == list(b)

    for i in range(8):
        assert b[i] == i

    assert len(b) == 8

    assert repr(b) == repr(list(range(8)))


def test_freezeable():
    class Bleh(Freezeable):
        pass

    b = Bleh()

    # This should be OK
    b.a = 1

    # This should fail
    with pytest.raises(TypeError):
        hash(b)

    b.freeze()

    # Now this should fail...
    with pytest.raises(ValueError):
        b.a = 1

    # but this should work
    hash(b)
