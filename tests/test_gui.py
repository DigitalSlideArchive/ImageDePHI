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
