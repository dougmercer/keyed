import cairo
import shapely
import shapely.affinity
from shapely.geometry.base import BaseGeometry

from keyed import Animation, Rectangle, Scene

scene = Scene(num_frames=24 * 8)
s = 50
r = Rectangle(scene, x=10, y=10, width=s, height=s)

r.rotate(Animation(0, 10, 0, 45))
r.scale(Animation(0, 10, 1, 2))


def affine_transform(geom: BaseGeometry, matrix: cairo.Matrix | None) -> BaseGeometry:
    assert matrix is not None
    transform_params = [matrix.xx, matrix.xy, matrix.yx, matrix.yy, matrix.x0, matrix.y0]
    return shapely.affinity.affine_transform(geom, transform_params)


print(r.geom(10))
print(affine_transform(r.geom(10), r.get_matrix(10)))
