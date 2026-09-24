from app.models import Pattern, PatternPiece, db
from tests.factories import make_fabric, make_pattern, make_piece, make_project


def test_pattern_list_and_empty_state(client):
    response = client.get("/patterns/")
    assert response.status_code == 200
    assert b"No patterns yet" in response.data

    make_pattern(name="Small Tote Bag")
    response = client.get("/patterns/")
    assert b"Small Tote Bag" in response.data
    assert b"3.0 hours" in response.data
    assert b"Outer fabric: 1.0 yards" in response.data
    assert b"Lining fabric: 0.5 yards" in response.data


def test_pattern_form_includes_preview_panel(client):
    response = client.get("/patterns/new")
    assert response.status_code == 200
    assert b"Pattern preview" in response.data
    assert b'data-form-preview="pattern"' in response.data


def test_pattern_list_shows_no_lining_when_yards_are_none(client):
    make_pattern(name="Scrunchie", lining_yards_required=None)
    response = client.get("/patterns/")
    assert b"Does not require lining" in response.data


def test_pattern_list_shows_zero_lining_yards(client):
    make_pattern(name="Zero lining", lining_yards_required=0.0)
    response = client.get("/patterns/")
    assert b"Lining fabric: 0.0 yards" in response.data
    assert b"Does not require lining" not in response.data


def test_create_pattern(client):
    response = client.post(
        "/patterns/new",
        data={
            "name": "Zipper Pouch",
            "estimated_hours": "2.5",
            "outer_yards_required": "0.75",
            "lining_yards_required": "0.5",
            "notions": "9in zipper",
            "notes": "Good beginner project",
            "image_url": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    pattern = Pattern.query.filter_by(name="Zipper Pouch").one()
    assert pattern.estimated_hours == 2.5
    assert pattern.outer_yards_required == 0.75
    assert pattern.lining_yards_required == 0.5
    assert b"Zipper Pouch" in response.data


def test_create_pattern_blank_lining_stores_none(client):
    client.post(
        "/patterns/new",
        data={
            "name": "No lining bag",
            "estimated_hours": "1",
            "outer_yards_required": "0.5",
            "lining_yards_required": "",
            "notions": "",
            "notes": "",
            "image_url": "",
        },
    )
    pattern = Pattern.query.filter_by(name="No lining bag").one()
    assert pattern.lining_yards_required is None


def test_create_pattern_rejects_negative_hours(client):
    response = client.post(
        "/patterns/new",
        data={
            "name": "Bad hours",
            "estimated_hours": "-2",
            "outer_yards_required": "1",
            "lining_yards_required": "",
            "notions": "",
            "notes": "",
            "image_url": "",
        },
    )
    assert response.status_code == 400
    assert b"cannot be negative" in response.data
    assert Pattern.query.count() == 0


def test_edit_pattern(client):
    pattern = make_pattern(name="Tote")
    response = client.post(
        f"/patterns/{pattern.id}/edit",
        data={
            "name": "Updated tote",
            "estimated_hours": "4",
            "outer_yards_required": "1.5",
            "lining_yards_required": "0",
            "notions": "snap",
            "notes": "updated",
            "image_url": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert db.session.get(Pattern, pattern.id).name == "Updated tote"
    assert db.session.get(Pattern, pattern.id).lining_yards_required == 0.0
    assert b"Updated tote" in response.data


def test_pattern_detail_lists_pieces(client):
    pattern = make_pattern()
    make_piece(pattern, piece_name="Front Panel", quantity_to_cut=2)
    response = client.get(f"/patterns/{pattern.id}")
    assert response.status_code == 200
    assert b"Front Panel" in response.data
    assert b"Cut 2" in response.data
    assert b"12in x 18in" in response.data
    assert b"Fabric type: Outer" in response.data


def test_add_edit_and_delete_piece(client):
    pattern = make_pattern()
    add_response = client.post(
        f"/patterns/{pattern.id}/pieces",
        data={
            "piece_name": "Handle Strap",
            "quantity_to_cut": "2",
            "measurements": "4in x 22in",
            "fabric_type": "Outer",
            "image_url": "",
            "notes": "",
        },
        follow_redirects=True,
    )
    assert add_response.status_code == 200
    piece = PatternPiece.query.filter_by(piece_name="Handle Strap").one()
    assert piece.quantity_to_cut == 2

    edit_response = client.post(
        f"/patterns/{pattern.id}/pieces/{piece.id}/edit",
        data={
            "piece_name": "Handle Strap",
            "quantity_to_cut": "4",
            "measurements": "4in x 22in",
            "fabric_type": "Outer",
            "image_url": "",
            "notes": "cut 2 pairs",
        },
        follow_redirects=True,
    )
    assert edit_response.status_code == 200
    assert db.session.get(PatternPiece, piece.id).quantity_to_cut == 4

    delete_response = client.post(
        f"/patterns/{pattern.id}/pieces/{piece.id}/delete",
        follow_redirects=True,
    )
    assert delete_response.status_code == 200
    assert db.session.get(PatternPiece, piece.id) is None


def test_add_piece_rejects_quantity_below_one(client):
    pattern = make_pattern()
    response = client.post(
        f"/patterns/{pattern.id}/pieces",
        data={
            "piece_name": "Front Panel",
            "quantity_to_cut": "0",
            "measurements": "",
            "fabric_type": "",
            "image_url": "",
            "notes": "",
        },
    )
    assert response.status_code == 400
    assert b"at least 1" in response.data
    assert PatternPiece.query.count() == 0


def test_delete_unused_pattern_also_deletes_pieces(client):
    pattern = make_pattern()
    make_piece(pattern)
    pattern_id = pattern.id
    response = client.post(f"/patterns/{pattern_id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert db.session.get(Pattern, pattern_id) is None
    assert PatternPiece.query.filter_by(pattern_id=pattern_id).count() == 0


def test_cannot_delete_pattern_used_by_project(client):
    pattern = make_pattern()
    make_piece(pattern)
    fabric = make_fabric()
    project = make_project(pattern, fabric, name="Birthday tote")

    response = client.post(f"/patterns/{pattern.id}/delete")
    assert response.status_code == 409
    assert b"cannot be deleted" in response.data
    assert b"Birthday tote" in response.data
    assert f"/projects/{project.id}/edit".encode() in response.data
    assert db.session.get(Pattern, pattern.id) is not None
    assert PatternPiece.query.filter_by(pattern_id=pattern.id).count() == 1
    assert project.id is not None
