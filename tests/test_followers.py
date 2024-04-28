from keyed import LambdaFollower, Property


class SimpleFollower:
    def get_value_at_frame(self, frame: int) -> float:
        return frame * 10


def test_property_following():
    follower = SimpleFollower()
    prop = Property(value=0)
    prop.follow(follower)

    for frame in range(10):
        expected_value = frame * 10
        assert prop.get_value_at_frame(frame) == expected_value, f"Failed at frame {frame}"


def test_lambda_follower():
    follower = LambdaFollower(lambda frame: frame * 10)
    prop = Property(value=0)
    prop.follow(follower)

    for frame in range(10):
        expected_value = frame * 10
        assert prop.get_value_at_frame(frame) == expected_value, f"Failed at frame {frame}"


def test_property_offset():
    follower = SimpleFollower()
    prop = Property(value=0)
    prop.follow(follower).offset(5)

    for frame in range(10):
        expected_value = (frame * 10) + 5
        assert prop.get_value_at_frame(frame) == expected_value, f"Failed at frame {frame}"
