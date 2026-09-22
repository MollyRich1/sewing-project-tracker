import click

from app.constants import (
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_PLANNED,
)
from app.models import Fabric, Pattern, PatternPiece, Project, db


def register_seed_commands(app):
    @app.cli.command("seed")
    def seed_command():
        """Add a small set of realistic demonstration data."""
        if (
            Pattern.query.first() is not None
            or Fabric.query.first() is not None
            or Project.query.first() is not None
        ):
            raise click.ClickException(
                "The database is not empty. Reset it first if you want demo data."
            )

        tote = Pattern(
            name="Everyday Tote Bag",
            notes="A lined tote with boxed corners and sturdy handles.",
            estimated_hours=3.5,
            outer_yards_required=1.0,
            lining_yards_required=0.75,
            notions="Fusible interfacing and optional magnetic snap",
        )
        tote.pieces = [
            PatternPiece(
                piece_name="Outer body",
                quantity_to_cut=2,
                measurements="16in x 18in",
                fabric_type="Outer",
                notes="Cut one pair",
            ),
            PatternPiece(
                piece_name="Lining body",
                quantity_to_cut=2,
                measurements="16in x 18in",
                fabric_type="Lining",
            ),
            PatternPiece(
                piece_name="Handle",
                quantity_to_cut=2,
                measurements="4in x 24in",
                fabric_type="Outer",
            ),
        ]
        pouch = Pattern(
            name="Simple Zipper Pouch",
            notes="A small lined pouch for practicing zipper installation.",
            estimated_hours=1.5,
            outer_yards_required=0.25,
            lining_yards_required=0.25,
            notions="One 9in zipper",
        )
        pouch.pieces = [
            PatternPiece(
                piece_name="Outer panel",
                quantity_to_cut=2,
                measurements="7in x 10in",
                fabric_type="Outer",
            ),
            PatternPiece(
                piece_name="Lining panel",
                quantity_to_cut=2,
                measurements="7in x 10in",
                fabric_type="Lining",
            ),
        ]
        apron = Pattern(
            name="Cross-back Apron",
            notes="An unlined apron with wide crossed straps.",
            estimated_hours=2.5,
            outer_yards_required=2.0,
            lining_yards_required=None,
            notions="Matching thread",
        )
        apron.pieces = [
            PatternPiece(
                piece_name="Apron body",
                quantity_to_cut=1,
                measurements="Cut on fold",
                fabric_type="Outer",
            )
        ]

        canvas = Fabric(
            name="Natural Cotton Canvas",
            yards_available=2.5,
            description="Warm natural canvas with a sturdy hand.",
            notes="Prewashed",
        )
        floral = Fabric(
            name="Blue Floral Cotton",
            yards_available=1.25,
            description="Light blue cotton with small white flowers.",
        )
        linen = Fabric(
            name="Sage Linen Blend",
            yards_available=2.0,
            description="Medium-weight sage linen and cotton blend.",
        )

        db.session.add_all([tote, pouch, apron, canvas, floral, linen])
        db.session.flush()
        db.session.add_all(
            [
                Project(
                    name="Market Day Tote",
                    pattern=tote,
                    outer_fabric=canvas,
                    lining_fabric=floral,
                    status=STATUS_IN_PROGRESS,
                    notes="Use the magnetic snap.",
                ),
                Project(
                    name="Travel Notions Pouch",
                    pattern=pouch,
                    outer_fabric=floral,
                    lining_fabric=floral,
                    status=STATUS_PLANNED,
                    notes="Self-lined with the floral cotton.",
                ),
                Project(
                    name="Garden Apron",
                    pattern=apron,
                    outer_fabric=linen,
                    status=STATUS_COMPLETED,
                ),
            ]
        )
        db.session.commit()
        click.echo("Added demo patterns, fabrics, and projects.")

    @app.cli.command("reset-db")
    @click.option(
        "--yes",
        is_flag=True,
        help="Confirm deletion of all local application data.",
    )
    def reset_db_command(yes):
        """Delete all data and recreate empty database tables."""
        if not yes:
            raise click.ClickException(
                "This deletes all data. Run again with --yes to confirm."
            )
        db.drop_all()
        db.create_all()
        click.echo("Reset the database. It is now empty.")
