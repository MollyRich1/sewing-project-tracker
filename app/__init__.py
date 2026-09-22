import os
import sqlite3

from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine

from config import Config


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    """SQLite does not enforce foreign keys unless this pragma is on."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    os.makedirs(app.instance_path, exist_ok=True)

    default_db = "sqlite:///" + os.path.join(app.instance_path, "sewing.db")
    app.config.setdefault("SQLALCHEMY_DATABASE_URI", default_db)

    if test_config:
        app.config.update(test_config)

    from app.models import db
    from app.routes.patterns import bp as patterns_bp

    db.init_app(app)
    app.register_blueprint(patterns_bp)

    with app.app_context():
        db.create_all()

    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables."""
        db.create_all()
        print("Initialized the database.")

    return app
