from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from imagedephi.gui import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_gui_home(client: TestClient):
    response = client.get("/")

    assert response.status_code == 200
    assert "Select Directory" in response.text

def test_gui_navigate_success(client: TestClient, tmp_path: Path,):
    response = client.get("/?path=%s" % str(tmp_path))

    assert response.status_code == 200

def test_gui_navigate_not_found(client: TestClient, tmp_path: Path,):
    response = client.get("/?path=%s" % str(tmp_path/"fake") )

    assert response.status_code == 404
    assert response.json() == {"detail": "Directory not found"}

def test_gui_directory_selection(client: TestClient, tmp_path: Path,):
    response = client.post("/directory_selection/", data={"directory":str(tmp_path)})

    assert response.status_code == 200
    assert response.json() == {"message": "You chose this directory: %s" % tmp_path}

def test_gui_directory_selection_failure(client: TestClient, tmp_path: Path,):
    response = client.post("/directory_selection/", data={"directory":str(tmp_path/"fake")})

    assert response.status_code == 404
