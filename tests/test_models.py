import pytest
from sqlalchemy.exc import IntegrityError

from app.constants import STATUS_PLANNED
from app.helpers import (
    fabric_is_deletable,
    get_projects_blocking_fabric_delete,
    get_projects_blocking_pattern_delete,
    pattern_is_deletable,
)
from app.models import Fabric, Pattern, PatternPiece, Project, db


def make_pattern(**overrides):
    values = {
        "name": "Small Tote Bag",
        "notes": "Includes exterior, lining, and handles",
        "estimated_hours": 3.0,
        "outer_yards_required": 1.0,
        "lining_yards_required": 0.5,
        "notions": "1 magnetic snap, fusible interfacing",
    }
    values.update(overrides)
    pattern = Pattern(**values)
    db.session.add(pattern)
    db.session.commit()
    return pattern


def make_fabric(**overrides):
    values = {
        "name": "Blue Floral Cotton",
        "yards_available": 2.5,
        "description": "Blue cotton with small white flowers",
        "notes": None,
    }
    values.update(overrides)
    fabric = Fabric(**values)
    db.session.add(fabric)
    db.session.commit()
    return fabric


def make_piece(pattern, **overrides):
    values = {
        "pattern": pattern,
        "piece_name": "Front Panel",
        "quantity_to_cut": 2,
        "measurements": "12in x 18in",
        "fabric_type": "Outer",
        "notes": "cut on fold",
    }
    values.update(overrides)
    piece = PatternPiece(**values)
    db.session.add(piece)
    db.session.commit()
    return piece


def make_project(pattern, outer_fabric, **overrides):
    values = {
        "name": "Mom birthday tote",
        "pattern": pattern,
        "outer_fabric": outer_fabric,
        "status": STATUS_PLANNED,
    }
    values.update(overrides)
    project = Project(**values)
    db.session.add(project)
    db.session.commit()
    return project


def test_pattern_has_many_pieces():
    pattern = make_pattern()
    make_piece(pattern, piece_name="Front Panel")
    make_piece(pattern, piece_name="Handle Strap", quantity_to_cut=2, fabric_type="Outer")

    db.session.refresh(pattern)
    names = [piece.piece_name for piece in pattern.pieces]
    assert names == ["Front Panel", "Handle Strap"]
    assert pattern.pieces[0].pattern is pattern


def test_deleting_pattern_cascade_deletes_pieces():
    pattern = make_pattern()
    make_piece(pattern, piece_name="Front Panel")
    make_piece(pattern, piece_name="Lining", fabric_type="Lining")
    pattern_id = pattern.id

    db.session.delete(pattern)
    db.session.commit()

    assert db.session.get(Pattern, pattern_id) is None
    assert PatternPiece.query.filter_by(pattern_id=pattern_id).count() == 0


def test_project_belongs_to_pattern():
    pattern = make_pattern()
    outer = make_fabric()
    project = make_project(pattern, outer)

    assert project.pattern is pattern
    assert project in pattern.projects
    assert project.pattern.estimated_hours == 3.0


def test_project_requires_outer_fabric():
    pattern = make_pattern()
    project = Project(
        name="Missing outer",
        pattern=pattern,
        status=STATUS_PLANNED,
    )
    db.session.add(project)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_project_lining_fabric_is_optional():
    pattern = make_pattern()
    outer = make_fabric()
    project = make_project(pattern, outer)

    assert project.outer_fabric is outer
    assert project.lining_fabric is None
    assert project.lining_fabric_id is None


def test_outer_and_lining_may_be_the_same_fabric():
    pattern = make_pattern()
    fabric = make_fabric(name="Canvas")
    project = make_project(pattern, fabric, lining_fabric=fabric)

    assert project.outer_fabric_id == project.lining_fabric_id
    assert project.outer_fabric is project.lining_fabric
    assert project in fabric.outer_projects
    assert project in fabric.lining_projects


def test_pattern_yards_lining_may_be_null():
    pattern = make_pattern(lining_yards_required=None)
    assert pattern.outer_yards_required == 1.0
    assert pattern.lining_yards_required is None


def test_cannot_delete_pattern_used_by_a_project():
    pattern = make_pattern()
    make_piece(pattern)
    outer = make_fabric()
    project = make_project(pattern, outer)

    assert pattern_is_deletable(pattern) is False
    assert get_projects_blocking_pattern_delete(pattern) == [project]

    db.session.delete(pattern)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()

    assert db.session.get(Pattern, pattern.id) is not None
    assert db.session.get(Project, project.id) is not None
    assert PatternPiece.query.filter_by(pattern_id=pattern.id).count() == 1


def test_unused_pattern_is_deletable():
    pattern = make_pattern()
    make_piece(pattern)
    assert pattern_is_deletable(pattern) is True
    assert get_projects_blocking_pattern_delete(pattern) == []


def test_cannot_delete_fabric_used_as_outer():
    pattern = make_pattern()
    outer = make_fabric(name="Outer cotton")
    lining = make_fabric(name="Lining cotton")
    project = make_project(pattern, outer, lining_fabric=lining)

    assert fabric_is_deletable(outer) is False
    assert get_projects_blocking_fabric_delete(outer) == [project]

    db.session.delete(outer)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert db.session.get(Fabric, outer.id) is not None
    assert db.session.get(Project, project.id) is not None


def test_cannot_delete_fabric_used_as_lining():
    pattern = make_pattern()
    outer = make_fabric(name="Outer cotton")
    lining = make_fabric(name="Lining cotton")
    project = make_project(pattern, outer, lining_fabric=lining)

    assert fabric_is_deletable(lining) is False
    assert get_projects_blocking_fabric_delete(lining) == [project]

    db.session.delete(lining)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()
    assert db.session.get(Fabric, lining.id) is not None


def test_same_fabric_for_outer_and_lining_blocks_delete_once():
    pattern = make_pattern()
    fabric = make_fabric()
    project = make_project(pattern, fabric, lining_fabric=fabric)

    blocking = get_projects_blocking_fabric_delete(fabric)
    assert blocking == [project]


def test_unused_fabric_is_deletable():
    fabric = make_fabric()
    assert fabric_is_deletable(fabric) is True
    fabric_id = fabric.id
    db.session.delete(fabric)
    db.session.commit()
    assert db.session.get(Fabric, fabric_id) is None


def test_deleting_a_project_does_not_delete_pattern_or_fabrics():
    pattern = make_pattern()
    make_piece(pattern)
    outer = make_fabric(name="Outer")
    lining = make_fabric(name="Lining")
    project = make_project(pattern, outer, lining_fabric=lining)
    project_id = project.id

    db.session.delete(project)
    db.session.commit()

    assert db.session.get(Project, project_id) is None
    assert db.session.get(Pattern, pattern.id) is not None
    assert db.session.get(Fabric, outer.id) is not None
    assert db.session.get(Fabric, lining.id) is not None
    assert PatternPiece.query.filter_by(pattern_id=pattern.id).count() == 1
    assert pattern_is_deletable(pattern) is True
    assert fabric_is_deletable(outer) is True
    assert fabric_is_deletable(lining) is True
