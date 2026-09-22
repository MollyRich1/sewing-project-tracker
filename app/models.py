from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def _utcnow():
    return datetime.now(timezone.utc)


class Pattern(db.Model):
    __tablename__ = "patterns"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    estimated_hours = db.Column(db.Float, nullable=False)
    outer_yards_required = db.Column(db.Float, nullable=False)
    lining_yards_required = db.Column(db.Float, nullable=True)
    notions = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    pieces = db.relationship(
        "PatternPiece",
        back_populates="pattern",
        cascade="all, delete-orphan",
    )
    # "all" keeps SQLAlchemy from nulling project.pattern_id; the
    # database RESTRICT rule then blocks the delete.
    projects = db.relationship(
        "Project",
        back_populates="pattern",
        passive_deletes="all",
    )

    def __repr__(self):
        return f"<Pattern {self.id} {self.name!r}>"


class PatternPiece(db.Model):
    __tablename__ = "pattern_pieces"

    id = db.Column(db.Integer, primary_key=True)
    pattern_id = db.Column(
        db.Integer,
        db.ForeignKey("patterns.id", ondelete="CASCADE"),
        nullable=False,
    )
    piece_name = db.Column(db.String(200), nullable=False)
    quantity_to_cut = db.Column(db.Integer, nullable=False)
    measurements = db.Column(db.String(200), nullable=True)
    fabric_type = db.Column(db.String(100), nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    pattern = db.relationship("Pattern", back_populates="pieces")

    def __repr__(self):
        return f"<PatternPiece {self.id} {self.piece_name!r}>"


class Fabric(db.Model):
    __tablename__ = "fabrics"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    yards_available = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    outer_projects = db.relationship(
        "Project",
        foreign_keys="Project.outer_fabric_id",
        back_populates="outer_fabric",
        passive_deletes="all",
    )
    lining_projects = db.relationship(
        "Project",
        foreign_keys="Project.lining_fabric_id",
        back_populates="lining_fabric",
        passive_deletes="all",
    )

    def __repr__(self):
        return f"<Fabric {self.id} {self.name!r}>"


class Project(db.Model):
    __tablename__ = "projects"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    pattern_id = db.Column(
        db.Integer,
        db.ForeignKey("patterns.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Two FKs to fabrics: outer is required, lining is optional.
    # They may point at the same Fabric row.
    outer_fabric_id = db.Column(
        db.Integer,
        db.ForeignKey("fabrics.id", ondelete="RESTRICT"),
        nullable=False,
    )
    lining_fabric_id = db.Column(
        db.Integer,
        db.ForeignKey("fabrics.id", ondelete="RESTRICT"),
        nullable=True,
    )
    status = db.Column(db.String(50), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=_utcnow)

    pattern = db.relationship("Pattern", back_populates="projects")
    outer_fabric = db.relationship(
        "Fabric",
        foreign_keys=[outer_fabric_id],
        back_populates="outer_projects",
    )
    lining_fabric = db.relationship(
        "Fabric",
        foreign_keys=[lining_fabric_id],
        back_populates="lining_projects",
    )

    def __repr__(self):
        return f"<Project {self.id} {self.name!r}>"
