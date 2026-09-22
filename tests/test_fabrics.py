from app.models import Fabric, db
from tests.factories import make_fabric, make_pattern, make_project


def test_fabric_list_and_empty_state(client):
    response = client.get("/fabrics/")
    assert response.status_code == 200
    assert b"No fabrics yet" in response.data

    make_fabric(name="Blue Floral Cotton", yards_available=2.5)
    response = client.get("/fabrics/")
    assert b"Blue Floral Cotton" in response.data
    assert b"2.5 yards available" in response.data


def test_create_fabric(client):
    response = client.post(
        "/fabrics/new",
        data={
            "name": "Natural Canvas",
            "yards_available": "3.25",
            "description": "Heavy cotton canvas",
            "notes": "Prewashed",
            "image_url": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    fabric = Fabric.query.filter_by(name="Natural Canvas").one()
    assert fabric.yards_available == 3.25
    assert fabric.description == "Heavy cotton canvas"
    assert b"Fabric saved" in response.data


def test_create_fabric_rejects_negative_yardage(client):
    response = client.post(
        "/fabrics/new",
        data={
            "name": "Impossible Fabric",
            "yards_available": "-0.25",
            "description": "",
            "notes": "",
            "image_url": "",
        },
    )
    assert response.status_code == 400
    assert b"cannot be negative" in response.data
    assert Fabric.query.count() == 0


def test_edit_fabric(client):
    fabric = make_fabric(name="Canvas", yards_available=2)
    response = client.post(
        f"/fabrics/{fabric.id}/edit",
        data={
            "name": "Natural Canvas",
            "yards_available": "1.5",
            "description": "Updated description",
            "notes": "",
            "image_url": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    updated = db.session.get(Fabric, fabric.id)
    assert updated.name == "Natural Canvas"
    assert updated.yards_available == 1.5


def test_delete_unused_fabric(client):
    fabric = make_fabric()
    fabric_id = fabric.id
    response = client.post(
        f"/fabrics/{fabric_id}/delete", follow_redirects=True
    )
    assert response.status_code == 200
    assert db.session.get(Fabric, fabric_id) is None
    assert b"Fabric deleted" in response.data


def test_delete_blocked_when_fabric_is_outer(client):
    pattern = make_pattern()
    fabric = make_fabric(name="Outer Canvas")
    project = make_project(pattern, fabric, name="Market Tote")

    response = client.post(f"/fabrics/{fabric.id}/delete")
    assert response.status_code == 409
    assert b"cannot be deleted" in response.data
    assert b"Market Tote" in response.data
    assert b"Outer fabric" in response.data
    assert f"/projects/{project.id}/edit".encode() in response.data
    assert db.session.get(Fabric, fabric.id) is not None


def test_delete_blocked_when_fabric_is_lining(client):
    pattern = make_pattern()
    outer = make_fabric(name="Outer Canvas")
    lining = make_fabric(name="Striped Lining")
    make_project(pattern, outer, lining_fabric=lining, name="Lined Tote")

    response = client.post(f"/fabrics/{lining.id}/delete")
    assert response.status_code == 409
    assert b"Lined Tote" in response.data
    assert b"Lining fabric" in response.data
    assert db.session.get(Fabric, lining.id) is not None


def test_same_fabric_for_both_roles_is_listed_once_with_both_roles(client):
    pattern = make_pattern()
    fabric = make_fabric(name="Self Lining Cotton")
    make_project(
        pattern,
        fabric,
        lining_fabric=fabric,
        name="Self-lined Pouch",
    )

    response = client.get(f"/fabrics/{fabric.id}/delete")
    assert response.status_code == 200
    assert response.data.count(b"Self-lined Pouch") == 1
    assert b"Outer and Lining fabric" in response.data
