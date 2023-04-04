from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from imagedephi.gui import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_gui_home(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Select Directory" in response.text


def test_gui_navigate_success(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.get(
        "/", params={"input_directory": str(tmp_path), "output_directory": str(tmp_path)}
    )

    assert response.status_code == 200


def test_gui_navigate_input_not_found(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.get("/", params={"input_directory": str(tmp_path / "fake")})

    assert response.status_code == 404
    assert response.json() == {"detail": "Input directory not a directory"}


def test_gui_navigate_output_not_found(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.get("/", params={"output_directory": str(tmp_path / "fake")})

    assert response.status_code == 404
    assert response.json() == {"detail": "Output directory not a directory"}


def test_gui_redact(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.post(
        "/redact/",
        data={
            "input_directory": str(tmp_path),
            "output_directory": str(tmp_path),
            "overwrite": str(False),
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": (
            f"You chose this input directory: {tmp_path} and this output directory: {tmp_path}"
        )
    }


def test_gui_redact_input_failure(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.post(
        "/redact/",
        data={
            "input_directory": str(tmp_path / "fake"),
            "output_directory": str(tmp_path),
            "overwrite": str(False),
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Input directory not found"}


def test_gui_redact_output_failure(
    client: TestClient,
    tmp_path: Path,
) -> None:
    response = client.post(
        "/redact/",
        data={
            "input_directory": str(tmp_path),
            "output_directory": str(tmp_path / "fake"),
            "overwrite": str(False),
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Output directory not found"}
