from app.constants import (
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_PLANNED,
)
from tests.factories import make_fabric, make_pattern, make_project


def test_dashboard_empty_state_links_to_pattern_and_fabric_setup(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Set up your workspace" in response.data
    assert b"Add a pattern" in response.data
    assert b"Add fabric" in response.data
    assert b"Nothing is in progress" in response.data
    assert b"No projects are waiting" in response.data
    assert b"Completed projects will collect here" in response.data


def test_dashboard_shows_all_status_groups(client):
    pattern = make_pattern()
    fabric = make_fabric()
    make_project(pattern, fabric, name="Planned Tote", status=STATUS_PLANNED)
    make_project(
        pattern, fabric, name="Current Tote", status=STATUS_IN_PROGRESS
    )
    make_project(pattern, fabric, name="Finished Tote", status=STATUS_COMPLETED)

    response = client.get("/")
    assert response.status_code == 200
    assert b"Planned Tote" in response.data
    assert b"Current Tote" in response.data
    assert b"Finished Tote" in response.data
    assert b"New project" in response.data


def test_dashboard_includes_quick_status_controls(client):
    pattern = make_pattern()
    fabric = make_fabric()
    project = make_project(pattern, fabric)

    response = client.get("/")
    assert (
        f'/projects/{project.id}/status'.encode()
        in response.data
    )
    assert b'<option value="Completed"' in response.data


def test_navigation_links_all_main_pages(client):
    response = client.get("/")
    assert b">Dashboard</a>" in response.data
    assert b">Projects</a>" in response.data
    assert b">Patterns</a>" in response.data
    assert b">Fabrics</a>" in response.data
