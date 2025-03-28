from keyed import Animation, Scene, Text, easing
from signified import computed

s = Scene()


@computed
def as_str(val: float) -> str:
    return f"{val:.0f}"


x = Animation(0, 60, 200.0, s._width - 600, ease=easing.cubic_in_out)(0, s.frame)

t = Text(s, as_str(x), size=72, x=x)
t.lock_on(s, x=False)
s.add(t)
