from app.constants import (
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_PLANNED,
)
from app.models import Fabric, Pattern, Project, db
from tests.factories import make_fabric, make_pattern, make_piece, make_project


def project_form_data(pattern, outer, **overrides):
    values = {
        "name": "Weekend Tote",
        "pattern_id": str(pattern.id),
        "outer_fabric_id": str(outer.id),
        "lining_fabric_id": "",
        "status": STATUS_PLANNED,
        "notes": "Use contrast thread",
    }
    values.update(overrides)
    return values


def test_new_project_empty_state_links_to_missing_dependencies(client):
    response = client.get("/projects/new")
    assert response.status_code == 200
    assert b"Add a pattern" in response.data
    assert b"Add fabric" in response.data


def test_create_project_form_includes_preview_panel(client):
    pattern = make_pattern()
    make_fabric()
    response = client.get("/projects/new")
    assert response.status_code == 200
    assert b"Project preview" in response.data
    assert b'data-form-preview="project"' in response.data
    assert b"Preview yardage" not in response.data
    assert b"Save project" in response.data
    assert pattern.name.encode() in response.data


def test_create_project_with_required_outer_and_optional_lining(client):
    pattern = make_pattern()
    outer = make_fabric(name="Outer")

    response = client.post(
        "/projects/new",
        data=project_form_data(pattern, outer),
        follow_redirects=True,
    )
    assert response.status_code == 200
    project = Project.query.filter_by(name="Weekend Tote").one()
    assert project.pattern is pattern
    assert project.outer_fabric is outer
    assert project.lining_fabric is None
    assert project.status == STATUS_PLANNED
    assert b"Lining is still needed" in response.data


