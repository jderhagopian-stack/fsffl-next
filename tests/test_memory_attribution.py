from fsffl.memory_attribution import object_graph_size


def test_object_graph_size_counts_shared_values_once() -> None:
    shared = ["forecast-row", bytearray(32)]
    root = {"left": shared, "right": shared}

    total, nodes, truncated = object_graph_size(root)

    expected = sum(__import__("sys").getsizeof(item) for item in (root, "left", "right", shared, *shared))
    assert total >= expected
    assert nodes == 6
    assert not truncated


def test_object_graph_size_bounds_walk() -> None:
    root = list(range(100))

    _, nodes, truncated = object_graph_size(root, max_nodes=10)

    assert nodes == 11
    assert truncated
