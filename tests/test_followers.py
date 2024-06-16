from keyed import Expression, Property


class SimpleFollower:
    def at(self, frame: float) -> float:
        return frame * 10


def test_property_following() -> None:
    follower = SimpleFollower()
    prop = Property(value=0)
    prop.follow(follower)

    for frame in range(10):
        expected_value = frame * 10
        assert prop.at(frame) == expected_value, f"Failed at frame {frame}"


def test_lambda_follower() -> None:
    follower = Expression(lambda frame: frame * 10)
    prop = Property(value=0)
    prop.follow(follower)

    for frame in range(10):
        expected_value = frame * 10
        assert prop.at(frame) == expected_value, f"Failed at frame {frame}"


def test_property_offset() -> None:
    follower = SimpleFollower()
    prop = Property(value=0)
    prop.follow(follower).offset(5)

    for frame in range(10):
        expected_value = (frame * 10) + 5
        assert prop.at(frame) == expected_value, f"Failed at frame {frame}"
