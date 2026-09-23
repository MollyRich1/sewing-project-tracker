import os
from io import BytesIO

from app.constants import STATUS_IN_PROGRESS
from app.images import project_image_ref
from app.models import Fabric, Pattern, PatternPiece, Project, db
from tests.factories import make_fabric, make_pattern, make_project

PNG_BYTES = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"\x00" * 64


def _image_tuple(data=PNG_BYTES, filename="swatch.png", mime="image/png"):
    return (BytesIO(data), filename, mime)


def _upload_path(app, relative):
    return os.path.join(app.config["UPLOAD_FOLDER"], relative)


def test_create_fabric_without_image(client):
    response = client.post(
        "/fabrics/new",
        data={
            "name": "Plain Canvas",
            "yards_available": "2",
            "description": "",
            "notes": "",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    fabric = Fabric.query.filter_by(name="Plain Canvas").one()
    assert fabric.image_url is None
    assert b"media-placeholder--fabric" in response.data


def test_create_fabric_with_image_and_serve_it(client, app):
    response = client.post(
        "/fabrics/new",
        data={
            "name": "Photo Canvas",
            "yards_available": "1.5",
            "description": "Natural canvas",
            "notes": "",
            "image": _image_tuple(),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    fabric = Fabric.query.filter_by(name="Photo Canvas").one()
    assert fabric.image_url.startswith("fabrics/")
    assert fabric.image_url.endswith(".png")
    assert os.path.isfile(_upload_path(app, fabric.image_url))
    served = client.get(f"/uploads/{fabric.image_url}")
    assert served.status_code == 200
    assert served.data.startswith(b"\x89PNG")
    assert fabric.image_url.encode() in response.data


def test_edit_fabric_keeps_image_unless_replaced(client, app):
    client.post(
        "/fabrics/new",
        data={
            "name": "Keep Me",
            "yards_available": "2",
            "image": _image_tuple(filename="first.png"),
        },
    )
    fabric = Fabric.query.filter_by(name="Keep Me").one()
    original = fabric.image_url

    keep_response = client.post(
        f"/fabrics/{fabric.id}/edit",
        data={
            "name": "Keep Me",
            "yards_available": "3",
            "description": "",
            "notes": "",
        },
        follow_redirects=True,
    )
    assert keep_response.status_code == 200
    db.session.refresh(fabric)
    assert fabric.image_url == original
    assert os.path.isfile(_upload_path(app, original))

    replace_response = client.post(
        f"/fabrics/{fabric.id}/edit",
        data={
            "name": "Keep Me",
            "yards_available": "3",
            "description": "",
            "notes": "",
            "image": _image_tuple(JPEG_BYTES, "next.jpg", "image/jpeg"),
        },
        follow_redirects=True,
    )
    assert replace_response.status_code == 200
    db.session.refresh(fabric)
    assert fabric.image_url != original
    assert fabric.image_url.endswith(".jpg")
    assert os.path.isfile(_upload_path(app, fabric.image_url))
    assert not os.path.isfile(_upload_path(app, original))


def test_delete_fabric_removes_its_image_file(client, app):
    client.post(
        "/fabrics/new",
        data={
            "name": "Disposable",
            "yards_available": "1",
            "image": _image_tuple(),
        },
    )
    fabric = Fabric.query.filter_by(name="Disposable").one()
    image_url = fabric.image_url
    response = client.post(f"/fabrics/{fabric.id}/delete", follow_redirects=True)
    assert response.status_code == 200
    assert db.session.get(Fabric, fabric.id) is None
    assert not os.path.isfile(_upload_path(app, image_url))


def test_create_pattern_with_and_without_image(client, app):
    without = client.post(
        "/patterns/new",
        data={
            "name": "No Photo Pattern",
            "estimated_hours": "2",
            "outer_yards_required": "1",
            "lining_yards_required": "",
            "notions": "",
            "notes": "",
        },
        follow_redirects=True,
    )
    assert without.status_code == 200
    bare = Pattern.query.filter_by(name="No Photo Pattern").one()
    assert bare.image_url is None

    with_image = client.post(
        "/patterns/new",
        data={
            "name": "Cover Pattern",
            "estimated_hours": "3",
            "outer_yards_required": "1",
            "lining_yards_required": "",
            "notions": "",
            "notes": "",
            "image": _image_tuple(filename="cover.png"),
        },
        follow_redirects=True,
    )
    assert with_image.status_code == 200
    pattern = Pattern.query.filter_by(name="Cover Pattern").one()
    assert pattern.image_url.startswith("patterns/")
    assert os.path.isfile(_upload_path(app, pattern.image_url))
    assert pattern.image_url.encode() in with_image.data


def test_edit_pattern_replaces_image(client, app):
    client.post(
        "/patterns/new",
        data={
            "name": "Replace Pattern",
            "estimated_hours": "1",
            "outer_yards_required": "1",
            "lining_yards_required": "",
            "notions": "",
            "notes": "",
            "image": _image_tuple(filename="old.png"),
        },
    )
    pattern = Pattern.query.filter_by(name="Replace Pattern").one()
    original = pattern.image_url
    client.post(
        f"/patterns/{pattern.id}/edit",
        data={
            "name": "Replace Pattern",
            "estimated_hours": "1",
            "outer_yards_required": "1",
            "lining_yards_required": "",
            "notions": "",
            "notes": "",
            "image": _image_tuple(JPEG_BYTES, "new.jpg", "image/jpeg"),
        },
    )
    db.session.refresh(pattern)
    assert pattern.image_url.endswith(".jpg")
    assert not os.path.isfile(_upload_path(app, original))


def test_create_and_replace_project_image(client, app):
    pattern = make_pattern()
    fabric = make_fabric()
    create = client.post(
        "/projects/new",
        data={
            "name": "Photo Project",
            "pattern_id": str(pattern.id),
            "outer_fabric_id": str(fabric.id),
            "lining_fabric_id": "",
            "status": STATUS_IN_PROGRESS,
            "notes": "",
            "image": _image_tuple(filename="wip.png"),
        },
        follow_redirects=True,
    )
    assert create.status_code == 200
    project = Project.query.filter_by(name="Photo Project").one()
    original = project.image_url
    assert original.startswith("projects/")
    assert original.encode() in create.data

    client.post(
        f"/projects/{project.id}/edit",
        data={
            "name": "Photo Project",
            "pattern_id": str(pattern.id),
            "outer_fabric_id": str(fabric.id),
            "lining_fabric_id": "",
            "status": STATUS_IN_PROGRESS,
            "notes": "",
            "image": _image_tuple(JPEG_BYTES, "finished.jpg", "image/jpeg"),
        },
    )
    db.session.refresh(project)
    assert project.image_url.endswith(".jpg")
    assert not os.path.isfile(_upload_path(app, original))
    assert os.path.isfile(_upload_path(app, project.image_url))


def test_project_fallback_uses_project_then_pattern_then_fabric():
    pattern = make_pattern(image_url="patterns/pattern.png")
    fabric = make_fabric(image_url="fabrics/fabric.png")
    project = make_project(pattern, fabric)

    assert project_image_ref(project) == "patterns/pattern.png"

    project.image_url = "projects/project.png"
    db.session.commit()
    assert project_image_ref(project) == "projects/project.png"

    project.image_url = None
    pattern.image_url = None
    db.session.commit()
    assert project_image_ref(project) == "fabrics/fabric.png"

    fabric.image_url = None
    db.session.commit()
    assert project_image_ref(project) is None


def test_dashboard_and_lists_use_fallback_images(client):
    pattern = make_pattern(name="Cross-back Apron", image_url=None)
    fabric = make_fabric(name="Sage Linen Blend")
    client.post(
        f"/fabrics/{fabric.id}/edit",
        data={
            "name": fabric.name,
            "yards_available": str(fabric.yards_available),
            "description": "",
            "notes": "",
            "image": _image_tuple(filename="linen.png"),
        },
    )
    db.session.refresh(fabric)
    project = make_project(
        pattern, fabric, name="Garden Apron", status=STATUS_IN_PROGRESS
    )

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert fabric.image_url.encode() in dashboard.data
    assert b"media-placeholder--project" not in dashboard.data

    projects = client.get("/projects/")
    assert fabric.image_url.encode() in projects.data

    client.post(
        f"/patterns/{pattern.id}/edit",
        data={
            "name": pattern.name,
            "estimated_hours": str(pattern.estimated_hours),
            "outer_yards_required": str(pattern.outer_yards_required),
            "lining_yards_required": "",
            "notions": "",
            "notes": "",
            "image": _image_tuple(filename="apron.png"),
        },
    )
    db.session.refresh(pattern)
    dashboard = client.get("/")
    assert pattern.image_url.encode() in dashboard.data

    client.post(
        f"/projects/{project.id}/edit",
        data={
            "name": project.name,
            "pattern_id": str(pattern.id),
            "outer_fabric_id": str(fabric.id),
            "lining_fabric_id": "",
            "status": STATUS_IN_PROGRESS,
            "notes": "",
            "image": _image_tuple(filename="garden.png"),
        },
    )
    db.session.refresh(project)
    dashboard = client.get("/")
    assert project.image_url.encode() in dashboard.data


def test_rejects_unsupported_and_mismatched_uploads(client):
    response = client.post(
        "/fabrics/new",
        data={
            "name": "Bad File",
            "yards_available": "1",
            "image": _image_tuple(b"not-an-image", "notes.txt", "text/plain"),
        },
    )
    assert response.status_code == 400
    assert b"JPG, PNG, or WebP" in response.data
    assert Fabric.query.count() == 0

    disguised = client.post(
        "/patterns/new",
        data={
            "name": "Disguised",
            "estimated_hours": "1",
            "outer_yards_required": "1",
            "lining_yards_required": "",
            "notions": "",
            "notes": "",
            "image": _image_tuple(b"<html>nope</html>", "cover.png", "image/png"),
        },
    )
    assert disguised.status_code == 400
    assert b"not a valid" in disguised.data
    assert Pattern.query.count() == 0


def test_projects_table_has_optional_image_url(app):
    from sqlalchemy import inspect

    columns = {
        column["name"]: column for column in inspect(db.engine).get_columns("projects")
    }
    assert "image_url" in columns
    assert columns["image_url"]["nullable"] is True


def test_rejects_oversized_image(client, app):
    app.config["MAX_IMAGE_BYTES"] = 40
    response = client.post(
        "/fabrics/new",
        data={
            "name": "Huge Photo",
            "yards_available": "1",
            "image": _image_tuple(PNG_BYTES + b"\x00" * 80, "huge.png"),
        },
    )
    assert response.status_code == 400
    assert b"too large" in response.data
    assert Fabric.query.count() == 0


def test_piece_upload_and_pattern_delete_cleans_files(client, app):
    client.post(
        "/patterns/new",
        data={
            "name": "Tote",
            "estimated_hours": "2",
            "outer_yards_required": "1",
            "lining_yards_required": "",
            "notions": "",
            "notes": "",
            "image": _image_tuple(filename="pattern.png"),
        },
    )
    pattern = Pattern.query.filter_by(name="Tote").one()
    client.post(
        f"/patterns/{pattern.id}/pieces",
        data={
            "piece_name": "Body",
            "quantity_to_cut": "2",
            "measurements": "",
            "fabric_type": "Outer",
            "notes": "",
            "image": _image_tuple(filename="piece.png"),
        },
    )
    piece = PatternPiece.query.filter_by(piece_name="Body").one()
    paths = [pattern.image_url, piece.image_url]
    for path in paths:
        assert os.path.isfile(_upload_path(app, path))

    client.post(f"/patterns/{pattern.id}/delete", follow_redirects=True)
    for path in paths:
        assert not os.path.isfile(_upload_path(app, path))


def test_upload_route_rejects_path_traversal(client):
    response = client.get("/uploads/fabrics/../projects/secret.png")
    assert response.status_code == 404
