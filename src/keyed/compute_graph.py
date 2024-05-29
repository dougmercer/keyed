from typing import Self, Sequence

import cairo
import networkx as nx

from .transformation import Transform, Transformable


class TransformDependencyGraph:
    def __init__(self) -> None:
        self.graph = nx.DiGraph()

    @classmethod
    def from_transforms(cls, transforms: Sequence[Transform] | None = None) -> Self:
        transforms = transforms or Transform.all_transforms
        new = cls()
        for t in transforms:
            new.add_transform(t)
        return new

    def add_transform(self, transform: Transform) -> None:
        self.graph.add_node(transform, transform=transform)
        if hasattr(transform, "center"):
            dependency: Transformable = transform.center
            self.graph.add_node(dependency, dependency=dependency)
            self.graph.add_edge(dependency, transform)

    def sorted_transforms(self) -> list[Transform]:
        sorted_nodes = nx.topological_sort(self.graph)
        return [self.graph.nodes[node]["transform"] for node in sorted_nodes]

    def draw(self) -> None:
        from matplotlib import pyplot as plt

        nx.draw(self.graph)
        plt.axis("off")  # turn off axis
        plt.show()


def apply_transforms(frame: int, transforms: list[Transform]) -> cairo.Matrix:
    matrix = cairo.Matrix()
    graph = TransformDependencyGraph.from_transforms(transforms)
    raise NotImplementedError
    for transform in graph.sorted_transforms():
        matrix = matrix.multiply(transform.get_matrix(frame))
    return matrix
