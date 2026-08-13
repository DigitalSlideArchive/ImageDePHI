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
    assert response.json() == {"detail": "Input directory not found"}


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


def test_gui_redact_export_associated(
    client: TestClient,
    tmp_path: Path,
    data_dir: Path,
) -> None:
    """Test that export_associated=True creates an Associated directory."""
    response = client.post(
        app.url_path_for("redact"),
        params={
            "input_directory": str(data_dir / "input" / "svs"),
            "output_directory": str(tmp_path),
            "export_associated": True,
            "rename": False,
        },
    )

    assert response.status_code == 200
    associated_dirs = [d for d in tmp_path.iterdir() if "Associated" in str(d) and d.is_dir()]
    assert len(associated_dirs) == 1


def test_gui_redact_no_rename(
    client: TestClient,
    tmp_path: Path,
    data_dir: Path,
) -> None:
    """Test that rename=False preserves the original filename."""
    from freezegun import freeze_time

    with freeze_time("2023-05-12 12:12:53"):
        response = client.post(
            app.url_path_for("redact"),
            params={
                "input_directory": str(data_dir / "input" / "tiff"),
                "output_directory": str(tmp_path),
                "rename": False,
            },
        )

    assert response.status_code == 200
    output_file = tmp_path / "Redacted_2023-05-12_12-12-53" / "test_image.tif"
    assert output_file.exists()
