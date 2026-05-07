from __future__ import annotations

import socket

import pytest

pytestmark = pytest.mark.integration


def _is_port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.fixture(scope="session", autouse=True)
def _skip_if_docker_down() -> None:
    if not _is_port_open("localhost", 10000):
        pytest.skip("Azurite is not running; start with `make up`")


def test_scaffold_runs_integration() -> None:
    assert True
