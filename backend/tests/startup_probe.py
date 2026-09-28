"""Fresh-process offline import/startup probe, invoked by test_startup.py."""

import importlib.abc
import socket
import sys

SCIENTIFIC_MODULES = {
    "argopy",
    "copernicusmarine",
    "erddapy",
    "gsw",
    "netCDF4",
    "numpy",
    "pandas",
    "pydap",
    "xarray",
}


class RejectScientificImports(importlib.abc.MetaPathFinder):
    """Fail even when scientific packages are installed in a future environment."""

    def find_spec(
        self, fullname: str, path: object = None, target: object = None
    ) -> None:
        if fullname.partition(".")[0] in SCIENTIFIC_MODULES:
            raise AssertionError(f"Unexpected scientific import: {fullname}")
        return None


def deny_connection(*args: object, **kwargs: object) -> None:
    raise AssertionError("Unexpected outbound networking during import/startup")


original_connect = socket.socket.connect
original_connect_ex = socket.socket.connect_ex


def guarded_connect(connection: socket.socket, address: object) -> None:
    # Windows' event-loop socket pair can connect to loopback internally;
    # provider connections must still fail before any external contact.
    if not isinstance(address, tuple) or address[0] not in ("127.0.0.1", "::1"):
        deny_connection()
    return original_connect(connection, address)


def guarded_connect_ex(connection: socket.socket, address: object) -> int:
    if not isinstance(address, tuple) or address[0] not in ("127.0.0.1", "::1"):
        deny_connection()
    return original_connect_ex(connection, address)


def run_probe(project_root: str) -> None:
    sys.path.insert(0, project_root)
    sys.meta_path.insert(0, RejectScientificImports())
    socket.create_connection = deny_connection
    socket.getaddrinfo = deny_connection
    socket.socket.connect = guarded_connect
    socket.socket.connect_ex = guarded_connect_ex
    socket.socket.sendto = deny_connection

    from fastapi.testclient import TestClient

    from backend.app.main import app

    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok",
            "service": "Project Ocean Backend",
        }
    imported_roots = {name.partition(".")[0] for name in sys.modules}
    assert not SCIENTIFIC_MODULES.intersection(imported_roots)
    print("Isolated import, startup, and health passed without scientific imports.")


if __name__ == "__main__":
    run_probe(sys.argv[1])
