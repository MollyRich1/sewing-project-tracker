import pytest

from app import create_app
from app.models import db


@pytest.fixture
def app(tmp_path):
    db_path = tmp_path / "test.db"
    upload_path = tmp_path / "uploads"
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{db_path}",
            "UPLOAD_FOLDER": str(upload_path),
        }
    )
    yield application
    with application.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture(autouse=True)
def app_context(app):
    with app.app_context():
        yield


@pytest.fixture
def client(app):
    return app.test_client()
