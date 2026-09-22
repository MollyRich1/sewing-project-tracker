from app.constants import (
    STATUS_COMPLETED,
    STATUS_IN_PROGRESS,
    STATUS_PLANNED,
)
from app.models import Fabric, Pattern, PatternPiece, Project
from tests.factories import make_pattern


def test_seed_command_adds_realistic_demo_data(app):
    result = app.test_cli_runner().invoke(args=["seed"])

    assert result.exit_code == 0
    assert "Added demo patterns" in result.output
    assert Pattern.query.count() == 3
    assert PatternPiece.query.count() == 6
    assert Fabric.query.count() == 3
    assert Project.query.count() == 3
    assert {project.status for project in Project.query.all()} == {
        STATUS_PLANNED,
        STATUS_IN_PROGRESS,
        STATUS_COMPLETED,
    }
    self_lined = Project.query.filter_by(name="Travel Notions Pouch").one()
    assert self_lined.outer_fabric_id == self_lined.lining_fabric_id
    apron = Pattern.query.filter_by(name="Cross-back Apron").one()
    assert apron.lining_yards_required is None


def test_seed_command_refuses_nonempty_database(app):
    make_pattern()
    result = app.test_cli_runner().invoke(args=["seed"])

    assert result.exit_code != 0
    assert "database is not empty" in result.output
    assert Pattern.query.count() == 1


def test_reset_command_requires_confirmation(app):
    make_pattern()
    result = app.test_cli_runner().invoke(args=["reset-db"])

    assert result.exit_code != 0
    assert "with --yes to confirm" in result.output
    assert Pattern.query.count() == 1


def test_reset_command_returns_database_to_empty(app):
    seed_result = app.test_cli_runner().invoke(args=["seed"])
    assert seed_result.exit_code == 0

    reset_result = app.test_cli_runner().invoke(args=["reset-db", "--yes"])
    assert reset_result.exit_code == 0
    assert "now empty" in reset_result.output
    assert Pattern.query.count() == 0
    assert PatternPiece.query.count() == 0
    assert Fabric.query.count() == 0
    assert Project.query.count() == 0
