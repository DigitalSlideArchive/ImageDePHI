from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from imagedephi.gui.app import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_gui_select_directory(client: TestClient) -> None:
    response = client.get(app.url_path_for("select_directory"))

    assert response.status_code == 200


def test_gui_select_directory_success(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.get(
        app.url_path_for("select_directory"),
        params={"input_directory": str(tmp_path), "output_directory": str(tmp_path)},
    )

    assert response.status_code == 200


def test_gui_select_directory_not_found(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.get(
        app.url_path_for("select_directory"), params={"directory": str(tmp_path / "fake")}
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Input directory not a directory"}


def test_gui_redact(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.post(
        app.url_path_for("redact"),
        params={"input_directory": str(tmp_path), "output_directory": str(tmp_path)},
    )

    assert response.status_code == 200


def test_gui_redact_input_failure(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.post(
        app.url_path_for("redact"),
        params={"input_directory": str(tmp_path / "fake"), "output_directory": str(tmp_path)},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Input directory not found"}


def test_gui_redact_output_failure(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.post(
        app.url_path_for("redact"),
        params={"input_directory": str(tmp_path), "output_directory": str(tmp_path / "fake")},
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Output directory not found"}