def test_create_project_allows_same_outer_and_lining_fabric(client):
    pattern = make_pattern()
    fabric = make_fabric(name="Self Lining Cotton")

    response = client.post(
        "/projects/new",
        data=project_form_data(
            pattern, fabric, lining_fabric_id=str(fabric.id)
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    project = Project.query.one()
    assert project.outer_fabric_id == project.lining_fabric_id


def test_project_name_is_required_and_not_generated(client):
    pattern = make_pattern()
    fabric = make_fabric()
    response = client.post(
        "/projects/new",
        data=project_form_data(pattern, fabric, name=""),
    )
    assert response.status_code == 400
    assert b"Project name is required" in response.data
    assert Project.query.count() == 0


def test_project_status_must_be_allowed_on_create(client):
    pattern = make_pattern()
    fabric = make_fabric()
    response = client.post(
        "/projects/new",
        data=project_form_data(pattern, fabric, status="Almost Done"),
    )
    assert response.status_code == 400
    assert b"valid project status" in response.data
    assert Project.query.count() == 0


def test_create_rejects_missing_or_unknown_relationships(client):
    pattern = make_pattern()
    fabric = make_fabric()

    missing_outer = client.post(
        "/projects/new",
        data=project_form_data(pattern, fabric, outer_fabric_id=""),
    )
    assert missing_outer.status_code == 400
    assert b"Outer fabric is required" in missing_outer.data

    unknown_pattern = client.post(
        "/projects/new",
        data=project_form_data(pattern, fabric, pattern_id="9999"),
    )
    assert unknown_pattern.status_code == 400
    assert b"existing pattern" in unknown_pattern.data
    assert Project.query.count() == 0


def test_project_preview_shows_yardage_and_enough_answers(client):
    pattern = make_pattern(
        estimated_hours=3.5,
        outer_yards_required=1.0,
        lining_yards_required=0.75,
    )
    outer = make_fabric(name="Plenty of Canvas", yards_available=2.5)
    lining = make_fabric(name="Short Lining", yards_available=0.5)

    response = client.get(
        "/projects/new",
        query_string=project_form_data(
            pattern,
            outer,
            lining_fabric_id=str(lining.id),
        ),
    )
    assert response.status_code == 200
    assert b"Estimated time: 3.5 hours" in response.data
    assert b"Pattern requires: 1.0 yards" in response.data
    assert b"Selected fabric available: 2.5 yards" in response.data
    assert b"Enough fabric:" in response.data
    assert b'yardage-result--yes" data-yardage-result>Yes<' in response.data
    assert b"Pattern requires: 0.75 yards" in response.data
    assert b"Selected fabric available: 0.5 yards" in response.data
    assert b'yardage-result--no" data-yardage-result>No<' in response.data
    assert b"Selected fabrics" in response.data
    assert b"Plenty of Canvas" in response.data
    assert b"2.5 yd on hand" in response.data
    assert b"Short Lining" in response.data
    assert b"0.5 yd on hand" in response.data


def test_pattern_with_zero_lining_yards_still_requires_lining(client):
    pattern = make_pattern(lining_yards_required=0.0)
    outer = make_fabric()
    response = client.get(
        "/projects/new",
        query_string=project_form_data(pattern, outer),
    )
    assert response.status_code == 200
    assert b"Pattern requires: 0.0 yards" in response.data
    assert b"Lining is still needed" in response.data
    assert b"does not require lining" not in response.data


def test_pattern_with_none_lining_yards_does_not_require_lining(client):
    pattern = make_pattern(lining_yards_required=None)
    outer = make_fabric()
    response = client.get(
        "/projects/new",
        query_string=project_form_data(pattern, outer),
    )
    assert response.status_code == 200
    assert b"This pattern does not require lining" in response.data
    assert b"Lining is still needed" not in response.data


def test_insufficient_fabric_does_not_block_save_or_change_inventory(client):
    pattern = make_pattern(outer_yards_required=3.0)
    outer = make_fabric(yards_available=1.0)

    response = client.post(
        "/projects/new",
        data=project_form_data(pattern, outer),
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert Project.query.count() == 1
    assert db.session.get(Fabric, outer.id).yards_available == 1.0
    assert b"Enough fabric:" in response.data
    assert b'yardage-result--no">No<' in response.data


def test_project_list_filters_by_status_and_defaults_to_in_progress(client):
    pattern = make_pattern()
    fabric = make_fabric()
    make_project(pattern, fabric, name="Plan Me", status=STATUS_PLANNED)
    make_project(pattern, fabric, name="Sew Me", status=STATUS_IN_PROGRESS)
    make_project(pattern, fabric, name="Done", status=STATUS_COMPLETED)

    default_response = client.get("/projects/")
    assert b"Sew Me" in default_response.data
    assert b"Plan Me" not in default_response.data
    assert b"Done" not in default_response.data

    planned_response = client.get(
        "/projects/", query_string={"status": STATUS_PLANNED}
    )
    assert b"Plan Me" in planned_response.data
    assert b"Sew Me" not in planned_response.data
    assert b"Planned (1)" in planned_response.data
    assert b"In Progress (1)" in planned_response.data
    assert b"Completed (1)" in planned_response.data


def test_project_detail_shows_pattern_fabrics_time_and_pieces(client):
    pattern = make_pattern(estimated_hours=4)
    make_piece(pattern, piece_name="Front Panel")
    outer = make_fabric(name="Green Canvas")
    lining = make_fabric(name="Dot Lining")
    project = make_project(pattern, outer, lining_fabric=lining)

    response = client.get(f"/projects/{project.id}")
    assert response.status_code == 200
    assert b"Small Tote Bag" in response.data
    assert b"Green Canvas" in response.data
    assert b"Dot Lining" in response.data
    assert b"4.0 hours" in response.data
    assert b"Front Panel" in response.data


def test_edit_project_reassigns_pattern_and_fabrics(client):
    first_pattern = make_pattern(name="First")
    second_pattern = make_pattern(name="Second")
    first_fabric = make_fabric(name="First Fabric")
    second_fabric = make_fabric(name="Second Fabric")
    project = make_project(first_pattern, first_fabric)

    response = client.post(
        f"/projects/{project.id}/edit",
        data=project_form_data(
            second_pattern,
            second_fabric,
            name="Replanned Tote",
            status=STATUS_IN_PROGRESS,
        ),
        follow_redirects=True,
    )
    assert response.status_code == 200
    updated = db.session.get(Project, project.id)
    assert updated.name == "Replanned Tote"
    assert updated.pattern_id == second_pattern.id
    assert updated.outer_fabric_id == second_fabric.id
    assert updated.status == STATUS_IN_PROGRESS


def test_quick_status_change_accepts_allowed_status(client):
    pattern = make_pattern()
    fabric = make_fabric()
    project = make_project(pattern, fabric, status=STATUS_PLANNED)

    response = client.post(
        f"/projects/{project.id}/status",
        data={"status": STATUS_COMPLETED},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert db.session.get(Project, project.id).status == STATUS_COMPLETED


def test_quick_status_change_uses_safe_internal_redirect(client):
    pattern = make_pattern()
    fabric = make_fabric()
    project = make_project(pattern, fabric, status=STATUS_PLANNED)

    response = client.post(
        f"/projects/{project.id}/status",
        data={"status": STATUS_IN_PROGRESS},
        headers={"Referer": "https://example.com/untrusted"},
    )
    assert response.status_code == 302
    assert response.location.endswith("/projects/?status=In+Progress")


def test_quick_status_change_rejects_arbitrary_status(client):
    pattern = make_pattern()
    fabric = make_fabric()
    project = make_project(pattern, fabric, status=STATUS_PLANNED)

    response = client.post(
        f"/projects/{project.id}/status",
        data={"status": "Almost Done"},
    )
    assert response.status_code == 400
    assert db.session.get(Project, project.id).status == STATUS_PLANNED


def test_delete_project_preserves_pattern_and_fabrics(client):
    pattern = make_pattern()
    outer = make_fabric(name="Outer")
    lining = make_fabric(name="Lining")
    project = make_project(pattern, outer, lining_fabric=lining)
    project_id = project.id

    response = client.post(
        f"/projects/{project_id}/delete", follow_redirects=True
    )
    assert response.status_code == 200
    assert db.session.get(Project, project_id) is None
    assert db.session.get(Pattern, pattern.id) is not None
    assert db.session.get(Fabric, outer.id) is not None
    assert db.session.get(Fabric, lining.id) is not None
