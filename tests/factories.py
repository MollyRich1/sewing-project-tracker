from app.constants import STATUS_PLANNED
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
