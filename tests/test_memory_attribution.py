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


def test_phase_entry_is_logged_before_work_can_fail(monkeypatch, caplog) -> None:
    import logging
    import pytest
    from fsffl import memory_attribution as memory
    monkeypatch.setattr(memory, 'enabled', lambda: True)
    with caplog.at_level(logging.INFO, logger='uvicorn.error'):
        with pytest.raises(RuntimeError, match='fixture failure'):
            with memory.sample_rss_phase('career.fixture'):
                assert 'phase=career.fixture status=start rss_before=' in caplog.text
                raise RuntimeError('fixture failure')
    assert 'phase=career.fixture elapsed=' in caplog.text


def test_phase_instrumentation_remains_opt_in(monkeypatch, caplog) -> None:
    import logging
    from fsffl import memory_attribution as memory
    monkeypatch.setattr(memory, 'enabled', lambda: False)
    with caplog.at_level(logging.INFO, logger='uvicorn.error'):
        with memory.sample_rss_phase('career.disabled'):
            pass
    assert 'career.disabled' not in caplog.text
