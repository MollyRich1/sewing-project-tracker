from app.constants import (
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_PLANNED,
)
from tests.factories import make_fabric, make_pattern, make_project


def test_dashboard_empty_state_links_to_pattern_and_fabric_setup(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Set up your sewing table" in response.data
    assert b"Add a pattern" in response.data
    assert b"Add fabric" in response.data
    assert b"No project is in progress" in response.data
    assert b"Your projects will gather here" in response.data
    assert b"0 yd" in response.data


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
    assert b"In Progress" in response.data
    assert b"Planned" in response.data
    assert b"Completed" in response.data
    assert b"+ New Project" in response.data


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
    assert b"+ New Project</a>" in response.data


def test_dashboard_uses_real_fabric_and_pattern_data(client):
    first_pattern = make_pattern(name="First Pattern")
    make_pattern(name="Second Pattern", lining_yards_required=None)
    first_fabric = make_fabric(name="Canvas", yards_available=2.5)
    make_fabric(name="Cotton", yards_available=1.25)
    make_project(first_pattern, first_fabric, name="Current Make")

    response = client.get("/")
    assert response.status_code == 200
    assert b">2</strong>" in response.data
    assert b"fabrics" in response.data
    assert b"3.75 yd" in response.data
    assert b"Canvas" in response.data
    assert b"Cotton" in response.data
    assert b"First Pattern" in response.data
    assert b"Second Pattern" in response.data


def test_dashboard_limits_compact_project_grid_to_three(client):
    pattern = make_pattern()
    fabric = make_fabric()
    for index in range(4):
        make_project(
            pattern,
            fabric,
            name=f"Project {index}",
            status=STATUS_PLANNED,
        )

    response = client.get("/")
    assert response.status_code == 200
    assert response.data.count(b'class="mini-project"') == 3
